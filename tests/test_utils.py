import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import os
import tempfile
from pathlib import Path
from ytpl_sync.utils.time_window import is_within_time_window
from ytpl_sync.utils.disk import check_free_space, DiskSpaceError
from ytpl_sync.utils.cleanup import cleanup_orphan_files

def test_time_window_inside():
    with patch('ytpl_sync.utils.time_window.datetime') as mock_dt:
        mock_dt.datetime.now.return_value.time.return_value = datetime(2023, 1, 1, 10, 0).time()
        assert is_within_time_window("09:00-11:00") is True

def test_time_window_outside():
    with patch('ytpl_sync.utils.time_window.datetime') as mock_dt:
        mock_dt.datetime.now.return_value.time.return_value = datetime(2023, 1, 1, 12, 0).time()
        assert is_within_time_window("09:00-11:00") is False

def test_time_window_none():
    assert is_within_time_window(None) is True

def test_time_window_midnight_wrap():
    with patch('ytpl_sync.utils.time_window.datetime') as mock_dt:
        mock_dt.datetime.strptime = datetime.strptime
        
        mock_dt.datetime.now.return_value.time.return_value = datetime(2023, 1, 1, 23, 30).time()
        assert is_within_time_window("23:00-01:00") is True
        
        mock_dt.datetime.now.return_value.time.return_value = datetime(2023, 1, 1, 0, 30).time()
        assert is_within_time_window("23:00-01:00") is True
        
        mock_dt.datetime.now.return_value.time.return_value = datetime(2023, 1, 1, 2, 0).time()
        assert is_within_time_window("23:00-01:00") is False

@patch('shutil.disk_usage')
def test_disk_check_passes(mock_du):
    class MockNamedTuple:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    mock_du.return_value = MockNamedTuple(total=1000**3, used=500**3, free=500**3)
    # Does not return anything on success, just shouldn't raise
    check_free_space("/", 10)

@patch('shutil.disk_usage')
def test_disk_check_fails(mock_du):
    class MockNamedTuple:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    mock_du.return_value = MockNamedTuple(total=1000**3, used=995**3, free=5**3) # 5GB free
    with pytest.raises(DiskSpaceError):
        check_free_space("/", 10)

def test_cleanup_orphan_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        old_part = dir_path / "old.part"
        new_part = dir_path / "new.part"
        
        old_part.touch()
        new_part.touch()
        
        old_time = datetime.now().timestamp() - (25 * 3600)
        os.utime(old_part, (old_time, old_time))
        
        cleanup_orphan_files(str(dir_path), max_age_hours=24)
        
        assert not old_part.exists()
        assert new_part.exists()
