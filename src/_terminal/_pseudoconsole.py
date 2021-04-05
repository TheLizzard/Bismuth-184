# Mostly taken from: https://github.com/iljau/PyEchoCon/blob/master/PyEchoCon.py

from _winapi import GENERIC_READ, OPEN_EXISTING, GENERIC_WRITE
from ctypes import Structure, byref, sizeof, POINTER, windll
from ctypes import c_char_p, c_size_t, wintypes, HRESULT, create_string_buffer
from ctypes import c_int64, c_void_p

from ctypes.wintypes import *
from ctypes import windll

import os
import msvcrt


# Set up all of the constants:
STILL_ACTIVE = 259

INFINITE = DWORD(-1)

EXTENDED_STARTUPINFO_PRESENT = 0x00080000
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016


# Set up all of the types
null_ptr = POINTER(c_void_p)()

PVOID = LPVOID
LPTSTR = c_void_p
SIZE_T = c_size_t

HPCON = HANDLE


# COORD used for the size of the pseudo console
class COORD(Structure):
    _fields_ = [("X", SHORT),
                ("Y", SHORT)]

class STARTUPINFO(Structure):
    _fields_ = [("cb", DWORD),
                ("lpReserved", LPTSTR),
                ("lpDesktop", LPTSTR),
                ("lpTitle", LPTSTR),
                ("dwX", DWORD),
                ("dwY", DWORD),
                ("dwXSize", DWORD),
                ("dwYSize", DWORD),
                ("dwXCountChars", DWORD),
                ("dwYCountChars", DWORD),
                ("dwFillAttribute", DWORD),
                ("dwFlags", DWORD),
                ("wShowWindow", WORD),
                ("cbReserved2", WORD),
                ("lpReserved2", LPBYTE),
                ("hStdInput", HANDLE),
                ("hStdOutput", HANDLE),
                ("hStdError", HANDLE)]

class STARTUPINFOEX(Structure):
    _fields_ = [("StartupInfo", STARTUPINFO),
                ("lpAttributeList", POINTER(PVOID))]

class PROCESS_INFORMATION(Structure):
    _fields_ = [("hProcess", HANDLE),
                ("hThread", HANDLE),
                ("dwProcessId", DWORD),
                ("dwThreadId", DWORD)]


def _errcheck_bool(value, func, args):
    """
    Checks if the value is 0 otherwise it throws an error
    """
    if not value:
        raise ctypes.WinError()
    return args


# Set up all of the functions that we are going to call
GetLastError = windll.kernel32.GetLastError
GetLastError.argtypes = tuple()
GetLastError.restype = DWORD


SetLastError = windll.kernel32.SetLastError
SetLastError.argtypes = (DWORD, )


GetExitCodeProcess = windll.kernel32.GetExitCodeProcess
GetExitCodeProcess.argtype = (HANDLE, LPDWORD)
GetExitCodeProcess.restype = BOOL
GetExitCodeProcess.errcheck = _errcheck_bool


InitializeProcThreadAttributeList = windll.kernel32.InitializeProcThreadAttributeList
InitializeProcThreadAttributeList.argtype = (POINTER(HANDLE), POINTER(HANDLE),
                                             PVOID, DWORD)
InitializeProcThreadAttributeList.restype = BOOL
InitializeProcThreadAttributeList.errcheck = _errcheck_bool


UpdateProcThreadAttribute = windll.kernel32.UpdateProcThreadAttribute
UpdateProcThreadAttribute.argtype = (POINTER(PVOID), DWORD, POINTER(DWORD),
                                     PVOID, SIZE_T, PVOID, POINTER(SIZE_T))
UpdateProcThreadAttribute.restype = BOOL
UpdateProcThreadAttribute.errcheck = _errcheck_bool


DeleteProcThreadAttributeList = windll.kernel32.DeleteProcThreadAttributeList
DeleteProcThreadAttributeList.argtypes = (POINTER(PVOID), )


CreateFileW = windll.kernel32.CreateFileW # <-- Unicode version!
CreateFileW.restype = HANDLE
CreateFileW.argtypes = (LPCWSTR, DWORD, DWORD, POINTER(c_void_p),
                       DWORD, DWORD, HANDLE)


CreateProcessW = windll.kernel32.CreateProcessW # <-- Unicode version!
CreateProcessW.restype = BOOL
CreateProcessW.errcheck = _errcheck_bool


HeapAlloc = windll.kernel32.HeapAlloc
HeapAlloc.restype = LPVOID
HeapAlloc.argtypes = (HANDLE, DWORD, SIZE_T)


HeapFree = windll.kernel32.HeapFree
HeapFree.restype = BOOL
HeapFree.argtypes = (HANDLE, DWORD, LPVOID)
HeapFree.errcheck = _errcheck_bool


GetProcessHeap = windll.kernel32.GetProcessHeap
GetProcessHeap.restype = HANDLE
GetProcessHeap.argtypes = tuple()


CreatePseudoConsole = windll.kernel32.CreatePseudoConsole
CreatePseudoConsole.argtypes = (COORD, HANDLE, HANDLE, DWORD, POINTER(HPCON))
CreatePseudoConsole.restype = HRESULT


ReadFile = windll.kernel32.ReadFile
ReadFile.restype = BOOL
ReadFile.errcheck = _errcheck_bool
ReadFile.argtypes = (HANDLE, LPVOID, DWORD, LPDWORD, POINTER(c_void_p))


ClosePseudoConsole = windll.kernel32.ClosePseudoConsole
ClosePseudoConsole.argtypes = (HPCON, )


CancelIoEx = ctypes.windll.kernel32.CancelIoEx
CancelIoEx.restype = BOOL
CancelIoEx.errcheck = _errcheck_bool
CancelIoEx.argtypes = (HANDLE, POINTER(c_void_p))


CloseHandle = ctypes.windll.kernel32.CloseHandle
CloseHandle.argtypes = (HANDLE, )
CloseHandle.restype = BOOL
CloseHandle.errcheck = _errcheck_bool


WaitForSingleObject = windll.kernel32.WaitForSingleObject
WaitForSingleObject.restype = DWORD
WaitForSingleObject.argtypes = (ctypes.wintypes.HANDLE, DWORD)


ResizePseudoConsole = windll.kernel32.ResizePseudoConsole
ResizePseudoConsole.argtypes = (HPCON, COORD)
ResizePseudoConsole.restype = HRESULT


# Set up all of the function that we are going to use
def InitializeStartupInfoAttachedToPseudoConsole(startup_info, console):
    dwAttributeCount = 1
    dwFlags = 0
    lpSize = PVOID()

    # Call with null lpAttributeList first to get back the lpSize
    try:
        InitializeProcThreadAttributeList(None, dwAttributeCount,
                                          dwFlags, byref(lpSize))
    except WindowsError as error:
        if error.winerror == 122:
            # OSError: [WinError 122] The data area passed to a
            # system call is too small.
            SetLastError(0)
        else:
            raise error

    mem = HeapAlloc(GetProcessHeap(), 0, lpSize.value)
    startup_info.lpAttributeList = ctypes.cast(mem, ctypes.POINTER(c_void_p))

    InitializeProcThreadAttributeList(startup_info.lpAttributeList,
                                      dwAttributeCount, dwFlags, byref(lpSize))


    UpdateProcThreadAttribute(startup_info.lpAttributeList, DWORD(0),
                              DWORD(PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE),
                              console, sizeof(console), None, None)

    return mem


def CreatePseudoConsoleAndPipes(width:int, height:int, flags:int=0) -> HANDLE:
    """
    Creates a pseudo console (acts a bit like a pty pipe).
    Arguments:
        width:int        The width of the console
        height:int       The height of the console
        flags:int        Default=0  PSEUDOCONSOLE_INHERIT_CURSOR=1
    Note:
        The width and the height are used internally in `CreatePseudoConsole`
        when characters like "\b" or <move cursor> are written to the pipe.
        Make sure to keep up to date. Note that when `flags=1` it might
        hang on `CreatePseudoConsole`
    Returns:
        console:HANDLE   The console object. Its attributes:
                             read_fd        What should be used to read
                                            the slaves stdout
                             write_fd       What should be used to write
                                            to the slaves stdin
                             read_handler   The windows handler of read_fd
                             write_handler  The windows handler of write_fd
    """
    # Create the parent pipes
    read_pty_fd, write_fd = os.pipe()
    read_pty_handler = msvcrt.get_osfhandle(read_pty_fd)

    # Create the child pipes
    read_fd, write_pty_fd = os.pipe()
    write_pty_handler = msvcrt.get_osfhandle(write_pty_fd)

    # Create the console
    size = COORD(width, height)
    console = HPCON()

    result = CreatePseudoConsole(size, read_pty_handler, write_pty_handler,
                                 DWORD(flags), byref(console))
    # Check if any errors occured
    if result != 0:
        raise ctypes.WinError(result)

    os.close(write_pty_fd)
    os.close(read_pty_fd)

    # Add references for the fds to the console
    console.read_fd = read_fd
    console.write_fd = write_fd
    console.read_handler = msvcrt.get_osfhandle(read_fd)
    console.write_handler = msvcrt.get_osfhandle(write_fd)

    # Return the console object
    return console
