from __future__ import annotations
import signal as _signal
import fcntl
import os

lock_file = lambda file: fcntl.flock(file, fcntl.LOCK_EX)
unlock_file = lambda file: fcntl.flock(file, fcntl.LOCK_UN)
signal_send = os.kill
signal_register = _signal.signal
signal_get = _signal.getsignal
SIGUSR1 = _signal.SIGUSR1
SIGUSR2 = _signal.SIGUSR2
SELF_PID:int = os.getpid()

def pid_exists(pid:int) -> bool:
    pid:int = int(pid) # pid must be an int
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


# Make sure we don't get any signals (that will close us) while we are
#   initialising. Remove after implementing signal emulation on posix
for SIG in (SIGUSR1, SIGUSR2):
    signal_register(SIG, _signal.SIG_IGN)