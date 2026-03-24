from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from .models import Video
import uuid

@dataclass
class RunContext:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
    dry_run: bool = False
    discovered: int = 0
    skipped: int = 0
    downloaded: int = 0
    encoded: int = 0
    uploaded: int = 0
    failed: int = 0
    abandoned: int = 0
    newly_deleted: int = 0
    encoding_savings_mb: float = 0.0
    videos_this_run: List[Video] = field(default_factory=list)

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "dry_run": self.dry_run,
            "discovered": self.discovered,
            "skipped": self.skipped,
            "downloaded": self.downloaded,
            "encoded": self.encoded,
            "uploaded": self.uploaded,
            "failed": self.failed,
            "abandoned": self.abandoned,
            "newly_deleted": self.newly_deleted,
            "encoding_savings_mb": self.encoding_savings_mb,
            "videos_touched_count": len(self.videos_this_run)
        }
