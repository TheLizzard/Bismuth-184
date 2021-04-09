from threading import Thread, Lock
from time import sleep
from . import _pseudoconsole
import os


class Buffer:
    """
    This is a bytes buffer.
    Methods:
        read(number_of_bytes:int, blocking:bool=True) -> bytes
        append(data:bytes) -> None 
        readall() -> bytes
        __len__() -> int
        reset() -> None
    """
    def __init__(self):
        self.data = b""
        self.lock = Lock()

    def __len__(self):
        """
        Returns the length of the data in the buffer
        """
        return len(self.data)

    def append(self, data:bytes):
        """
        Appends data to the buffer
        """
        with self.lock:
            self.data += data

    def reset(self):
        """
        Clears all of the contents of the buffer
        """
        with self.lock:
            self.data = b""
    clear = reset

    def readall(self):
        """
        Reads all of the data out of the buffer
        """
        with self.lock:
            data = self.data
            self.data = b""
        return data

    def read(self, number_of_bytes:int, blocking:bool=True):
        """
        Reads `number_of_bytes` number of bytes.
        Note that if `blocking` is `True` then it will wait until the length
        of the data in the buffer is at least equal to `number_of_bytes`.
        """
        # If blocking sleep until there is enough data in the buffer
        if blocking:
            while len(self.data) < number_of_bytes:
                sleep(0.2)
        # Return the first `number_of_bytes` from the buffer
        with self.lock:
            data = self.data[:number_of_bytes]
            self.data = self.data[number_of_bytes:]
            return data


class Console:
    """
    A console that can run cmd commands.

    Methods:
        run(command:str) -> None
        poll() -> int
        close_proc() -> None
        close_console() -> None
        read(number_of_bytes:int, blocking:bool=False) -> bytes
        write(data:bytes) -> None
        resize(width:int=None, height:int=None) -> None

    Attributes:
        proc_alive:bool=False            # Is the process alive
        width:int                        # The width of the console
        height:int                       # The height of the console
        last_error:int=None              # The last windows api error code
        stdout_callback:function=None    # The function to be called when
                                         #   something is read from proc's
                                         #   stdout
        raise_callback_errors:bool=True  # Tells us if we should raise an error
                                         #   if something goes wrong in the
                                         #   callback

    Example (remove the `\` to add syntax highlighting):
        \"""
        # Create a console:
        console = Console(80, 24)
        # Run a command
        console.run("python simple_input_req.py")
        # Write stuff to stdin
        console.write(b"Hello\r")
        # Wait until the program exits:
        while console.poll() is None:
            sleep(0.2)
        # Wait for the thread to read all of the console's output
        sleep(0.1)
        # Print all of the console's output
        print(console.read(10000).decode())
        print("Exit code =", console.poll())
        # If you want to resize the console
        console.resize(width=50)
        # Close the process
        console.close_proc()
        # Close the console
        console.close_console()
    """
    def __init__(self, width:int, height:int, flags:int=0):
        """
        Creates a `Console` object.

        Notes:
            when `flags=1`, the program might hang on
            `<Console>.close_console()` for more info read this:
            https://github.com/microsoft/terminal/issues/1810
            Right now if `flags` isn't 0 it will raise an error
        """
        if flags != 0:
            raise ValueError("`flags` can't be anything except for 0. For "+\
                             "more info use `help(Console.__init__)`")
        self.output_buffer = Buffer()
        self.console = _pseudoconsole.CreatePseudoConsoleAndPipes(width, height,
                                                                  flags)
        self.console_alive = True
        self.read_output = False
        self.proc_alive = False
        self.lock = Lock()
        self.width = width
        self.height = height

        self.last_exit_code = None
        self.last_error = None
        self.stdout_callback = None
        self.raise_callback_errors = True

    def discard_output(self) -> None:
        """
        Discards all of the contents of `self.output_buffer`

        Note:
            If there is no process running this function will return:
                `"No process running"`
        """
        if not self.proc_alive:
            return "No process running"

        with self.lock:
            self.output_buffer.clear()

    def __del__(self) -> None:
        self.close_console()

    def run(self, command:str) -> None:
        """
        Runns the command given in the console.

        Arguments:
            command:str     The cmd command to be executed

        To stop the process use `<Console>.close_proc()`
        """
        if not self.console_alive:
            raise ValueError("This console is no longer alive!")

        self.last_exit_code = None

        # Start reading the proc output and save it into `self.output_buffer`
        if not self.read_output:
            Thread(target=self.pipe_listener, daemon=True).start()

        # Start the new process
        self.startup_info = _pseudoconsole.STARTUPINFOEX()
        self.startup_info.StartupInfo.cb = _pseudoconsole.sizeof(
                                                   _pseudoconsole.STARTUPINFOEX)

        self.mem = _pseudoconsole.InitializeStartupInfoAttachedToPseudoConsole(
                                                self.startup_info, self.console)

        self.proc_information = _pseudoconsole.PROCESS_INFORMATION()

        _pseudoconsole.CreateProcessW(None, command, None, None, False,
                       _pseudoconsole.EXTENDED_STARTUPINFO_PRESENT, None, None,
                       _pseudoconsole.byref(self.startup_info.StartupInfo),
                       _pseudoconsole.byref(self.proc_information))
        self.proc_handle = self.proc_information.hProcess

        self.proc_alive = True

    def wait_for_single_object(self, timeout_ms:int=None) -> None:
        """
        Calls `WaitForSingleObject` (no idea what it does) with a timeout.
        If `timeout_ms` is `None` then it will be converted to
        `_pseudoconsole.INFINITE`

        Notes:
            UNTESTED MIGHT CRASH YOUR LIFE
            If there is no process running this function will return:
                `"No process running"`
        """
        if not self.proc_alive:
            return "No process running"

        if timeout_ms is None:
            timeout_ms = _pseudoconsole.INFINITE
        _pseudoconsole.WaitForSingleObject(self.proc_information.hThread,
                                           timeout_ms)

    def poll(self) -> int:
        """
        Gets the exit code of the process.

        Returns:
            int     if the process has ended and the int is the exit code
            None    if the process hasn't ended yet

        Notes:
            This (mostly likely) can handle the process sending 259 as its
            error code even though that means `STILL_ACTIVE` in Windows API
            terms.
            If there is no process running this function will return:
                `"No process running"`
        """
        if not self.proc_alive:
            return "No process running"

        if self.last_exit_code is None:
            result = _pseudoconsole.DWORD()
            _pseudoconsole.GetExitCodeProcess(self.proc_handle,
                                              _pseudoconsole.byref(result))
            result_value = result.value
            if result_value == _pseudoconsole.STILL_ACTIVE:
                # Suggested here: https://stackoverflow.com/a/1591379/11106801
                # by @Netherwire. I have no idea how/why it works
                alive = _pseudoconsole.WaitForSingleObject(self.proc_handle, 0)
                if alive != 0:
                    return None
            self.last_exit_code = result_value
        return self.last_exit_code

    def close_proc(self) -> None:
        """
        Closes the process. Currently there are no checks to see if it
        is successful. This can be called multiple times even if the
        process is already closed
        """
        # If we are already dead skip
        if not self.proc_alive:
            return None
        self.proc_alive = False

        # Close the process
        _pseudoconsole.CloseHandle(self.proc_information.hThread)
        _pseudoconsole.CloseHandle(self.proc_information.hProcess)

        # Delete the process' memory
        _pseudoconsole.DeleteProcThreadAttributeList(
                                              self.startup_info.lpAttributeList)
        _pseudoconsole.HeapFree(_pseudoconsole.GetProcessHeap(), 0, self.mem)

    def close_console(self) -> None:
        """
        Closes the console. Currently there are no checks to see if it
        is successful. This can be called multiple times even if the
        console is already closed.
        """
        # Make sure that ther is no process still here
        self.close_proc()
        if not self.console_alive:
            return None
        self.console_alive = False
        self.read_output = False

        # Close the PseudoConsole
        _pseudoconsole.ClosePseudoConsole(self.console)

        # Close the fds
        os.close(self.console.read_fd)
        os.close(self.console.write_fd)
        # Tell the program that we are about to close its stdout
        #_pseudoconsole.CancelIoEx(self.console.read_fd,
        #                          _pseudoconsole.null_ptr)
        # Close the handles
        #_pseudoconsole.CloseHandle(self.console.write_handler)
        #_pseudoconsole.CloseHandle(self.console.read_handler)

    def pipe_listener(self, buffer_size:int=1) -> None:
        """
        DO NOT CALL
        Reads `self.console.read_fd` and writes everything
        to `self.output_buffer`.

        Arguments:
            buffer_size:int=1   # How many bytes to read at a time. Note that
                                # if it's > 1 it might have problems
                                # (no idea why)

        Raises:
            WindowsError        # An error occured
        """
        self.read_output = True
        while self.read_output:
            try:
                data = os.read(self.console.read_fd, 1)
                with self.lock:
                    self.output_buffer.append(data)
                    if self.stdout_callback is not None:
                        try:
                            self.stdout_callback(data)
                        except Exception as error:
                            if self.raise_callback_errors:
                                raise error
            except OSError as error:
                error_code = _pseudoconsole.GetLastError()
                self.read_output = False

                # Error 109: The pipe has been ended.
                # Error 995: The I/O operation has been aborted
                if error_code not in (995, 109):
                    self.last_error = error_code
                    raise WindowsError(error_code)

    def read(self, number_of_bytes:int, blocking:bool=False) -> bytes:
        """
        Reads data out of `self.output_buffer` which is data that has been
        taken from `self.console.read_fd`. If `blocking` is `True` it will
        wait until there are at least `number_of_bytes` number of bytes in
        the buffer before returning the first `number_of_bytes`.

        Arguments:
            number_of_bytes:int   # Number of bytes to read
            blocking:bool=False   # If the read should be blocking

        Returns:
            bytes                 # The data from the buffer
        """
        with self.lock:
            return self.output_buffer.read(number_of_bytes, blocking=blocking)

    def write(self, data:bytes) -> None:
        """
        Writes the data given to the process' stdin

        Arguments:
            data:bytes     # The data to write to the process' stdin
        """
        with self.lock:
            os.write(self.console.write_fd, data)

    def resize(self, width:int=None, height:int=None) -> None:
        """
        Resizes the console to the width/height specified.
        If `width` is `None` the last value of `width` is used. Same
        goes for `height`.

        Arguments:
            width:int=None    # The new width
            height:int=None   # The new height

        Raises:
            WindowsError      # An error occured
        """
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height

        size = _pseudoconsole.COORD(self.width, self.height)
        result = _pseudoconsole.ResizePseudoConsole(self.console, size)
        if result != 0:
            error_code = _pseudoconsole.GetLastError()
            self.last_error = error_code
            raise WindowsError(error_code)


if __name__ == "__main__":
    console = Console(80, 24)
    console.run("python -m tkinter")
    console.write(b"Hello\r")
    while console.poll() is None:
        sleep(0.2)
    sleep(1)
    print(console.read(10000).decode())
    print("Exit code =", console.poll())
    console.close_proc()
    console.close_console()
    console.close_console()

#pseudoconsole.py
