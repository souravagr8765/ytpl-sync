"""
Concurrency lock management for preventing overlapping script runs.
"""
import os
import signal
import atexit
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LockAcquireError(Exception):
    pass

class LockFile:
    def __init__(self, lock_path: str):
        self.path = Path(lock_path).expanduser()

    def acquire(self) -> None:
        if self.path.exists():
            try:
                content = self.path.read_text().strip()
                pid = int(content)

                is_alive = False
                try:
                    os.kill(pid, 0)
                    is_alive = True
                except PermissionError:
                    is_alive = True
                except (ProcessLookupError, OSError):
                    is_alive = False

                if is_alive:
                    raise LockAcquireError(f"Another instance is already running (PID {pid}). Exiting.")
                else:
                    logger.warning(f"Stale lock file found (PID {pid} not running). Removing.")
                    self.path.unlink(missing_ok=True)
            except LockAcquireError:
                raise
            except Exception:
                logger.warning("Stale lock file found (unreadable or invalid). Removing.")
                try:
                    self.path.unlink(missing_ok=True)
                except Exception:
                    pass

        self.path.write_text(str(os.getpid()))

        atexit.register(self.release)

        def sig_handler(sig, frame):
            self.release()
            signal.signal(sig, signal.SIG_DFL)
            if hasattr(signal, "raise_signal"):
                signal.raise_signal(sig)
            else:
                os.kill(os.getpid(), sig)

        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, sig_handler)

    def release(self) -> None:
        try:
            if self.path.exists():
                self.path.unlink()
            logger.debug(f"Lock file {self.path} released.")
        except Exception as e:
            logger.debug(f"Failed to release lock file {self.path}: {e}")
