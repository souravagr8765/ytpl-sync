"""
Report and message generation module for ytpl-sync.
"""
import logging
from datetime import datetime
from ytpl_sync.models import Video, VideoStatus
from ytpl_sync.run_context import RunContext

logger = logging.getLogger(__name__)

# Use a static version or try import
VERSION = "1.0.0"
try:
    from ytpl_sync import __version__
    VERSION = __version__
except ImportError:
    pass

class ReportBuilder:
    def _format_duration(self, seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"

    def build_email_report(self, ctx: RunContext) -> str:
        try:
            now = datetime.utcnow()
            duration_secs = int((now - ctx.started_at).total_seconds())
            duration_str = self._format_duration(duration_secs)
            
            # Calculate average encoding savings
            encoded_vids = [v for v in ctx.videos_this_run if v.encoding_savings_pct is not None]
            avg_savings = sum(v.encoding_savings_pct for v in encoded_vids) / len(encoded_vids) if encoded_vids else None

            lines = [
                "ytpl-sync Run Report",
                "====================",
                f"Run ID: {ctx.run_id}",
                f"Timestamp: {now.isoformat()}",
                f"Duration: {duration_str}",
                "",
                "Summary:",
                "--------",
                f"Discovered: {ctx.discovered}",
                f"Skipped: {ctx.skipped}",
                f"Downloaded: {ctx.downloaded}",
                f"Encoded: {ctx.encoded}",
                f"Uploaded: {ctx.uploaded}",
                f"Failed: {ctx.failed}",
                f"Abandoned: {ctx.abandoned}",
                f"Newly Deleted: {ctx.newly_deleted}",
                ""
            ]
            
            if avg_savings is not None:
                lines.append(f"Average encoding savings: {avg_savings:.2f}%")
                lines.append("")

            # Section: Downloaded this run
            uploaded_videos = [v for v in ctx.videos_this_run if v.status == VideoStatus.UPLOADED]
            if uploaded_videos:
                lines.append("Downloaded this run:")
                lines.append("--------------------")
                for v in uploaded_videos:
                    orig_mb = (v.original_size_bytes or 0) / (1024*1024)
                    final_mb = (v.final_size_bytes or 0) / (1024*1024)
                    size_str = f"{orig_mb:.1f}MB -> {final_mb:.1f}MB"
                    if v.rclone_remote and v.rclone_path:
                        dest = f"{v.rclone_remote}:{v.rclone_path}"
                    else:
                        dest = v.local_path or "Unknown"
                    lines.append(f"- {v.title or v.video_id} ({v.source_name}) | {size_str} | Dest: {dest}")
                lines.append("")

            # Section: Failed
            failed_videos = [v for v in ctx.videos_this_run if v.status in (VideoStatus.FAILED, VideoStatus.ABANDONED)]
            if failed_videos:
                lines.append("Failed:")
                lines.append("-------")
                for v in failed_videos:
                    reason = v.failed_reason or "Unknown"
                    lines.append(f"- {v.title or v.video_id} | Stage: {v.failed_stage} | Reason: {reason} | Retries: {v.retry_count}")
                lines.append("")

            # Section: Newly deleted on YouTube
            deleted_videos = [v for v in ctx.videos_this_run if v.status == VideoStatus.DELETED]
            if deleted_videos:
                lines.append("Newly deleted on YouTube:")
                lines.append("-------------------------")
                for v in deleted_videos:
                    lines.append(f"- {v.title or v.video_id}")
                lines.append("")

            lines.append(f"ytpl-sync v{VERSION} | Run ID: {ctx.run_id}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error building email report: {e}")
            return "Error generating email report."

    def build_telegram_message(self, ctx: RunContext) -> str:
        try:
            # Calculate average encoding savings
            encoded_vids = [v for v in ctx.videos_this_run if v.encoding_savings_pct is not None]
            avg_savings = sum(v.encoding_savings_pct for v in encoded_vids) / len(encoded_vids) if encoded_vids else None

            lines = [
                "ytpl-sync run complete",
                f"Stats: Discovered: {ctx.discovered} | Downloaded: {ctx.downloaded} | Encoded: {ctx.encoded} | Uploaded: {ctx.uploaded} | Failed: {ctx.failed} | Deleted: {ctx.newly_deleted}"
            ]

            failed_videos = [v for v in ctx.videos_this_run if v.status in (VideoStatus.FAILED, VideoStatus.ABANDONED)]
            if failed_videos:
                lines.append("Failed videos:")
                for i, v in enumerate(failed_videos):
                    if i < 5:
                        lines.append(f"- {v.title or v.video_id}")
                    else:
                        lines.append(f"+ {len(failed_videos) - 5} more")
                        break

            if avg_savings is not None:
                lines.append(f"Avg encoding savings: {avg_savings:.2f}%")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error building telegram message: {e}")
            return "ytpl-sync run complete (Error generating full message)"

    def build_failure_alert_email(self, video: Video) -> str:
        try:
            lines = [
                f"Title: {video.title or video.video_id}",
                f"Video ID: {video.video_id}",
                f"YouTube URL: {video.youtube_url or f'https://youtube.com/watch?v={video.video_id}'}",
                f"Failed Stage: {video.failed_stage}",
                f"Failed Reason: {video.failed_reason}",
                f"Retry Count: {video.retry_count}"
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error building failure alert email: {e}")
            return "Error generating failure alert email."

    def build_failure_alert_telegram(self, video: Video) -> str:
        try:
            reason = str(video.failed_reason or "Unknown")[:80]
            title = video.title or video.video_id
            return f"ABANDONED: {title} | Stage: {video.failed_stage} | {reason}"
        except Exception as e:
            logger.error(f"Error building failure alert telegram: {e}")
            return "ABANDONED: Error formatting failure message"
