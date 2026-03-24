import os
import json
import logging
import subprocess
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from ytpl_sync.models import Video, VideoStatus, FailedStage

logger = logging.getLogger(__name__)

class StorageFullError(Exception):
    pass

class GDriveStorage:
    def __init__(self, accounts: list, rclone_path: str):
        self.accounts = accounts
        self.rclone_path = rclone_path or "rclone"

    def _get_used_quota(self, rclone_remote: str) -> Optional[float]:
        try:
            cmd = [self.rclone_path, "about", f"{rclone_remote}:", "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            used_bytes = data.get("used", 0)
            used_gb = used_bytes / (1024**3)
            return used_gb
        except Exception as e:
            logger.warning(f"Failed to get quota for {rclone_remote}: {e}")
            return None

    def _select_account(self) -> Optional[dict]:
        for account in self.accounts:
            if hasattr(account, "model_dump"):
                account_dict = account.model_dump()
            elif hasattr(account, "dict"):
                account_dict = account.dict()
            else:
                account_dict = account
            
            rclone_remote = account_dict.get("rclone_remote")
            quota_gb = account_dict.get("quota_gb", 15)
            
            used_gb = self._get_used_quota(rclone_remote)
            if used_gb is not None:
                if used_gb < (quota_gb * 0.90):
                    return account_dict
                    
        return None

    def upload(self, video: Video) -> Video:
        account = self._select_account()
        if not account:
            raise StorageFullError("All Google Drive accounts are at 90% capacity.")
            
        source_file = video.final_filename if video.final_filename else video.temp_path
        if not source_file or not os.path.exists(source_file):
            video.status = VideoStatus.FAILED
            video.failed_stage = FailedStage.UPLOAD
            video.failed_reason = f"Source file not found: {source_file}"
            return video
            
        rclone_remote = account.get("rclone_remote")
        upload_folder = account.get("upload_folder", "").strip("/")
        
        filename = os.path.basename(source_file)
        safe_source_name = re.sub(r'[\\/*?:"<>|]', "", video.source_name)
        
        if upload_folder:
            remote_dest_dir = f"{rclone_remote}:{upload_folder}/{safe_source_name}"
            rclone_path = f"{upload_folder}/{safe_source_name}/{filename}"
        else:
            remote_dest_dir = f"{rclone_remote}:{safe_source_name}"
            rclone_path = f"{safe_source_name}/{filename}"
            
        video.status = VideoStatus.UPLOADING
        
        try:
            cmd = [
                self.rclone_path,
                "copy",
                source_file,
                remote_dest_dir,
                "--progress=false",
                "--stats=0"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                video.rclone_remote = rclone_remote
                video.rclone_path = rclone_path
                video.status = VideoStatus.UPLOADED
                video.uploaded_at = datetime.now(timezone.utc).isoformat()
                
                try:
                    os.remove(source_file)
                except OSError as e:
                    logger.warning(f"Failed to delete local temp file {source_file}: {e}")
            else:
                video.status = VideoStatus.FAILED
                video.failed_stage = FailedStage.UPLOAD
                video.failed_reason = result.stderr.strip() or "rclone copy failed with no stderr output"
                
        except Exception as e:
            video.status = VideoStatus.FAILED
            video.failed_stage = FailedStage.UPLOAD
            video.failed_reason = str(e)
            
        return video
