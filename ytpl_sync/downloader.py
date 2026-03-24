import os
import glob
import logging
from typing import Optional
from datetime import datetime, timezone

import yt_dlp

from ytpl_sync.models import Video, VideoStatus, FailedStage

logger = logging.getLogger(__name__)

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

class Downloader:
    def __init__(self, ffmpeg_path: str, cookies_file: Optional[str]):
        self.ffmpeg_path = ffmpeg_path
        self.cookies_file = cookies_file

    def download(self, video: Video, output_dir: str, quality_config, run_id: str) -> Video:
        """
        Downloads a single video. Returns a Video object with status DOWNLOADED or FAILED.
        """
        # Safety net: Never re-download if status is already complete.
        if video.status in (
            VideoStatus.DOWNLOADED.value,
            VideoStatus.ENCODED.value,
            VideoStatus.UPLOADING.value,
            VideoStatus.UPLOADED.value,
            VideoStatus.DOWNLOADED,
            VideoStatus.ENCODED,
            VideoStatus.UPLOADING,
            VideoStatus.UPLOADED,
        ):
            logger.warning(f"Safety net: Attempted to download video {video.video_id} which has status {video.status}")
            return video

        # 1. Update video status for download start
        video.status = VideoStatus.DOWNLOADING
        video.download_started_at = now()
        video.run_id = run_id

        # 2. Build yt-dlp format selector based on quality_config
        res = quality_config.max_resolution
        prefer_format = quality_config.prefer_format

        if prefer_format == "webm":
            format_selector = f"bestvideo[ext=webm][height<={res}]+bestaudio[ext=webm]/bestvideo[height<={res}]+bestaudio[ext=webm]/bestvideo[height<={res}]+bestaudio/best[height<={res}]"
        elif prefer_format == "mp4":
            format_selector = f"bestvideo[ext=mp4][height<={res}]+bestaudio[ext=m4a]/best[ext=mp4][height<={res}]/best[height<={res}]"
        elif prefer_format == "any":
            format_selector = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]"
        else:
            format_selector = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]"

        # 3. ydl_opts
        ydl_opts = {
            "format": format_selector,
            "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "concurrent_fragment_downloads": 4,
            "noprogress": True,
            "ffmpeg_location": self.ffmpeg_path
        }

        if self.cookies_file:
            ydl_opts["cookiefile"] = self.cookies_file

        try:
            # 4. Run yt_dlp.YoutubeDL(ydl_opts).download
            url_to_download = video.youtube_url or f"https://www.youtube.com/watch?v={video.video_id}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url_to_download])

            # 5. Find the downloaded file (glob output_dir/video_id.*).
            search_pattern = os.path.join(output_dir, f"{video.video_id}.*")
            files = glob.glob(search_pattern)
            
            # Filter out yt-dlp temp files
            files = [f for f in files if not f.endswith(".part") and not f.endswith(".ytdl")]

            if not files:
                raise FileNotFoundError(f"Downloaded file not found for {video.video_id}")

            downloaded_file = files[0]

            # 6. On success
            video.status = VideoStatus.DOWNLOADED
            video.original_filename = os.path.basename(downloaded_file)
            video.original_size_bytes = os.path.getsize(downloaded_file)
            video.downloaded_at = now()
            video.temp_path = downloaded_file

        except yt_dlp.utils.DownloadError as e:
            # 7. On Error
            logger.error(f"yt-dlp error downloading video {video.video_id}: {e}")
            video.status = VideoStatus.FAILED
            video.failed_stage = FailedStage.DOWNLOAD
            video.failed_reason = str(e)
        except Exception as e:
            logger.error(f"Unexpected error downloading video {video.video_id}: {e}")
            video.status = VideoStatus.FAILED
            video.failed_stage = FailedStage.DOWNLOAD
            video.failed_reason = str(e)

        # 8. Return video
        return video
