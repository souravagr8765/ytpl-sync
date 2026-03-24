import logging
from typing import Optional
from ytpl_sync.models import Video, VideoStatus

from .sqlite_backend import SQLiteBackend
from .neon_backend import NeonBackend

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, sqlite: SQLiteBackend, neon: NeonBackend):
        self.sqlite = sqlite
        self.neon = neon
        self._queued_for_neon: list[Video] = []

    def initialize(self) -> None:
        self.sqlite.initialize()
        self.neon.initialize()

    def upsert_video(self, video: Video) -> None:
        video.pending_neon_sync = True
        self.sqlite.upsert(video)
        self._queued_for_neon.append(video)

    def flush_to_neon(self) -> None:
        if not self._queued_for_neon:
            return
            
        success = self.neon.upsert_many(self._queued_for_neon)
        if success:
            for v in self._queued_for_neon:
                v.pending_neon_sync = False
            self.sqlite.upsert_many(self._queued_for_neon)
        
        self._queued_for_neon.clear()

    def get_video(self, video_id: str) -> Optional[Video]:
        return self.sqlite.get(video_id)

    def list_all_video_ids(self) -> set[str]:
        videos = self.sqlite.get_all()
        return {v.video_id for v in videos}

    def get_resumable(self) -> list[Video]:
        resumable_statuses = [
            VideoStatus.PENDING,
            VideoStatus.DOWNLOADING,
            VideoStatus.DOWNLOADED,
            VideoStatus.ENCODING,
            VideoStatus.ENCODED,
            VideoStatus.UPLOADING,
            VideoStatus.FAILED,
        ]
        return self.sqlite.get_by_status(*resumable_statuses)

    def get_pending_neon_sync(self) -> list[Video]:
        return self.sqlite.get_pending_neon_sync()
