import pytest
from unittest.mock import patch, MagicMock
from ytpl_sync.db.sqlite_backend import SQLiteBackend
from ytpl_sync.models import VideoStatus

def test_initialize_creates_table(tmp_db_path):
    db = SQLiteBackend(tmp_db_path)
    db.initialize()
    cur = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
    assert cur.fetchone() is not None

def test_upsert_and_get(tmp_db_path, sample_video):
    db = SQLiteBackend(tmp_db_path)
    db.initialize()
    db.upsert(sample_video)
    saved = db.get(sample_video.video_id)
    assert saved is not None
    assert saved.video_id == sample_video.video_id
    assert saved.status == sample_video.status

def test_upsert_updates(tmp_db_path, sample_video):
    db = SQLiteBackend(tmp_db_path)
    db.initialize()
    db.upsert(sample_video)
    sample_video.status = VideoStatus.ENCODED
    db.upsert(sample_video)
    saved = db.get(sample_video.video_id)
    assert saved.status == VideoStatus.ENCODED.value

def test_list_all_video_ids(tmp_db_path, sample_video):
    db = SQLiteBackend(tmp_db_path)
    db.initialize()
    sample_video.video_id = "1"
    db.upsert(sample_video)
    sample_video.video_id = "2"
    db.upsert(sample_video)
    sample_video.video_id = "3"
    db.upsert(sample_video)
    videos = db.get_all()
    ids = [v.video_id for v in videos]
    assert set(ids) == {"1", "2", "3"}

def test_get_by_status(tmp_db_path, sample_video):
    db = SQLiteBackend(tmp_db_path)
    db.initialize()
    sample_video.video_id = "1"
    sample_video.status = VideoStatus.PENDING
    db.upsert(sample_video)
    sample_video.video_id = "2"
    sample_video.status = VideoStatus.ENCODED
    db.upsert(sample_video)
    vids = db.get_by_status(VideoStatus.ENCODED.value)
    assert len(vids) == 1
    assert vids[0].video_id == "2"

def test_flush_to_neon_on_failure(tmp_db_path, sample_video):
    db = SQLiteBackend(tmp_db_path)
    db.initialize()
    
    sample_video.pending_neon_sync = True
    db.upsert(sample_video)
    
    videos = db.get_pending_neon_sync()
    assert len(videos) == 1
    assert videos[0].video_id == sample_video.video_id
