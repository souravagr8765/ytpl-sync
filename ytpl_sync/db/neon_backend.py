import json
import logging
from typing import Optional
from datetime import datetime, timezone

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

from ytpl_sync.models import Video

logger = logging.getLogger(__name__)

class NeonBackend:
    def __init__(self, dsn: Optional[str]):
        self.dsn = dsn
        self.conn = None

    def connect(self) -> bool:
        if not self.dsn:
            return False
            
        if psycopg2 is None:
            logger.warning("psycopg2 is not installed. Networking features disabled.")
            return False
            
        try:
            self.conn = psycopg2.connect(self.dsn, connect_timeout=10)
            self.conn.autocommit = False
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Neon DB: {e}")
            self.conn = None
            return False

    def initialize(self) -> None:
        if not self.conn:
            return
            
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            source_name TEXT,
            source_type TEXT,
            source_url TEXT,
            run_id TEXT,
            title TEXT,
            description TEXT,
            channel_name TEXT,
            channel_id TEXT,
            upload_date TEXT,
            duration_seconds INTEGER,
            view_count BIGINT,
            like_count BIGINT,
            thumbnail_url TEXT,
            tags TEXT,
            categories TEXT,
            youtube_url TEXT,
            status TEXT,
            failed_stage TEXT,
            failed_reason TEXT,
            retry_count INTEGER,
            deleted BOOLEAN,
            deleted_detected_at TEXT,
            original_filename TEXT,
            original_size_bytes BIGINT,
            final_filename TEXT,
            final_size_bytes BIGINT,
            encoding_savings_pct REAL,
            temp_path TEXT,
            local_path TEXT,
            rclone_remote TEXT,
            rclone_path TEXT,
            discovered_at TEXT,
            download_started_at TEXT,
            downloaded_at TEXT,
            encode_started_at TEXT,
            encoded_at TEXT,
            upload_started_at TEXT,
            uploaded_at TEXT,
            updated_at TEXT,
            pending_neon_sync BOOLEAN
        );
        CREATE INDEX IF NOT EXISTS idx_neon_status_pending ON videos (status, pending_neon_sync);
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(create_table_sql)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize Neon DB: {e}")
            self.conn.rollback()

    def upsert_many(self, videos: list[Video]) -> bool:
        if not self.conn or not videos:
            return False

        sql = """
        INSERT INTO videos (
            video_id, source_name, source_type, source_url, run_id, title, description, channel_name,
            channel_id, upload_date, duration_seconds, view_count, like_count, thumbnail_url, tags,
            categories, youtube_url, status, failed_stage, failed_reason, retry_count, deleted,
            deleted_detected_at, original_filename, original_size_bytes, final_filename, final_size_bytes,
            encoding_savings_pct, temp_path, local_path, rclone_remote, rclone_path, discovered_at,
            download_started_at, downloaded_at, encode_started_at, encoded_at, upload_started_at,
            uploaded_at, updated_at, pending_neon_sync
        ) VALUES %s
        ON CONFLICT (video_id) DO UPDATE SET
            source_name = EXCLUDED.source_name,
            source_type = EXCLUDED.source_type,
            source_url = EXCLUDED.source_url,
            run_id = EXCLUDED.run_id,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            channel_name = EXCLUDED.channel_name,
            channel_id = EXCLUDED.channel_id,
            upload_date = EXCLUDED.upload_date,
            duration_seconds = EXCLUDED.duration_seconds,
            view_count = EXCLUDED.view_count,
            like_count = EXCLUDED.like_count,
            thumbnail_url = EXCLUDED.thumbnail_url,
            tags = EXCLUDED.tags,
            categories = EXCLUDED.categories,
            youtube_url = EXCLUDED.youtube_url,
            status = EXCLUDED.status,
            failed_stage = EXCLUDED.failed_stage,
            failed_reason = EXCLUDED.failed_reason,
            retry_count = EXCLUDED.retry_count,
            deleted = EXCLUDED.deleted,
            deleted_detected_at = EXCLUDED.deleted_detected_at,
            original_filename = EXCLUDED.original_filename,
            original_size_bytes = EXCLUDED.original_size_bytes,
            final_filename = EXCLUDED.final_filename,
            final_size_bytes = EXCLUDED.final_size_bytes,
            encoding_savings_pct = EXCLUDED.encoding_savings_pct,
            temp_path = EXCLUDED.temp_path,
            local_path = EXCLUDED.local_path,
            rclone_remote = EXCLUDED.rclone_remote,
            rclone_path = EXCLUDED.rclone_path,
            discovered_at = EXCLUDED.discovered_at,
            download_started_at = EXCLUDED.download_started_at,
            downloaded_at = EXCLUDED.downloaded_at,
            encode_started_at = EXCLUDED.encode_started_at,
            encoded_at = EXCLUDED.encoded_at,
            upload_started_at = EXCLUDED.upload_started_at,
            uploaded_at = EXCLUDED.uploaded_at,
            updated_at = EXCLUDED.updated_at,
            pending_neon_sync = EXCLUDED.pending_neon_sync
        """

        def prep_video(v):
            v.updated_at = datetime.now(timezone.utc).isoformat()
            tj = json.dumps(v.tags) if v.tags is not None else None
            cj = json.dumps(v.categories) if v.categories is not None else None
            return (
                v.video_id, v.source_name, v.source_type, v.source_url, v.run_id,
                v.title, v.description, v.channel_name, v.channel_id, v.upload_date,
                v.duration_seconds, v.view_count, v.like_count, v.thumbnail_url,
                tj, cj, v.youtube_url, v.status, v.failed_stage,
                v.failed_reason, v.retry_count, v.deleted, v.deleted_detected_at,
                v.original_filename, v.original_size_bytes, v.final_filename, v.final_size_bytes,
                v.encoding_savings_pct, v.temp_path, v.local_path, v.rclone_remote,
                v.rclone_path, v.discovered_at, v.download_started_at, v.downloaded_at,
                v.encode_started_at, v.encoded_at, v.upload_started_at, v.uploaded_at,
                v.updated_at, v.pending_neon_sync
            )

        tuples = [prep_video(v) for v in videos]

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, sql, tuples)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to batch upsert to Neon DB: {e}")
            self.conn.rollback()
            return False

    def count(self) -> Optional[int]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM videos")
                return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to count Neon DB rows: {e}")
            self.conn.rollback()
            return None

    def max_updated_at(self) -> Optional[str]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT MAX(updated_at) FROM videos")
                return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get max_updated_at from Neon DB: {e}")
            self.conn.rollback()
            return None

    def _row_to_video(self, row, desc) -> Video:
        data = {}
        for (col, val) in zip(desc, row):
            if col.name in ('tags', 'categories') and isinstance(val, str):
                try:
                    data[col.name] = json.loads(val)
                except:
                    data[col.name] = val
            else:
                data[col.name] = val
        return Video(**data)

    def get_since(self, updated_at: str) -> list[Video]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM videos WHERE updated_at > %s", (updated_at,))
                desc = cur.description
                rows = cur.fetchall()
                return [self._row_to_video(row, desc) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get updated rows from Neon DB: {e}")
            self.conn.rollback()
            return []

    def close(self) -> None:
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
