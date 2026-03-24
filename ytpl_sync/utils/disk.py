import os
import shutil
import logging

logger = logging.getLogger(__name__)

class DiskSpaceError(Exception):
    def __init__(self, available_gb: float, required_gb: float):
        self.available_gb = available_gb
        self.required_gb = required_gb
        super().__init__(f"Insufficient disk space. Available: {available_gb:.2f} GB, Required: {required_gb:.2f} GB")

def check_free_space(path: str, min_free_gb: float) -> None:
    expanded_path = os.path.expanduser(path)
    
    check_path = expanded_path
    while not os.path.exists(check_path):
        parent = os.path.dirname(check_path)
        if parent == check_path:
            break
        check_path = parent

    total, used, free = shutil.disk_usage(check_path)
    free_gb = free / (1024**3)
    logger.debug(f"Available free space at {expanded_path}: {free_gb:.2f} GB")
    
    if free_gb < min_free_gb:
        raise DiskSpaceError(free_gb, min_free_gb)
