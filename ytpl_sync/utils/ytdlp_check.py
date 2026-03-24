import subprocess
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def check_ytdlp(auto_update: bool) -> str:
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
        version_str = result.stdout.strip()
        
        match = re.search(r'(\d{4})\.(\d{2})\.(\d{2})', version_str)
        if match:
            version_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if datetime.now() - version_date > timedelta(days=30):
                logger.warning(f"yt-dlp version {version_str} is over 30 days old. Consider updating.")
        
        if auto_update:
            update_result = subprocess.run(["yt-dlp", "-U"], capture_output=True, text=True)
            logger.info(update_result.stdout.strip())
            
        return version_str
        
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not found. Please install it (e.g., 'pip install yt-dlp') and ensure it is in your PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error checking yt-dlp version: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error running yt-dlp: {e}")
