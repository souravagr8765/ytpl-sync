import logging
from typing import Optional
import yt_dlp

logger = logging.getLogger(__name__)

class ChannelResolver:
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
            logger.error(f"DownloadError resolving channel {url}: {e}")
            return []

        if not info or 'entries' not in info:
            logger.error(f"No entries found for channel {url}")
            return []

        entries = info['entries']
        initial_count = len(entries)
        logger.info(f"Found {initial_count} videos in channel {url} before filtering")

        results = []
        filters = getattr(source_config, 'filters', None)

        for entry in entries:
            if not entry:
                continue

            if filters:
                after_date = getattr(filters, 'after_date', None)
                if after_date and entry.get('upload_date'):
                    if str(entry.get('upload_date')) < str(after_date):
                        continue

                keywords = getattr(filters, 'keywords', None)
                if keywords:
                    title_lower = (entry.get('title') or '').lower()
                    if not any(k.lower() in title_lower for k in keywords):
                        continue

                exclude_keywords = getattr(filters, 'exclude_keywords', None)
                if exclude_keywords:
                    title_lower = (entry.get('title') or '').lower()
                    if any(ek.lower() in title_lower for ek in exclude_keywords):
                        continue

                min_duration = getattr(filters, 'min_duration_seconds', None)
                if min_duration is not None and entry.get('duration') is not None:
                    if entry.get('duration') < min_duration:
                        continue

                max_duration = getattr(filters, 'max_duration_seconds', None)
                if max_duration is not None and entry.get('duration') is not None:
                    if entry.get('duration') > max_duration:
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

        logger.info(f"Retained {len(results)} videos after filtering channel {url}")
        return results
