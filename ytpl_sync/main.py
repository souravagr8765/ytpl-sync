import argparse
import asyncio
import logging
import os
import sys
import tempfile
import traceback
import uuid
import yaml
from datetime import datetime
from pathlib import Path

try:
    from ytpl_sync import __version__
    VERSION = __version__
except ImportError:
    try:
        from . import __version__
        VERSION = __version__
    except ImportError:
        VERSION = "1.0.0"

from .config import AppConfig
from .run_context import RunContext
from .models import VideoStatus, Video, FailedStage

from .lock import LockFile, LockAcquireError
from .utils.time_window import assert_time_window, TimeWindowError
from .utils.disk import check_free_space, DiskSpaceError
from .utils.cleanup import cleanup_orphan_files
from .utils.ytdlp_check import check_ytdlp
from .utils.subprocess_runner import find_executable

from .db.manager import DatabaseManager
from .db.sqlite_backend import SQLiteBackend
from .db.neon_backend import NeonBackend
from .db.reconciler import Reconciler

from .sources.resolver import resolve_source

from .downloader import Downloader
from .encoder import Encoder
from .storage.router import StorageRouter

from .notifications.mailer import Mailer
from .notifications.telegram import TelegramNotifier
from .notifications.reporter import ReportBuilder

logger = logging.getLogger(__name__)

def load_config(path: str) -> AppConfig:
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)

def setup_logging(config: AppConfig):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler
    log_file = Path(config.settings.log_file).expanduser()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)


def handle_failure(video: Video, ctx: RunContext, config: AppConfig, mailer: Mailer, telegram: TelegramNotifier) -> None:
    video.retry_count += 1
    reporter = ReportBuilder()
    
    if video.retry_count >= config.settings.max_retries:
        video.status = VideoStatus.ABANDONED
        ctx.abandoned += 1
        logger.warning(f"Video ABANDONED after {video.retry_count} retries: {video.title or video.video_id}")
        
        try:
            if config.notifications.email.send_on_failure:
                mailer.send(f"[ytpl-sync] ABANDONED: {video.title or video.video_id}", reporter.build_failure_alert_email(video))
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            
        try:
            if config.notifications.telegram.send_on_failure:
                telegram.send(reporter.build_failure_alert_telegram(video))
        except Exception as e:
            logger.error(f"Failed to send telegram alert: {e}")
            
    else:
        logger.warning(f"Video failed at stage {video.failed_stage} (attempt {video.retry_count}/{config.settings.max_retries}): {video.title or video.video_id} - {video.failed_reason}")
    ctx.failed += 1


async def run(config: AppConfig, args: argparse.Namespace) -> RunContext:
    run_id = str(uuid.uuid4())[:8]
    dry_run = args.dry_run or config.settings.dry_run
    ctx = RunContext(run_id=run_id, started_at=datetime.utcnow(), dry_run=dry_run)
    
    logger.info(f"=== ytpl-sync started | run_id={run_id} | dry_run={dry_run} ===")
    
    mailer = Mailer()
    telegram = TelegramNotifier()
    reporter = ReportBuilder()

    lock = LockFile(config.settings.lock_file)
    try:
        lock.acquire()
    except LockAcquireError as e:
        logger.error(str(e))
        sys.exit(1)

    try:
        try:
            assert_time_window(config.settings.only_run_between)
        except TimeWindowError as e:
            logger.info(str(e))
            sys.exit(0)
            
        temp_dir = config.settings.temp_dir or tempfile.gettempdir()
        min_free_gb = float(config.settings.min_free_gb)
        try:
            check_free_space(temp_dir, min_free_gb)
        except DiskSpaceError as e:
            logger.error(str(e))
            try:
                mailer.send("[ytpl-sync] CRITICAL: Disk Space Error", str(e))
            except Exception: pass
            try:
                telegram.send(f"CRITICAL: {str(e)}")
            except Exception: pass
            sys.exit(1)
            
        cleaned = cleanup_orphan_files(temp_dir)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} orphan files in {temp_dir}")
            
        check_ytdlp(config.settings.ytdlp_auto_update)
        
        ffmpeg_path = find_executable('ffmpeg', config.settings.ffmpeg_path)
        rclone_path = find_executable('rclone', config.settings.rclone_path)
        
        if config.encoding.enabled and not ffmpeg_path:
            logger.error("ffmpeg is required for encoding but was not found.")
            sys.exit(1)
        if config.destination.mode == "gdrive" and not rclone_path:
            logger.error("rclone is required for gdrive destination but was not found.")
            sys.exit(1)
            
        sqlite = SQLiteBackend(db_path="~/.ytpl-sync.db")
        neon = NeonBackend(dsn=os.environ.get('NEON_DSN'))
        manager = DatabaseManager(sqlite, neon)
        manager.initialize()
        
        reconciler = Reconciler()
        reconcile_result = await reconciler.run(sqlite, neon, dry_run=dry_run)
        logger.info(f"Reconciliation summary: {reconcile_result}")

        downloader = Downloader()
        encoder = Encoder()
        storage_router = StorageRouter()
        
        sources_to_run = config.sources
        if args.source:
            sources_to_run = [s for s in sources_to_run if s.name == args.source]
            
        for source in sources_to_run:
            logger.info(f"Processing source: {source.name} ({source.type})")
            
            try:
                videos = resolve_source(source, cookies_file=config.settings.cookies_file)
            except Exception as e:
                logger.error(f"Failed to resolve source {source.name}: {e}")
                continue
                
            ctx.discovered += len(videos)
            
            known_videos = [v for v in sqlite.get_all() if v.source_name == source.name]
            discovered_video_ids = {v.video_id for v in videos}
            
            for kv in known_videos:
                if kv.video_id not in discovered_video_ids and not kv.deleted and kv.status in (VideoStatus.DOWNLOADED, VideoStatus.ENCODED, VideoStatus.UPLOADED):
                    logger.info(f"Video {kv.video_id} no longer in source {source.name}. Marking as deleted.")
                    kv.deleted = True
                    kv.deleted_detected_at = datetime.utcnow().isoformat()
                    kv.status = VideoStatus.DELETED
                    if not dry_run:
                        manager.upsert_video(kv)
                    ctx.newly_deleted += 1
            
            for video_meta in videos:
                existing_video = manager.get_video(video_meta.video_id)
                if existing_video:
                    video = existing_video
                    video.title = video_meta.title or video.title
                    video.description = video_meta.description or video.description
                    video.duration_seconds = video_meta.duration_seconds or video.duration_seconds
                    video.upload_date = video_meta.upload_date or video.upload_date
                else:
                    video = video_meta

                if video.status in (VideoStatus.UPLOADED, VideoStatus.ABANDONED, VideoStatus.DELETED):
                    ctx.skipped += 1
                    continue
                    
                if dry_run:
                    logger.info(f"[DRY RUN] Would process video: {video.title or video.video_id} (Status: {video.status})")
                    continue
                    
                effective_config = config.get_effective_config(source)
                
                # DOWNLOAD
                if video.status in (VideoStatus.PENDING, VideoStatus.DOWNLOADING, VideoStatus.FAILED):
                    if video.status == VideoStatus.FAILED and video.failed_stage in (FailedStage.ENCODE, FailedStage.UPLOAD):
                        pass # resume from next stage
                    else:
                        video = downloader.download(video, temp_dir, effective_config['quality'], run_id)
                        manager.upsert_video(video)
                        if video.status == VideoStatus.FAILED:
                            handle_failure(video, ctx, config, mailer, telegram)
                            continue
                        ctx.downloaded += 1

                # ENCODE
                if video.status in (VideoStatus.DOWNLOADED, VideoStatus.ENCODING, VideoStatus.FAILED):
                    if video.status == VideoStatus.FAILED and video.failed_stage == FailedStage.UPLOAD:
                        pass # resume from next stage
                    else:
                        video = encoder.encode(video, effective_config['encoding'])
                        manager.upsert_video(video)
                        if video.status == VideoStatus.FAILED:
                            handle_failure(video, ctx, config, mailer, telegram)
                            continue
                        if video.status == VideoStatus.ENCODED:
                            ctx.encoded += 1
                            if video.original_size_bytes and video.final_size_bytes:
                                savings_mb = (video.original_size_bytes - video.final_size_bytes) / (1024 * 1024)
                                ctx.encoding_savings_mb += max(0.0, savings_mb)

                # UPLOAD
                if video.status in (VideoStatus.ENCODED, VideoStatus.UPLOADING, VideoStatus.FAILED):
                    video = storage_router.store(video, effective_config['destination'])
                    manager.upsert_video(video)
                    if video.status == VideoStatus.FAILED:
                        handle_failure(video, ctx, config, mailer, telegram)
                        continue
                    ctx.uploaded += 1

                ctx.videos_this_run.append(video)
                
            manager.flush_to_neon()

        logger.info(f"Run {run_id} complete. Summary: {ctx.summary_dict()}")
        
        had_activity = ctx.downloaded > 0 or ctx.uploaded > 0 or ctx.failed > 0 or ctx.newly_deleted > 0
        if had_activity:
            if config.notifications.email.enabled and config.notifications.email.send_report_on_activity:
                try:
                    mailer.send(f"[ytpl-sync] Run complete - {ctx.uploaded} uploaded, {ctx.failed} failed", reporter.build_email_report(ctx))
                except Exception as e:
                    logger.error(f"Failed to send email report: {e}")
                    
            if config.notifications.telegram.enabled and config.notifications.telegram.send_report_on_activity:
                try:
                    telegram.send(reporter.build_telegram_message(ctx))
                except Exception as e:
                    logger.error(f"Failed to send telegram report: {e}")
                    
    finally:
        lock.release()
        
    return ctx

def parse_args():
    parser = argparse.ArgumentParser(description="ytpl-sync: Sync YouTube videos to local/gdrive")
    parser.add_argument('--config', default='./config.yaml', help="Path to config.yaml")
    parser.add_argument('--dry-run', action='store_true', help="Override config dry_run to True")
    parser.add_argument('--version', action='store_true', help="Print version from VERSION file and exit")
    parser.add_argument('--source', help="Run only the source with this name")
    return parser.parse_args()

def cli():
    args = parse_args()
    
    if args.version:
        import importlib.metadata
        try:
            version = importlib.metadata.version('ytpl-sync')
        except Exception:
            version = VERSION
        print(f"ytpl-sync {version}")
        sys.exit(0)
        
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"CRITICAL: Failed to load config {args.config}: {e}")
        sys.exit(1)
        
    if args.dry_run:
        config.settings.dry_run = True
        
    setup_logging(config)
        
    try:
        asyncio.run(run(config, args))
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled error: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    cli()
