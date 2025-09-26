from __future__ import annotations
from threading import Thread, Event as _Event
from time import sleep, perf_counter
from subprocess import Popen, PIPE
from signal import SIGTERM
import sys
import os

try:
    from signal import SIGKILL
except ImportError:
    SIGKILL = None

try:
    from .ipc import IPC, Event, pid_exists, SELF_PID, SIGUSR2, close_all_ipcs
except ImportError:
    from ipc import IPC, Event, pid_exists, SELF_PID, SIGUSR2, close_all_ipcs
from bettertk import IS_WINDOWS, IS_UNIX


SLAVE_PATH:str = os.path.join(os.path.dirname(__file__), "slave.py")
SLAVE_CMD:str = f'{sys.executable} "{SLAVE_PATH}" "{{}}" {{}}'


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
                       "eightBitInput: false",
                       "metaSendsEscape: true",
                       # "ScrollBar: on",
                       # "xterm*sixelScrolling: on",
                       # f"xterm*scrollbar.thumb: {THUMB_SPRITE}",
                     )
    XTERM_ARGS:str = "-b 0 -bw 0 -bc +ai -bg black -fg white -fa Monospace " \
                     "-fs 12 -cu -sb -rightbar -sl 100000 -ti 340 "
    for XTERM_XRM in XTERM_XRMS:
        XTERM_ARGS += f"-xrm 'xterm*{XTERM_XRM}' "
    XTERM_ARGS:str = XTERM_ARGS.removesuffix(" ")
else:
    ...


def timeout(timeout:float, interval:float, check_exit:Callable[bool]) -> bool:
    start:float = perf_counter()
    while perf_counter()-start < timeout:
        if check_exit():
            return False
        sleep(interval)
    return True

def invert(func:Callable) -> Callable:
    def inverted(*args:tuple, **kwargs:dict) -> bool:
        return not func(*args, **kwargs)
    return inverted

def kill_proc(send_signal:Callable[int,None], is_alive:Callable[bool]) -> None:
    send_signal(SIGTERM)
    if timeout(1, 0.05, invert(is_alive)): # 1 sec for cleanup before SIGKILL
        if SIGKILL is not None:
            send_signal(SIGKILL)


TERMINAL_IPC:IPC = IPC("terminaltk", sig=SIGUSR2)


class BaseTerminal:
    __slots__ = "proc", "_running", "resizable", "ipc", "slave_pid", \
                "_ready_event", "_bindings", "sep_window"

    def __init__(self, *, into:int=None) -> None:
        self.sep_window:bool = None
        self._bindings:dict = {}
        self.ipc:IPC = TERMINAL_IPC
        self.ipc.find_where("others")
        self.slave_pid:str = None
        # Set up vars
        self.resizable:bool = hasattr(self, "resize")
        self._running:bool = False
        # Start and wait until ready
        self._ready_event:_Event = _Event()
        self.bind("ready", self._ready)
        self.start(into=into)
        assert self.sep_window is not None, "Set `sep_window` please"
        assert self._running, "You must call \"self.run(command, env=env)\" " \
                             'inside "self.start"'
        self._ready_event.wait()
        Thread(target=self.close_on_dead_slave, daemon=True).start()

    def _ready(self, event:Event) -> None:
        self.slave_pid:str = event._from
        self._ready_event.set()
        self.unbind("ready", self._ready)

    def send_event(self, event:str, *, data:object=None) -> None:
        self.ipc.event_generate(event, where=self.slave_pid, data=data)
    send = send_event

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
        slave_cmd:str = SLAVE_CMD.format(self.ipc.name, SELF_PID)
        command:str = self.str_rreplace_once(command, "%command%", slave_cmd)
        self.proc:Popen = Popen(command, env=env, shell=True, stdout=PIPE,
                                stderr=PIPE)
        self._running:bool = True
        def is_ready() -> bool:
            return (self.slave_pid is not None) or \
                   (self.proc.poll() is not None)
        if timeout(2, 0.05, is_ready):
            raise RuntimeError("Slave didn't report its pid")
        if self.proc.poll() is not None:
            raise RuntimeError("Xterm closed too quickly. Do you have it " \
                               "installed? If you do, you might have a " \
                               "problem with its installation.")

    def close(self) -> None:
        if self.running():
            self.send("exit")
        self.proc.wait()

    def close_on_dead_slave(self) -> None:
        self.proc.wait()
        while self._bindings:
            event, handler = next(iter(self._bindings.keys()))
            self.unbind(event, handler)

    def running(self) -> bool:
        return self.proc.poll() is None

    def clear(self) -> None:
        self.send("print", data="\r\x1b[2J\x1b[3J\x1b[H\x1bc")

    def send_signal(self, signal:int) -> None:
        self.send("signal", data=signal)

    @staticmethod
    def str_rreplace_once(string:str, find:str, replace:str) -> str:
        return string.replace(find, replace)

    def start(self, *, into:int=None):
        raise NotImplementedError("Override this method, making sure you " \
                                  "call `self.run(command, env=env)` at " \
                                  "the end. Also please set `self.sep_window`" \
                                  "to a boolean.")


class XTermTerminal(BaseTerminal):
    __slots__ = ()

    def start(self, *, into:tk.Misc=None) -> None:
        self.sep_window:bool = False
        into_arg:str = ""
        if into is not None:
            into_arg:str = f"-into {into.winfo_id()}"
        command:str = f"xterm {into_arg} {XTERM_ARGS} -e %command%"
        self.run(command, env=os.environ|dict(force_color_prompt="yes"))

    def resize(self, *, width:int, height:int) -> None:
        assert isinstance(width, int), "TypeError"
        assert isinstance(height, int), "TypeError"
        self.send("print", data=f"\x1b[4;{height};{width}t")


class DebugXTermTerminal(XTermTerminal):
    def start(self, *, into:tk.Misc=None) -> None:
        super().start(into=into)
        if XTERM_DEBUG: Thread(target=self.debug_proc_end, daemon=True).start()

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


class GnomeTermTerminal(BaseTerminal):
    __slots__ = ()

    def start(self, *, into:tk.Misc=None) -> None:
        self.run("gnome-terminal -- %command%")
        self.sep_window:bool = True


class ConhostTerminal(BaseTerminal):
    __slots__ = ()

    def start(self, *, into:tk.Misc=None) -> None:
        self.run("conhost -- %command%")
        self.sep_window:bool = True


class KonsoleTerminal(BaseTerminal):
    __slots__ = ()

    def start(self, *, into:tk.Misc=None) -> None:
        raise NotImplementedError("Not implemented yet.")
        command:str = f"konsole -e %command%"
        self.sep_window:bool = True
        self.run(command)
        # `NoTitlebarTk._reparent_window()` and `echo $WINDOWID`

    def ___resize(self, width:int, height:int) -> None:
        raise RuntimeError("https://bugs.kde.org/show_bug.cgi?id=238073")


AVAILABLE_TERMS:list[type[BaseTerminal]] = [
                                             XTermTerminal,
                                             DebugXTermTerminal,
                                             KonsoleTerminal, # not working
                                             GnomeTermTerminal, # sep window
                                             ConhostTerminal, # sep window
                                           ]

if IS_UNIX:
    Terminal:type = XTermTerminal
elif IS_WINDOWS:
    Terminal:type = ConhostTerminal
else:
    print('[WARNING]: (Terminal) NotImplementedError')
    Terminal:type = type(None)
assert issubclass(Terminal, BaseTerminal|None), "You must subclass BaseTerminal."



if __name__ == "__main__":
    XTERM_DEBUG:bool = True
    term:Terminal = Terminal()
    term.send("run", data=(sys.executable,))
    term.bind("", lambda e: print(e))