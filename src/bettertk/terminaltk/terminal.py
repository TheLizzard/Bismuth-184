from __future__ import annotations
from threading import Thread, Event as _Event
from time import sleep, perf_counter
from signal import SIGTERM, SIGKILL
from subprocess import Popen, PIPE
import sys
import os

try:
    from .ipc import IPC, Event, pid_exists, SELF_PID, SIGUSR1, SIGUSR2
except ImportError:
    from ipc import IPC, Event, pid_exists, SELF_PID, SIGUSR1, SIGUSR2
from bettertk import IS_WINDOWS, IS_UNIX


SLAVE_PATH:str = os.path.join(os.path.dirname(__file__), "slave.py")


if IS_WINDOWS:
    ...
elif IS_UNIX:
    XTERM_DEBUG:bool = False
    XTERM_KEY_BINDINGS:str = r" \n ".join((
                              "Ctrl Shift <Key>C: copy-selection(CLIPBOARD)",
                              "Ctrl <Key>V: insert-selection(CLIPBOARD)",
                              "Ctrl <Key>W: quit()",
                              # "Ctrl <Key>X: copy-selection(CLIPBOARD)",
                              "Shift <Key>Left: keymap(None)",
                              "Shift <Key>Right: keymap(None)",
                              "Shift <Key>Up: keymap(None)",
                              "Shift <Key>Down: keymap(None)",
                              "Ctrl <Key>KP_Add: larger-vt-font()",
                              "Ctrl <Key>KP_Subtract: smaller-vt-font()",
                              "Ctrl <Key>+: larger-vt-font()",
                              "Ctrl <Key>-: smaller-vt-font()",
                                         ))
    XTERM_XRMS:str = (
                       f"VT100.Translations: #override {XTERM_KEY_BINDINGS}",
                       # Do NOT delete the next line!
                       #r"VT100.Translations: #override Ctrl Shift <Key>C: copy-selection(CLIPBOARD) \n Ctrl <Key>V: insert-selection(CLIPBOARD) \n Ctrl <Key>W: quit() \n Ctrl <Key>X: copy-selection(CLIPBOARD)",
                       "curses: true",
                       "cutNewline: true",
                       "scrollTtyOutput: false",
                       "autoScrollLock: true",
                       "jumpScroll: false",
                       "scrollKey: true",
                       "omitTranslation: popup-menu",
                       "allowWindowOps: true",
                       "bellOnReset: false",
                       # "ScrollBar: on",
                       # "xterm*sixelScrolling: on",
                       # f"xterm*scrollbar.thumb: {THUMB_SPRITE}",
                     )
    XTERM_ARGS:str = "-b 0 -bw 0 -bc +ai -bg black -fg white -fa Monospace " \
                     "-fs 12 -cu -sb -rightbar -sl 100000 "
    for XTERM_XRM in XTERM_XRMS:
        XTERM_ARGS += f"-xrm 'xterm*{XTERM_XRM}' "
    XTERM_ARGS += f'-e {sys.executable} "{SLAVE_PATH}" "{{}}" "{{}}"'
    KONSOLE_ARGS = f'-e {sys.executable} "{SLAVE_PATH}" "{{}}" "{{}}"'
else:
    ...


def kill_proc(send_signal:Callable[int,None], is_alive:Callable[bool]) -> None:
    send_signal(SIGTERM)
    start:float = perf_counter()
    while perf_counter()-start < 3: # 3 sec for cleanup before SIGKILL
        if not is_alive():
            return None
        sleep(0.05)
    send_signal(SIGKILL)


TERMINAL_IPC:IPC = IPC("terminaltk", sig=SIGUSR2)


class BaseTerminal:
    __slots__ = "proc", "_running", "resizable", "ipc", "slave_pid", \
                "_ready_event", "_bindings"

    def __init__(self, *, into:int=None) -> None:
        self._bindings:dict = {}
        self.ipc:IPC = TERMINAL_IPC
        self.ipc.find_where("others")
        self.slave_pid:str = None
        # Create IPC
        # name:str = IPC.get_empty_name("instance-%d%d%d", "terminaltk",
        #                               is_abandoned=self._is_abandoned)
        # if name is None:
        #     raise FileExistsError("too many terminals exist already")
        # self.ipc:IPC = IPC(name)
        # with self.ipc._fs.open("owner_pid", "w") as file:
        #     file.write(str(SELF_PID))
        # Set up vars
        self.resizable:bool = hasattr(self, "resize")
        self._running:bool = False
        # Start and wait until ready
        self._ready_event:_Event = _Event()
        self.bind("ready", self._ready)
        self.start(self.ipc.name, into=into)
        assert self._running, "You must call \"self.run(command, env=env)\" " \
                             'inside "self.start"'
        self._ready_event.wait()

    def _ready(self, event:Event) -> None:
        self.slave_pid:str = event._from
        self._ready_event.set()
        self.unbind("ready", self._ready)

    def send_event(self, event:str, *, data:object=None) -> None:
        self.ipc.event_generate(event, where=self.slave_pid, data=data)

    def bind(self, event:str, handler:Callable[Event,None], **kwargs) -> None:
        # Call handler iff it's from the correct pid or event is ready
        def new_handler(event:Event) -> None:
            if (event._from == self.slave_pid) or (event.type == "ready"):
                handler(event)
        # Add new_handler to binding mapping
        if (event,handler) in self._bindings:
            raise RuntimeError("Can't bind the same function twice to " \
                               "same event. Also it's useless??")
        self._bindings[(event,handler)] = new_handler
        # Actual binding
        self.ipc.bind(event, new_handler, **kwargs)

    def unbind(self, event:str, handler:Callable) -> None:
        self.ipc.unbind(event, self._bindings[(event,handler)])
        self._bindings.pop((event,handler))

    @staticmethod
    def _is_abandoned(fs:Filesystem, name:str) -> bool:
        filename:str = fs.join(name, "owner_pid")
        if not fs.exists(filename):
            return False
        with fs.open(filename, "rb") as file:
            try:
                pid:int = int(file.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return False
        return not pid_exists(pid)

    def run(self, command:str, *, env:dict[str,str]=os.environ) -> None:
        self.proc:Popen = Popen(command, env=env, shell=True, stdout=PIPE,
                                stderr=PIPE)
        self._running:bool = True
        while self.slave_pid is None:
            sleep(0.1)

    def close(self) -> None:
        _dead_event:_Event = _Event()
        self.bind("exit", self.ipc.rm_event(_dead_event.set))
        self.send_event("exit")
        while (not _dead_event.wait(0.1)) and pid_exists(self.slave_pid):
            pass
        if self.proc.poll is None:
            kill_proc(self.proc.send_signal, lambda: not self.proc.poll())
        while self._bindings:
            event, handler = next(iter(self._bindings.keys()))
            self.unbind(event, handler)

    def running(self) -> bool:
        return self.proc.poll() is None

    def clear(self) -> None:
        self.send_event("print", data="\r\x1b[2J\x1b[3J\x1b[H\x1bc")

    def send_signal(self, signal:int) -> None:
        self.send_event("signal", data=signal)

    def start(self, ipc_name:str, *, into:int=None):
        raise NotImplementedError("Override this method, making sure you " \
                                  "call `self.run(command, env=env)` at " \
                                  "the end")


class XTermTerminal(BaseTerminal):
    __slots__ = ()

    def start(self, ipc_name:str, *, into:tk.Misc=None):
        args:str = XTERM_ARGS.format(ipc_name, SELF_PID)
        if into is None:
            command:str = f"xterm {args}"
        else:
            command:str = f"xterm -into {into.winfo_id()} {args}"
        self.run(command, env=os.environ|dict(force_color_prompt="yes"))
        if XTERM_DEBUG: Thread(target=self.debug_proc_end, daemon=True).start()

    def resize(self, *, width:int, height:int) -> None:
        assert isinstance(width, int), "TypeError"
        assert isinstance(height, int), "TypeError"
        self.send_event("print", data=f"\x1b[4;{height};{width}t")

    def debug_proc_end(self) -> None:
        def inner(_:Event=None) -> None:
            stdout:bytes = self.proc.stdout.read()
            stderr:bytes = self.proc.stderr.read()
            print(" stdout ".center(80, "#"))
            if len(stdout+stderr) > 0:
                print(stdout)
                print(" stderr ".center(80, "#"))
                print(stderr)
        self.bind("exit", inner)


class KonsoleTerminal(BaseTerminal):
    __slots__ = ()

    def start(self, ipc_name:str, *, into:tk.Misc=None):
        raise NotImplementedError("Not fully implemented. " \
                                  "Read the comment bellow")
        args:str = KONSOLE_ARGS.format(ipc_name, SELF_PID)
        self.run(f"konsole {args}")
        # Now we have to use `NoTitlebarTk._get_parent` on into
        #   maybe even on into's tk.Tk and then use
        #   `NoTitlebarTk._reparent_window(child, parent, x, y)`
        #   where child is the output from "echo $WINDOWID" when run
        #   from the slave

    def ___resize(self, width:int, height:int) -> None:
        raise RuntimeError("https://bugs.kde.org/show_bug.cgi?id=238073")


if IS_UNIX:
    Terminal:type = XTermTerminal
else:
    print('[WARNING]: (Terminal) NotImplementedError')
    Terminal:type = type(None)
assert issubclass(Terminal, BaseTerminal|None), "You must subclass BaseTerminal."



if __name__ == "__main__":
    XTERM_DEBUG:bool = True
    term:Terminal = Terminal()
    term.send_event("run", data=("python3",))
    term.bind("", lambda e: print(e))