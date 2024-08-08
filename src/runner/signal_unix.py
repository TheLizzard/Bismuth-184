from __future__ import annotations
import signal as _signal
import fcntl
import os

lock_file = lambda file: fcntl.flock(file, fcntl.LOCK_EX)
unlock_file = lambda file: fcntl.flock(file, fcntl.LOCK_UN)
signal_send = os.kill
signal_register = _signal.signal
signal_cleanup = lambda: None
SIGUSR1 = _signal.SIGUSR1
SIGUSR2 = _signal.SIGUSR2

def pid_exists(pid:int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False