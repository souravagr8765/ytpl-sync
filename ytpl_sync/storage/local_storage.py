import os
import shutil
import re
from pathlib import Path
from datetime import datetime, timezone

from ytpl_sync.models import Video, VideoStatus

class LocalStorage:
    def store(self, video: Video, dest_path: str) -> Video:
        expanded_dest = Path(dest_path).expanduser()
        
        safe_source_name = re.sub(r'[\\/*?:"<>|]', "", video.source_name)
        target_dir = expanded_dest / safe_source_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        source_file = video.final_filename if video.final_filename else video.temp_path
        if not source_file or not os.path.exists(source_file):
            video.status = VideoStatus.FAILED
            video.failed_stage = "UPLOAD"
            video.failed_reason = f"Source file not found: {source_file}"
            return video
            
        file_name = os.path.basename(source_file)
        final_dest_path = target_dir / file_name
        
        shutil.move(source_file, final_dest_path)
        
        video.local_path = str(final_dest_path)
        video.status = VideoStatus.UPLOADED
        video.uploaded_at = datetime.now(timezone.utc).isoformat()
        
        return video
