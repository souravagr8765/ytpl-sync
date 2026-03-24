import subprocess
import logging
import shutil
import os
from typing import Optional

logger = logging.getLogger(__name__)

def run_command(cmd: list[str], description: str, timeout: int = 3600, raise_on_error: bool = True) -> tuple[int, str, str]:
    logger.debug(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    stdout = result.stdout
    stderr = result.stderr
    
    logger.debug(f"stdout for '{description}':\n{stdout}")
    logger.warning(f"stderr for '{description}':\n{stderr}")
    
    if result.returncode != 0 and raise_on_error:
        raise RuntimeError(f"Command failed for '{description}' with return code {result.returncode}:\n{stderr}")
        
    return result.returncode, stdout, stderr

def find_executable(name: str, config_override: Optional[str] = None) -> str:
    if config_override is not None:
        if os.path.exists(config_override) and os.access(config_override, os.X_OK):
            return config_override
            
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"Executable '{name}' not found. Please install '{name}' (e.g., ffmpeg and rclone) and ensure it's in your PATH, or provide a valid override path.")
        
    return executable
