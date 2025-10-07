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
      | ping     |            | Got a ping, respond with pong           |
      +-----------------------------------------------------------------+
      +-----------------------------------------------------------------+
      | Generated events:                                               |
      +-----------------------------------------------------------------+
      | ready    |            | Whenever ready for events               |
      | finished | int        | Process finished, exit code in data     |
      | running  |            | Responce to "run"                       |
      | exit     |            | Responce to "exit" at exit              |
      | error    | str        | An error occured, error msg in data     |
      | ping     |            | Send a ping, master should pong         |
      | pong     |            | Respond to master's ping with pong      |
      +-----------------------------------------------------------------+

Notes for windows:
    for SIGINT use CTRL_C_EVENT signal
    for SIGKILL use "taskkill /f"
    for pause use DebugActiveProcess [debugapi.h (include Windows.h)]
    for unpause use DebugActiveProcessStop
"""
from __future__ import annotations
from threading import Thread, Lock, Event as _Event
from sys import stdin, stdout, stderr, argv
from subprocess import Popen, check_output
import signal as _signal
from time import sleep
import traceback
import os


Break:type = bool
def rm_event(func:"Callable[Break|None]") -> "Callable[ipc.Event,Break|None]":
    """
    A higher order function that takes a function that takes no args
    and returns a function that takes 1 arg that is ignored
    """
    def inner(event:"ipc.Event") -> "Break|None":
        return func()
    return inner


class Slave:
    __slots__ = "proc", "ipc", "_dead_event"

    def __init__(self, ipc:IPC) -> Slave:
        self._dead_event:_Event = _Event()
        self.proc:Popen = None
        self.ipc:IPC = ipc
        # Set up bindings:
        bind = lambda event, handler: ipc.bind(event, handler, threaded=True)
        bind("run", self.run)
        bind("pause", rm_event(self.pause))
        bind("unpause", rm_event(self.unpause))
        bind("signal", lambda event: self._send_signal(event.data))
        bind("print", lambda event: print(event.data, end="", flush=True))
        bind("exit", rm_event(self._dead_event.set))
        bind("ping", lambda event: self.send("pong", event.data))
        # Tell master we are ready
        self.send("ready")
        # Die if master is dead
        Thread(target=self._die_with_master, daemon=True).start()

    def _die_with_master(self) -> None:
        while self.ipc.find_where(MASTER_PID):
            sleep(2)
        self._dead_event.set()

    def mainloop(self) -> None:
        while not self._dead_event.is_set():
            try:
                self._dead_event.wait()
            except KeyboardInterrupt:
                pass

    def send(self, event:str, data:object=None) -> None:
        self.ipc.event_generate(event, where=MASTER_PID, data=data)

    def run(self, event:Event) -> None:
        if self.proc is not None:
            self.send("error", "ProcAlreadyRunning")
        else:
            self._run(event.data)

    def pause(self) -> None:
        if os.name == "posix":
            self._send_signal(_signal.SIGSTOP)
        else:
            self.send("error", "NotImplementedError")

    def unpause(self) -> None:
        if os.name == "posix":
            self._send_signal(_signal.SIGCONT)
        else:
            self.send("error", "NotImplementedError")

    def _run(self, command:tuple[str]) -> None:
        if len(command) == 0:
            return self.send("error", "EmptyCommand")
        if command[0] == "cd":
            return self.cd(command)
        elif command[0] == "export":
            return self.export(command)
        try:
            self.proc:Popen = Popen(command, stdin=stdin, stdout=stdout,
                                    stderr=stderr, shell=False, env=os.environ)
        except FileNotFoundError:
            self.send("error", f"Invalid executable: {command[0]!r}")
            return None
        self.send("running")
        def wait() -> None:
            self.proc.wait()
            exit_code:int = self.proc.poll()
            self.proc:Popen = None
            reset_stdin()
            self.send("finished", data=exit_code)
        Thread(target=wait, daemon=True).start()

    def _send_signal(self, signal:_signal.Signals|int) -> None:
        if not isinstance(signal, _signal.Signals|int):
            return self.send("error", "InvalidSignal")
        if self.proc is None:
            return None
        self.proc.send_signal(signal)

    def cd(self, command:tuple[str]) -> None:
        assert command[0] == "cd", "InternalError"
        exit_code:int = 1
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
        self.send("finished", data=exit_code)

    def export(self, command:tuple[str]) -> None:
        assert command[0] == "export", "InternalError"
        exit_code:int = 1
        if len(command) == 3:
            _, variable, value = command
            os.environ[variable] = value
            exit_code:int = 0
        else:
            print("slave: export: needs exactly 2 arguments")
        self.send("finished", data=exit_code)


try:
    from ipc import IPC, Event, SIGUSR2, Location, close_all_ipcs

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
        slave.send("exit")
    finally:
        close_all_ipcs()
except SystemExit:
    pass
except BaseException:
    import os, traceback
    path = os.path.dirname(__file__)
    with open(os.path.join(path, "err_tb.txt"), "w") as file:
        file.write(traceback.format_exc())