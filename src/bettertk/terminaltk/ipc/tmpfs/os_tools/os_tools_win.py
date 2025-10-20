# https://learn.microsoft.com/en-us/windows/win32/winprog/windows-data-types
# https://stackoverflow.com/a/70817890/11106801
from __future__ import annotations
from ctypes.wintypes import HANDLE, DWORD, LPVOID, BOOL
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
               ctypes.byref(overlapped))

def unlock_file(file:File) -> None:
    handle:DWORD = msvcrt.get_osfhandle(file.fileno())
    overlapped:OVERLAPPED = OVERLAPPED(0, 0, 0, 0, 0, 0)
    UnlockFileEx(handle, 0, ~0, ~0, ctypes.byref(overlapped))


class NamedSemaphore:
    __Slots__ = "_cevent", "_closed"

    def __init__(self, name:str, *, create:bool=False) -> NamedSemaphore:
        cname:LPCSTR = string_to_c(name)
        self._closed:bool = False
        if create:
            self._cevent:HANDLE = CreateEventA(None, True, False, cname)
        else:
            self._cevent:HANDLE = OpenEventA(EVENT_ALL_ACCESS, False, cname)

    def set(self) -> NamedSemaphore:
        SetEvent(self._cevent)
        return self

    def wait_clear(self) -> NamedSemaphore:
        res:DWORD = WaitForSingleObject(self._cevent, INFINITE)
        ResetEvent(self._cevent)
        return self

    def close(self) -> NamedSemaphore:
        CloseHandle(self._cevent)
        self._closed:bool = True
        return self

    def unlink(self) -> NamedSemaphore:
        if not self._closed:
            self.close()
        return self

    @property
    def closed(self) -> bool:
        return self._closed


def pid_exists(pid:int) -> bool:
    pid:int = int(pid) # pid must be an int
    return psutil.pid_exists(pid)
