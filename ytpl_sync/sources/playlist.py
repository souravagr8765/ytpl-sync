import logging
from typing import Optional
import yt_dlp

logger = logging.getLogger(__name__)

class PlaylistResolver:
    def resolve(self, source_config, cookies_file: Optional[str]) -> list[dict]:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
        }
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file

        url = source_config.url
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"DownloadError resolving playlist {url}: {e}")
            return []

        if not info or 'entries' not in info:
            logger.error(f"No entries found for playlist {url}")
            return []

        entries = info['entries']
        logger.info(f"Found {len(entries)} videos in playlist {url}")

        results = []
        for entry in entries:
            if not entry:
                continue
                
            results.append({
                'id': entry.get('id'),
                'title': entry.get('title'),
                'url': entry.get('url'),
                'duration': entry.get('duration'),
                'upload_date': entry.get('upload_date'),
                'view_count': entry.get('view_count'),
                'like_count': entry.get('like_count'),
                'channel': entry.get('channel'),
                'channel_id': entry.get('channel_id'),
                'thumbnails': entry.get('thumbnails'),
                'tags': entry.get('tags'),
                'categories': entry.get('categories'),
                'description': entry.get('description'),
            })

        return results
