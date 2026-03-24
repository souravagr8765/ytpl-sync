import pytest
import sqlite3
import tempfile
import yaml
from pathlib import Path
from ytpl_sync.models import Video, VideoStatus
from ytpl_sync.config import AppConfig

@pytest.fixture
def tmp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)

@pytest.fixture
def sample_video():
    return Video(
        video_id="test_vid_123",
        source_name="test_source",
        source_url="https://youtube.com/watch?v=test_vid_123",
        run_id="run_1",
        title="Test Video",
        description="A test video",
        upload_date="20231010",
        duration_seconds=120,
        status=VideoStatus.PENDING,
        url="https://youtube.com/watch?v=test_vid_123",
    )

@pytest.fixture
def sample_config():
    return AppConfig(**{
        "database": {"local_path": ":memory:"},
        "sources": [
            {
                "name": "test_source",
                "url": "https://example.com"
            }
        ]
    })
