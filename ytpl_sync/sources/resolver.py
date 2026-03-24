from typing import Optional
from datetime import datetime
from ytpl_sync.sources.playlist import PlaylistResolver
from ytpl_sync.sources.channel import ChannelResolver
from ytpl_sync.models import Video

def resolve_source(source_config, cookies_file: Optional[str], run_id: str) -> list[Video]:
    source_type = source_config.type.lower()
    
    if source_type == 'playlist':
        resolver = PlaylistResolver()
    elif source_type == 'channel':
        resolver = ChannelResolver()
    else:
        raise ValueError(f"Unknown source type: {source_config.type}")

    video_dicts = resolver.resolve(source_config, cookies_file)
    videos = []
    
    for v in video_dicts:
        thumbnail_url = None
        if v.get('thumbnails'):
            thumbnail_url = v['thumbnails'][-1].get('url') if isinstance(v['thumbnails'], list) and len(v['thumbnails']) > 0 else None
            
        upload_date = v.get('upload_date')
        if upload_date and len(upload_date) == 8 and upload_date.isdigit():
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        video = Video(
            video_id=v.get('id'),
            source_name=source_config.name,
            source_type=source_config.type,
            source_url=source_config.url,
            run_id=run_id,
            title=v.get('title'),
            description=v.get('description'),
            channel_name=v.get('channel'),
            channel_id=v.get('channel_id'),
            upload_date=upload_date,
            duration_seconds=v.get('duration'),
            view_count=v.get('view_count'),
            like_count=v.get('like_count'),
            thumbnail_url=thumbnail_url,
            tags=v.get('tags'),
            categories=v.get('categories'),
            youtube_url=v.get('url') or f"https://www.youtube.com/watch?v={v.get('id')}",
            discovered_at=datetime.utcnow().isoformat()
        )
        videos.append(video)

    return videos
