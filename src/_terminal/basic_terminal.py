from time import sleep
import subprocess

from .nonblocking_pipe import NonBlockingPipe, AdvancedFD
from constants.settings import settings

WIDTH = settings.terminal.width.get()


class StdFileDestriptors:
    """
    Just a holder for all of the `NonBlockingPipe` objects that
    represent stdin/stdout/stderr
    """
    def __init__(self):
        self._in = NonBlockingPipe()
        self.out = NonBlockingPipe()
        self.err = NonBlockingPipe()


class FinishedProcess:
    """
    A class that is instanciated only because `BasicTerminal` must
    always have a `self.proc` object
    """
    def __init__(self):
        self.returncode = 0
        self.pid = None

    def poll(self) -> str:
        return "Process terminated"

    def terminate(self) -> None:
        return None

    def kill(self) -> None:
        return None
FINISHED_PROC = FinishedProcess()


class BasicTerminal:
    def __init__(self, kill_proc, callback=None):
        self.kill_proc = kill_proc
        self.proc = FINISHED_PROC
        self.callback = callback

        self.std = StdFileDestriptors()
        self.std._in.config_non_blocking(False)
        self.std.out.config_non_blocking()
        self.std.err.config_non_blocking()

    def __del__(self) -> None:
        self.stop_process()

    @property
    def pid(self):
        return self.proc.pid

    def get_std_child(self) -> {"stdin": AdvancedFD, "stdout": AdvancedFD,
                                 "stderr": AdvancedFD}:
        """
        Returns a dictionary of the stdin/stdout/stderr for the child process
        """
        return {"stdin": self.std._in.get_readfd(),
                "stdout": self.std.out.get_writefd(),
                "stderr": self.std.err.get_writefd()}

    def get_std_parent(self) -> {"stdin": AdvancedFD, "stdout": AdvancedFD,
                                 "stderr": AdvancedFD}:
        """
        Returns a dictionary of the stdin/stdout/stderr for the parent process
        """
        return {"stdin": self.std._in.get_writefd(),
                "stdout": self.std.out.get_readfd(),
                "stderr": self.std.err.get_readfd()}

    def run(self, command: str, creationflags: int=0) -> int:
        """
        Runs the given command as if in cmd. It waits for the process
        to finish and returns the exit code
        """
        # Stop the previous process if it's still running
        self.stop_process()
        self.proc = subprocess.Popen(command, close_fds=False, shell=True,
                                     creationflags=creationflags,
                                     **self.get_std_child())
        # Wait for the proccess to end
        while self.proc.poll() is None:
            if self.callback is not None:
                self.callback()
            sleep(0.02)
        # Get the return code
        exit_code = self.proc.returncode
        # Make sure we clean up
        self.proc = FINISHED_PROC
        return exit_code

    def run_no_wait(self, command: str, creationflags: int=0) -> None:
        """
        Runs the given command as if in cmd. Doesn't wait for the process
        to finish.
        """
        # Stop the previous process if it's still running
        self.stop_process()
        self.proc = subprocess.Popen(command, close_fds=False, shell=True,
                                     creationflags=creationflags,
                                     **self.get_std_child())

    def stop_process(self):
        """
        Kills the previous process if it's still running.
        """
        if not ((self.proc is None) or (self.proc is FINISHED_PROC)):
            command = self.kill_proc.format(pid=self.proc.pid)
            subprocess.Popen(command, shell=True)
            self.proc = FINISHED_PROC

    def stdin_write(self, text, end="\n"):
        """
        Writes the text to stdin.
        """
        self.std._in.write((text + end).encode())

    def stdout_write(self, text, add_padding=False, end="\n"):
        """
        Writes the text to stdout.
        """
        if add_padding:
            text = self.add_padding(text)
        self.std.out.write((text + end).encode())

    def stderr_write(self, text, add_padding=False, end="\n"):
        """
        Writes the text to stderr.
        """
        if add_padding:
            text = self.add_padding(text)
        self.std.err.write((text + end).encode())

    def forever_cmd(self):
        """
        Runs CMD in a `while True` loop.
        Use `<BasicTerminal>.forver_cmd_running` to stop the loop
        """
        self.forver_cmd_running = True
        while self.forver_cmd_running:
            msg = "Running cmd.exe"
            self.stdout_write(msg, add_padding=True)
            error = self.run("cmd.exe")
            msg = "Process exit code: %s" % str(error)
            self.stdout_write(msg, add_padding=True)

    def poll(self):
        return self.proc.poll()

    @staticmethod
    def add_padding(text):
        """
        ============= Adds padding to the text to make it look good ============
        """
        text = " %s " % text
        length = len(text)
        p1 = "=" * int((WIDTH - length)/2 + 0.5)
        p2 = "=" * int((WIDTH - length)/2)
        return p1 + text + p2
