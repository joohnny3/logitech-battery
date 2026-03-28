"""Single instance enforcement using OS-level file locking."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_LOCK_NAME = "mouse-battery-monitor.lock"
_lock_file = None


def acquire() -> bool:
    """Try to acquire single-instance lock. Returns True if successful.

    The lock is held for the lifetime of the process.
    On crash or normal exit the OS releases the lock automatically.
    """
    global _lock_file
    lock_path = Path(tempfile.gettempdir()) / _LOCK_NAME
    try:
        _lock_file = open(lock_path, "w")  # noqa: SIM115
        if sys.platform == "win32":
            import msvcrt
            _lock_file.write(str(os.getpid()))
            _lock_file.flush()
            _lock_file.seek(0)
            msvcrt.locking(_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _lock_file.write(str(os.getpid()))
            _lock_file.flush()
        return True
    except (OSError, IOError):
        if _lock_file:
            _lock_file.close()
            _lock_file = None
        return False


def release() -> None:
    """Release the single-instance lock explicitly."""
    global _lock_file
    if _lock_file is None:
        return
    try:
        if sys.platform == "win32":
            import msvcrt
            _lock_file.seek(0)
            msvcrt.locking(_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lock_file, fcntl.LOCK_UN)
        _lock_file.close()
    except OSError:
        pass
    _lock_file = None
