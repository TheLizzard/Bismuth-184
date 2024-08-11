# https://learn.microsoft.com/en-us/windows/win32/winprog/windows-data-types
# https://stackoverflow.com/a/70817890/11106801
from __future__ import annotations
from ctypes.wintypes import HANDLE, DWORD, LPVOID, BOOL
from threading import Thread
import ctypes
import msvcrt
import psutil
import os

LPCSTR:type = LPVOID

def _errcheck_not_zero(value, func, args):
    if value in (0, None):
        raise ctypes.WinError()
    return args

def _errcheck_not_max(value, func, args):
    if value == 0xffffffff:
        raise ctypes.WinError()
    return args

class OVERLAPPED(ctypes.Structure):
    _fields_ = [
                 ("Internal", LPVOID),
                 ("InternalHigh", LPVOID),
                 ("Offset", DWORD),
                 ("OffsetHigh", DWORD),
                 ("Pointer", LPVOID),
                 ("hEvent", HANDLE),
               ]

# LockFile
LockFileEx = ctypes.windll.kernel32.LockFileEx
LockFileEx.argtypes = (HANDLE, DWORD, DWORD, DWORD, DWORD,
                       ctypes.POINTER(OVERLAPPED))
LockFileEx.restype = BOOL
LockFileEx.errcheck = _errcheck_not_zero
# UnlockFile
UnlockFileEx = ctypes.windll.kernel32.UnlockFileEx
UnlockFileEx.argtypes = (HANDLE, DWORD, DWORD, DWORD, ctypes.POINTER(OVERLAPPED))
UnlockFileEx.restype = BOOL
UnlockFileEx.errcheck = _errcheck_not_zero
# CreateEventA
CreateEventA = ctypes.windll.kernel32.CreateEventA
CreateEventA.argtypes = (LPVOID, BOOL, BOOL, LPCSTR)
CreateEventA.restype = HANDLE
CreateEventA.errcheck = _errcheck_not_zero
# OpenEventA
OpenEventA = ctypes.windll.kernel32.OpenEventA
OpenEventA.argtypes = (DWORD, BOOL, LPCSTR)
OpenEventA.restype = HANDLE
OpenEventA.errcheck = _errcheck_not_zero
# SetEvent
SetEvent = ctypes.windll.kernel32.SetEvent
SetEvent.argtypes = (HANDLE,)
SetEvent.restype = BOOL
SetEvent.errcheck = _errcheck_not_zero
# ResetEvent
ResetEvent = ctypes.windll.kernel32.ResetEvent
ResetEvent.argtypes = (HANDLE,)
ResetEvent.restype = BOOL
ResetEvent.errcheck = _errcheck_not_zero
# CloseHandle
CloseHandle = ctypes.windll.kernel32.CloseHandle
CloseHandle.argtypes = (HANDLE,)
CloseHandle.restype = BOOL
CloseHandle.errcheck = _errcheck_not_zero
# WaitForSingleObject
WaitForSingleObject = ctypes.windll.kernel32.WaitForSingleObject
WaitForSingleObject.argtypes = (HANDLE, DWORD)
WaitForSingleObject.restype = DWORD
WaitForSingleObject.errcheck = _errcheck_not_max

# Constants
LOCKFILE_EXCLUSIVE_LOCK:DWORD = DWORD(0x00000002)
EVENT_ALL_ACCESS:DWORD = DWORD(0x1f0003)
INFINITE:DWORD = DWORD(-1) # https://stackoverflow.com/q/17814571/11106801
WAIT_OBJECT_0:DWORD = DWORD(0x00000000)

# Helpers
def string_to_c(data:str) -> LPCSTR:
    return ctypes.create_string_buffer(data.encode())


# Functions
def lock_file(file:File) -> None:
    handle:DWORD = msvcrt.get_osfhandle(file.fileno())
    overlapped:OVERLAPPED = OVERLAPPED(0, 0, 0, 0, 0, 0)
    LockFileEx(handle, LOCKFILE_EXCLUSIVE_LOCK, 0, ~0, ~0,
               ctypes.pointer(overlapped))

def unlock_file(file:File) -> None:
    handle:DWORD = msvcrt.get_osfhandle(file.fileno())
    overlapped:OVERLAPPED = OVERLAPPED(0, 0, 0, 0, 0, 0)
    UnlockFileEx(handle, 0, ~0, ~0, ctypes.pointer(overlapped))


_signal_handlers:dict[int:Callable] = {}
_events:list[HANDLE] = []
SELF_PID:int = os.getpid()

SIGUSR1 = 1
SIGUSR2 = 2
SIG_DFL = object()


def signal_register(signal:int, handler:Callable) -> None:
    assert isinstance(signal, int), "TypeError"
    assert callable(handler) or (handler is SIG_DFL), "TypeError"

    # Loop to check if the signal has been activated
    def call_loop() -> None:
        while event in _events:
            res:DWORD = WaitForSingleObject(event, INFINITE)
            ResetEvent(event)
            handler:Callable = _signal_handlers[signal]
            if handler is not SIG_DFL:
                handler(signal, None)

    _is_new_signal:bool = (_signal_handlers.get(signal, None) is None)
    _signal_handlers[signal] = handler
    # Create event and start loop
    if _is_new_signal:
        event:HANDLE = CreateEventA(None, True, False,
                                    string_to_c(f"_signal_{SELF_PID}_{signal}"))
        _events.append(event)
        Thread(target=call_loop, daemon=True).start()


def signal_get(signal:int) -> Callable:
    if signal not in _signal_handlers:
        return SIG_DFL
    return _signal_handlers[signal]


def signal_send(pid:int, signal:int) -> None:
    assert signal != 0, "Use `pid_exists` function instead"
    try:
        event:HANDLE = OpenEventA(EVENT_ALL_ACCESS, False,
                                  string_to_c(f"_signal_{pid}_{signal}"))
    except OSError:
        # Signal not accepted by pid
        return None
    SetEvent(event)
    CloseHandle(event)


def pid_exists(pid:int) -> bool:
    pid:int = int(pid) # pid must be an int
    psutil.pid_exists(pid)