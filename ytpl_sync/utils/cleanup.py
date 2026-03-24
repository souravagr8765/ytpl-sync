import os
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def cleanup_orphan_files(temp_dir: str, max_age_hours: int = 24) -> int:
    count = 0
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    
    temp_path = Path(temp_dir)
    if not temp_path.exists() or not temp_path.is_dir():
        return 0
        
    patterns = ["*.part", "*.ytdl", "*.temp", "*.tmp"]
    
    for pattern in patterns:
        for file_path in temp_path.rglob(pattern):
            try:
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    if now - mtime > max_age_seconds:
                        file_path.unlink()
                        count += 1
                        logger.info(f"Deleted orphan file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")
                
    return count
