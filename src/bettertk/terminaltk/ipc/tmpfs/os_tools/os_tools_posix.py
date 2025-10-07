from __future__ import annotations
from ctypes.util import find_library
import signal as _signal
import ctypes
import fcntl
import os

lock_file = lambda file: fcntl.flock(file, fcntl.LOCK_EX)
unlock_file = lambda file: fcntl.flock(file, fcntl.LOCK_UN)
SELF_PID:int = os.getpid()

def pid_exists(pid:int) -> bool:
    pid:int = int(pid) # pid must be an int
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _errcheck_not_zero(value, func, args):
    if value in (0, None):
        args_str = ", ".join(map(str, args))
        raise OSError(f"{func.__name__}({args_str}) => {value}")
    return args

def _errcheck_zero(value, func, args):
    if value != 0:
        args_str = ", ".join(map(str, args))
        raise OSError(f"{func.__name__}({args_str}) => {value}")
    return args

def string_to_c(data:str) -> CHAR_PTR:
    return ctypes.create_string_buffer(data.encode())


libc_name:str = find_library("c") or find_library("libc") or \
                find_library("C") or find_library("libC")

libc = ctypes.cdll.LoadLibrary(libc_name)

O_CREAT:int = os.O_CREAT
O_EXCL:int = os.O_EXCL
SEM_FAILED:int = 0


mode_t:type = ctypes.c_uint32
CSemaphore:type = ctypes.c_void_p


_sem_open = libc.sem_open
_sem_open.argtypes = (ctypes.c_char_p, ctypes.c_int, mode_t, ctypes.c_uint)
_sem_open.restype = CSemaphore
_sem_open.errcheck = _errcheck_not_zero # SEM_FAILED is probably 0

_sem_close = libc.sem_close
_sem_close.argtypes = (CSemaphore,)
_sem_close.restype = ctypes.c_int
_sem_close.errcheck = _errcheck_zero

_sem_unlink = libc.sem_unlink
_sem_unlink.argtypes = (ctypes.c_char_p,)
_sem_unlink.restype = ctypes.c_int
_sem_unlink.errcheck = _errcheck_zero

_sem_post = libc.sem_post
_sem_post.argtypes = (CSemaphore,)
_sem_post.restype = ctypes.c_int
_sem_post.errcheck = _errcheck_zero

_sem_post = libc.sem_post
_sem_post.argtypes = (CSemaphore,)
_sem_post.restype = ctypes.c_int
_sem_post.errcheck = _errcheck_zero

_sem_wait = libc.sem_wait
_sem_wait.argtypes = (CSemaphore,)
_sem_wait.restype = ctypes.c_int
_sem_wait.errcheck = _errcheck_zero

_sem_getvalue = libc.sem_getvalue
_sem_getvalue.argtypes = (CSemaphore, ctypes.POINTER(ctypes.c_int))
_sem_getvalue.restype = ctypes.c_int
_sem_getvalue.errcheck = _errcheck_zero


class NamedSemaphore:
    __slots__ = "_csem", "_name", "_closed"

    def __init__(self, name:str, *, create:bool=False) -> NamedSemaphore:
        flags:int = O_CREAT|O_EXCL if create else 0
        self._csem = _sem_open(string_to_c(name), flags, 0o644, 0)
        if self._csem in (-1, 0, None): # Whatever the value of SEM_FAILED is
            raise OSError("sem_open failed")
        self._closed:bool = False
        self._name:str = name

    def set(self) -> NamedSemaphore:
        _sem_post(self._csem)
        return self

    def wait_clear(self) -> NamedSemaphore:
        _sem_wait(self._csem)
        return self

    def close(self) -> NamedSemaphore:
        self._closed:bool = True
        _sem_close(self._csem)
        return self

    def unlink(self) -> NamedSemaphore:
        if not self._closed:
            self.close()
        _sem_unlink(string_to_c(self._name))
        return self

    @property
    def closed(self) -> bool:
        return self._closed