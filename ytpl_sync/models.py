from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class VideoStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    ENCODING = "ENCODING"
    ENCODED = "ENCODED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    DELETED = "DELETED"

class FailedStage(str, Enum):
    DOWNLOAD = "DOWNLOAD"
    ENCODE = "ENCODE"
    UPLOAD = "UPLOAD"

class SourceType(str, Enum):
    PLAYLIST = "PLAYLIST"
    CHANNEL = "CHANNEL"

@dataclass
class Video:
    video_id: str
    source_name: str
    source_type: str
    source_url: str
    run_id: str

    # YouTube metadata
    title: Optional[str] = None
    description: Optional[str] = None
    channel_name: Optional[str] = None
    channel_id: Optional[str] = None
    upload_date: Optional[str] = None          # YYYY-MM-DD
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[list[str]] = None
    categories: Optional[list[str]] = None
    youtube_url: Optional[str] = None

    # Status & resume
    status: str = VideoStatus.PENDING
    failed_stage: Optional[str] = None
    failed_reason: Optional[str] = None
    retry_count: int = 0

    # Deletion
    deleted: bool = False
    deleted_detected_at: Optional[str] = None

    # File info
    original_filename: Optional[str] = None
    original_size_bytes: Optional[int] = None
    final_filename: Optional[str] = None
    final_size_bytes: Optional[int] = None
    encoding_savings_pct: Optional[float] = None

    # Paths
    temp_path: Optional[str] = None
    local_path: Optional[str] = None

    # Drive info
    rclone_remote: Optional[str] = None
    rclone_path: Optional[str] = None

    # Timestamps (ISO strings)
    discovered_at: Optional[str] = None
    download_started_at: Optional[str] = None
    downloaded_at: Optional[str] = None
    encode_started_at: Optional[str] = None
    encoded_at: Optional[str] = None
    upload_started_at: Optional[str] = None
    uploaded_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Sync flag
    pending_neon_sync: bool = False
