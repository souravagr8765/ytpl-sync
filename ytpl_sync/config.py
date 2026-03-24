import os
from pathlib import Path
from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

class RootPathValidatorModel(BaseModel):
    @field_validator('*', mode='before')
    @classmethod
    def expand_tilde(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith('~'):
            return str(Path(v).expanduser())
        return v

class SettingsConfig(RootPathValidatorModel):
    ffmpeg_path: Optional[str] = None
    rclone_path: Optional[str] = None
    temp_dir: Optional[str] = None
    lock_file: str = "~/.ytpl-sync.lock"
    log_file: str = "~/.ytpl-sync.log"
    min_free_gb: int = 5
    only_run_between: Optional[str] = None
    ytdlp_auto_update: bool = False
    cookies_file: Optional[str] = None
    max_retries: int = 3
    dry_run: bool = False

class EncodingConfig(BaseModel):
    enabled: bool = True
    encoder: Literal["software", "nvenc", "vaapi", "videotoolbox"] = "software"
    preset: str = "medium"
    crf: int = 28
    audio_bitrate: str = "96k"

class QualityConfig(BaseModel):
    max_resolution: Literal[480, 720, 1080, 1440, 2160] = 1080
    prefer_format: Literal["webm", "mp4", "any"] = "webm"

class LocalDestConfig(RootPathValidatorModel):
    path: str = "~/ytpl-downloads"

class GDriveAccountConfig(BaseModel):
    name: str
    rclone_remote: str
    quota_gb: int
    upload_folder: str

class GDriveDestConfig(BaseModel):
    accounts: List[GDriveAccountConfig] = Field(default_factory=list)

class DestinationConfig(BaseModel):
    mode: Literal["local", "gdrive"] = "local"
    local: Optional[LocalDestConfig] = None
    gdrive: Optional[GDriveDestConfig] = None

class EmailNotificationsConfig(BaseModel):
    enabled: bool = True
    send_report_on_activity: bool = True
    send_on_failure: bool = True

class TelegramNotificationsConfig(BaseModel):
    enabled: bool = True
    send_report_on_activity: bool = True
    send_on_failure: bool = True

class NotificationsConfig(BaseModel):
    email: EmailNotificationsConfig = Field(default_factory=EmailNotificationsConfig)
    telegram: TelegramNotificationsConfig = Field(default_factory=TelegramNotificationsConfig)

class SourceFiltersConfig(BaseModel):
    after_date: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)
    min_duration_seconds: Optional[int] = None
    max_duration_seconds: Optional[int] = None

class SourceConfig(BaseModel):
    type: str
    name: str
    url: str
    filters: Optional[SourceFiltersConfig] = None
    destination: Optional[DestinationConfig] = None
    encoding: Optional[Dict[str, Any]] = None
    quality: Optional[Dict[str, Any]] = None

class AppConfig(BaseModel):
    settings: SettingsConfig
    encoding: EncodingConfig = Field(default_factory=EncodingConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    destination: DestinationConfig = Field(default_factory=DestinationConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    sources: List[SourceConfig] = Field(default_factory=list)

    def get_effective_config(self, source: SourceConfig) -> Dict[str, Any]:
        """Returns the merged encoding, quality, and destination specs for a given source."""
        result = {
            "destination": source.destination.model_dump() if source.destination else self.destination.model_dump(),
            "encoding": self.encoding.model_dump(),
            "quality": self.quality.model_dump()
        }
        
        if source.encoding:
            result["encoding"].update(source.encoding)
        if source.quality:
            result["quality"].update(source.quality)
            
        return result
