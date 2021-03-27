from threading import Thread
from time import sleep
import msvcrt
import os

# No idea what is going on here but if it works, it works.
from ctypes import windll, byref, wintypes, GetLastError, WinError, POINTER
from ctypes.wintypes import HANDLE, DWORD, BOOL

# ???
LPDWORD = POINTER(DWORD)
# https://docs.microsoft.com/en-gb/windows/win32/api/winbase/nf-winbase-createnamedpipea
PIPE_WAIT = wintypes.DWORD(0x00000000)
PIPE_NOWAIT = wintypes.DWORD(0x00000001)
ERROR_NO_DATA = 232


class AdvancedFD:
    """
    A wrapper for a file descriptor so that we can call:
        `<AdvancedFD>.read(number_of_bytes)` and
        `<AdvancedFD>.write(data_as_bytes)` and
        `<AdvancedFD>.fileno()` and
        `<AdvancedFD>.close()` and
        `<AdvancedFD>.config_non_blocking(non_blocking=True)`

    It also makes the `read_fd` non blocking. When reading from a non-blocking
    pipe with no data it returns b"".

    Methods:
        write(data: bytes) -> None
        read(number_of_bytes: int) -> bytes
        get_rawfd() -> int
        fileno() -> int
        close() -> None
    """
    def __init__(self, fd: int):
        self.fd = fd
        self.closed = False

    def fileno(self) -> int:
        """
        Returns the raw fd as an int.
        """
        return self.get_rawfd()

    def __del__(self) -> None:
        """
        When this object is garbage collected close the fd
        """
        self.close()

    def close(self) -> None:
        """
        Closes the file descriptor.
        Note: it cannot be reopened and might raise an error if it is
        being used. You don't have to call this function. It is automatically
        called when this object is being garbage collected.
        """
        self.closed = True

    def write(self, data: bytes) -> None:
        """
        Writes a string of bytes to the file descriptor.
        Note: Must be bytes.
        """
        os.write(self.fd, data)

    def read(self, x: int) -> bytes:
        """
        Reads `x` bytes from the file descriptor.
        Note: `x` must be an int
              Returns the bytes. Use `<bytes>.decode()` to convert it to a str
        """
        try:
            return os.read(self.fd, x)
        except:
            return b""

    def config_non_blocking(self, non_blocking=True) -> bool:
        """
        If the `non_blocking` argument is `true`, this makes the file
        descriptor non blocking. If it is `False` it makes the file
        descriptor blocking again.
        Returns `True` if sucessfull, otherwise returns `False`
        """

        if non_blocking:
            mode = PIPE_NOWAIT
        else:
            mode = PIPE_WAIT

        # Please note that this is kindly plagiarised from:
        # https://stackoverflow.com/a/34504971/11106801
        SetNamedPipeHandleState = windll.kernel32.SetNamedPipeHandleState
        SetNamedPipeHandleState.argtypes = [HANDLE, LPDWORD, LPDWORD, LPDWORD]
        SetNamedPipeHandleState.restype = BOOL

        handle = msvcrt.get_osfhandle(self.fd)

        res = SetNamedPipeHandleState(handle, byref(mode), None, None)
        return not (res == 0)

    def get_rawfd(self) -> int:
        """
        Returns the raw fd as an int.
        """
        return self.fd


class NonBlockingPipe:
    """
    Creates 2 file descriptors and wrapps them in the `AdvancedFD` class
    so that we can call:
        `<AdvancedFD>.read(number_of_bytes)` and
        `<AdvancedFD>.write(data_as_bytes)` and
        `<AdvancedFD>.fileno()` and
        `<AdvancedFD>.close()` and
        `<AdvancedFD>.config_non_blocking(non_blocking=True)`

    It also makes the `read_fd` non blocking. When reading from a non-blocking
    pipe with no data it returns b"".

    Methods:
        read(number_of_bytes: int) -> bytes
        write(data: bytes) -> None
        get_rawfds() -> (int, int)
        is_waiting() -> bool
        close() -> None
    """
    def __init__(self):
        self.read_fd, self.write_fd = self.create_pipes()

    '''
    def is_waiting(self) -> bool:
        """
        This checks if a process is trying to read from `read_fd`
        """
        self.config_non_blocking(True)
        self.write_fd.write(b"\r")
        char_in_fd = self.read_fd.read(1)
        self.config_non_blocking(False)
        print(char_in_fd)
        if char_in_fd == b"\r":
            result = False
        elif char_in_fd == b"":
            result = True
        else:
            raise ValueError("Accidentally read \"%s\" from a fd" % char_in_fd)
        return result
    '''
    def is_waiting(self, timeout) -> bool:
        """
        Checks if someone is reading from `read_fd`. It does that by:
            writing "\r" to the fd
            starting a thread that tries to read the "\r"
            if the thread is unsuccessful and is alive:
                the thread is still trying to read from `read_fd` but can't
                because someone handled the "\r" give 10 "\r"s to the thread
                to stop it and return `True`
            else:
                no one was there to handle the "\r" that is why the read read
                it so fast, we can return `False`
        """
        self.write_fd.write(b"\r")
        thread = Thread(target=self.try_read)
        thread.start()
        sleep(timeout/1000)
        if thread.is_alive():
            self.write_fd.write(b"\r"*10)
            return True
        return False

    def try_read(self):
        data = self.read_fd.read(1)

    def write(self, text):
        self.write_handle.write(text)

    def config_non_blocking(self, non_blocking=True) -> bool:
        """
        If the `non_blocking` argument is `true`, this makes the read file
        descriptor non blocking. If it is `False` it makes the read file
        descriptor blocking again.
        Returns `True` if sucessfull, otherwise returns `False`
        """
        return self.read_fd.config_non_blocking(non_blocking)

    def __del__(self) -> None:
        """
        When this object is garbage collected close the fds
        """
        self.close()

    def close(self) -> None:
        """
        Note: it cannot be reopened and might raise an error if it is
        being used. You don't have to call this function. It is automatically
        called when this object is being garbage collected.
        """
        self.read_fd.close()
        self.write_fd.close()

    def create_pipes(self) -> (AdvancedFD, AdvancedFD):
        """
        Creates 2 file descriptors and wrapps them in the `Pipe` class so
        that we can call:
            `<Pipe>.read(number_of_bytes)` and
            `<Pipe>.write(data_as_bytes)`
        """
        read_fd, write_fd = os.pipe()
        return AdvancedFD(read_fd), AdvancedFD(write_fd)

    def write(self, data: bytes) -> None:
        """
        Writes a string of bytes to the file descriptor.
        Note: Must be bytes.
        """
        self.write_fd.write(data)

    def read(self, number_of_bytes: int) -> bytes:
        """
        Reads `x` bytes from the file descriptor.
        Note: `x` must be an int
              Returns the bytes. Use `<bytes>.decode()` to convert it to a str
        """
        return self.read_fd.read(number_of_bytes)

    def get_rawfds(self) -> (int, int):
        """
        Returns the raw file descriptors as ints in the form:
            (read_fd, write_fd)
        """
        return self.read_fd.get_rawfd(), self.write_fd.get_rawfd()

    def get_readfd(self) -> AdvancedFD:
        """
        Returns an `AdvancedFD` object that represents the read fd
        """
        return self.read_fd

    def get_writefd(self) -> AdvancedFD:
        """
        Returns an `AdvancedFD` object that represents the write fd
        """
        return self.write_fd


if __name__  == "__main__":
    import subprocess
    from time import sleep

    # Create the nonblocking pipe
    pipe = NonBlockingPipe()

    subprocess.Popen("cmd", stdin=pipe.get_readfd(), shell=True)
    sleep(0.5)

    print(pipe.is_waiting())

    # pipe.config_non_blocking(True)

    pipe.write(b"xxx")
    print(pipe.read(1024)) # Check if it can still read properly

    pipe.write(b"yyy")
    print(pipe.read(1024)) # Read all of the data in the pipe
    # print(pipe.read(1024)) # Check if it is non blocking
