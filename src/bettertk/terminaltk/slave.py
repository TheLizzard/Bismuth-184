"""
      +-----------------------------------------------------------------+
      | Bound events:                                                   |
      +-----------------------------------------------------------------+
      | run      | tuple[str] | Run a command (needs process)           |
      | pause    |            | Pause process (needs process)           |
      | unpause  |            | Unpause process (needs process)         |
      | signal   | int|Signal | Sends signal to process (needs process) |
      | print    | str        | Prints a string                         |
      | exit     |            | Drops everything and exits              |
      +-----------------------------------------------------------------+
      +-----------------------------------------------------------------+
      | Generated events:                                               |
      +-----------------------------------------------------------------+
      | ready    |            | Whenever ready for events               |
      | finished | int        | Process finished, exit code in data     |
      | running  |            | Responce to "run"                       |
      | exit     |            | Responce to "exit" at exit              |
      | error    | str        | An error occured, error msg in data     |
      +-----------------------------------------------------------------+

Notes for windows:
    for SIGINT use CTRL_C_EVENT signal
    for SIGKILL use "taskkill /f"
    for pause use DebugActiveProcess [debugapi.h (include Windows.h)]
    for unpause use DebugActiveProcessStop
"""
from __future__ import annotations
from sys import stdin, stdout, stderr, argv
from subprocess import Popen, check_output
from threading import Thread, Lock, Event as _Event
import signal as _signal
import traceback
import os


class Slave:
    __slots__ = "proc", "ipc", "_dead_event"

    def __init__(self, ipc:IPC) -> Slave:
        self._dead_event:_Event = _Event()
        self.proc:Popen = None
        self.ipc:IPC = ipc
        # Set up bindings:
        bind = lambda event, handler: ipc.bind(event, handler, threaded=True)
        bind("run", self.run)
        bind("pause", ipc.rm_event(self.pause))
        bind("unpause", ipc.rm_event(self.unpause))
        bind("signal", lambda event: self._send_signal(event.data))
        bind("print", lambda event: print(event.data, end="", flush=True))
        bind("exit", ipc.rm_event(self._dead_event.set))
        # Tell master we are ready
        self.ipc.event_generate("ready", where=MASTER_PID)

    def mainloop(self) -> None:
        while not self._dead_event.is_set():
            try:
                self._dead_event.wait()
            except KeyboardInterrupt:
                pass

    def _error(self, error:str) -> None:
        self.ipc.event_generate("error", where=MASTER_PID, data=error)

    def run(self, event:Event) -> None:
        if self.proc is not None:
            self._error("ProcAlreadyRunning")
        else:
            self._run(event.data)

    def pause(self) -> None:
        if os.name == "posix":
            self._send_signal(_signal.SIGSTOP)
        else:
            self._error("NotImplementedError")

    def unpause(self) -> None:
        if os.name == "posix":
            self._send_signal(_signal.SIGCONT)
        else:
            self._error("NotImplementedError")

    def _run(self, command:tuple[str]) -> None:
        if len(command) == 0:
            return self._error("EmptyCommand")
        if command[0] == "cd":
            return self.cd(command)
        self.proc:Popen = Popen(command, stdin=stdin, stdout=stdout,
                                stderr=stderr, shell=False)
        self.ipc.event_generate("running", where=MASTER_PID)
        def wait() -> None:
            self.proc.wait()
            exit_code:int = self.proc.poll()
            self.proc:Popen = None
            reset_stdin()
            self.ipc.event_generate("finished", where=MASTER_PID,
                                    data=exit_code)
        Thread(target=wait, daemon=True).start()

    def _send_signal(self, signal:_signal.Signals|int) -> None:
        if not isinstance(signal, _signal.Signals|int):
            return self._error("InvalidSignal")
        if self.proc is None:
            return None
        self.proc.send_signal(signal)

    def cd(self, command:tuple[str]) -> None:
        exit_code:int = 1
        assert command[0] == "cd", "InternalError"
        if len(command) == 1:
            print("slave: cd: no argument")
        elif len(command) == 2:
            try:
                os.chdir(command[1])
                exit_code:int = 0
            except OSError as error:
                print(error)
        else:
            print("slave: cd: too many arguments")
        self.ipc.event_generate("finished", where=MASTER_PID, data=exit_code)


try:
    from ipc import IPC, Event, SIGUSR1, SIGUSR2, Location

    if os.name == "posix":
        # https://docs.python.org/3/library/termios.html#example
        import termios
        default_stdin_state = termios.tcgetattr(stdin.fileno())
        def reset_stdin() -> None:
            termios.tcsetattr(stdin.fileno(), termios.TCSADRAIN,
                              default_stdin_state)
    else:
        reset_stdin = lambda: None

    assert len(argv) == 3, "Wrong number of command line args"
    MASTER_PID:Location = argv[2]
    ipc:IPC = IPC(argv[1], sig=SIGUSR2)
    try:
        slave:Slave = Slave(ipc)
        slave.mainloop()
    finally:
        ipc.event_generate("exit", where=MASTER_PID)
        ipc.close()
except SystemExit:
    pass
except BaseException:
    import os, traceback
    path = os.path.dirname(__file__)
    with open(os.path.join(path, "err_tb.txt"), "w") as file:
        file.write(traceback.format_exc())