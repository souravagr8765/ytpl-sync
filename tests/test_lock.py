import pytest
import tempfile
from pathlib import Path
import os
from ytpl_sync.lock import LockFile, LockAcquireError

def test_acquire_and_release():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    Path(path).unlink()
    
    lock = LockFile(path)
    lock.acquire()
    assert Path(path).exists()
    assert str(os.getpid()) == Path(path).read_text().strip()
    lock.release()
    assert not Path(path).exists()

def test_stale_lock():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"99999999")
        path = f.name
    
    lock = LockFile(path)
    lock.acquire() # Should succeed and overwrite
    assert Path(path).read_text().strip() == str(os.getpid())
    lock.release()

def test_concurrent_lock():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(str(os.getpid()).encode())
        path = f.name
    
    lock = LockFile(path)
    with pytest.raises(LockAcquireError):
        lock.acquire()
    Path(path).unlink(missing_ok=True)
