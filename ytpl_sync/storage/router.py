from typing import Any
from ytpl_sync.models import Video, VideoStatus, FailedStage
from ytpl_sync.storage.local_storage import LocalStorage
from ytpl_sync.storage.gdrive_storage import GDriveStorage

class StorageRouter:
    def __init__(self, app_config, rclone_path: str):
        self.app_config = app_config
        self.rclone_path = rclone_path
        self.local_storage = LocalStorage()
        
    def store(self, video: Video, effective_dest_config: Any) -> Video:
        mode = "local"
        dest_path = "~/ytpl-downloads"
        accounts = []
        
        if isinstance(effective_dest_config, dict):
            if "mode" in effective_dest_config:
                dest_dict = effective_dest_config
            else:
                dest_dict = effective_dest_config.get("destination", {})
                
            mode = dest_dict.get("mode", "local")
            local_conf = dest_dict.get("local", {})
            if local_conf:
                dest_path = local_conf.get("path", "~/ytpl-downloads")
                
            gdrive_conf = dest_dict.get("gdrive", {})
            if gdrive_conf:
                accounts = gdrive_conf.get("accounts", [])
                
        else:
            if hasattr(effective_dest_config, "mode"):
                dest_obj = effective_dest_config
            else:
                dest_obj = getattr(effective_dest_config, "destination", effective_dest_config)
                
            mode = getattr(dest_obj, "mode", "local")
            local_conf = getattr(dest_obj, "local", None)
            if local_conf:
                dest_path = getattr(local_conf, "path", "~/ytpl-downloads")
                
            gdrive_conf = getattr(dest_obj, "gdrive", None)
            if gdrive_conf:
                accounts = getattr(gdrive_conf, "accounts", [])
                
        if mode == "local":
            return self.local_storage.store(video, dest_path)
        elif mode == "gdrive":
            gdrive_storage = GDriveStorage(accounts, self.rclone_path)
            return gdrive_storage.upload(video)
        else:
            video.status = VideoStatus.FAILED
            video.failed_stage = FailedStage.UPLOAD
            video.failed_reason = f"Unknown storage mode: {mode}"
            return video
