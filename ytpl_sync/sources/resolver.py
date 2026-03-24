from typing import Optional
from ytpl_sync.sources.playlist import PlaylistResolver
from ytpl_sync.sources.channel import ChannelResolver

def resolve_source(source_config, cookies_file: Optional[str]) -> list[dict]:
    source_type = source_config.type.lower()
    
    if source_type == 'playlist':
        resolver = PlaylistResolver()
    elif source_type == 'channel':
        resolver = ChannelResolver()
    else:
        raise ValueError(f"Unknown source type: {source_config.type}")

    videos = resolver.resolve(source_config, cookies_file)
    
    for video in videos:
        video['source_name'] = source_config.name
        video['source_type'] = source_config.type
        video['source_url'] = source_config.url

    return videos
