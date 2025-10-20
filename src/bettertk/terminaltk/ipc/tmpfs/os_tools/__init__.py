from __future__ import annotations
from threading import Thread
import signal as _signal
import os

if os.name not in ("nt", "posix"):
    raise OSError(f"Unknown OS: {os.name!r}")

try:
    if os.name == "nt":
        from .os_tools_win import *
    elif os.name == "posix":
        from .os_tools_posix import *
except ImportError:
    if os.name == "nt":
        from os_tools_win import *
    elif os.name == "posix":
        from os_tools_posix import *


_signal_handlers:dict[int:Callable] = {}
_events:list[NamedSemaphore] = []
SELF_PID:int = os.getpid()
_stop:bool = False

MAX_SIGUSR_N:int = 10
for i in range(1, MAX_SIGUSR_N+1):
    globals()[f"SIGUSR{i}"] = _signal.NSIG + i
SIG_DFL = SIG_IGN = object()


def signal_register(signal:int, handler:Callable) -> None:
    if _stop: return None
    assert isinstance(signal, int), "TypeError"
    assert callable(handler) or (handler is SIG_DFL), "TypeError"

    # Loop to check if the signal has been activated
    def call_loop() -> None:
        while event in _events:
            event.wait_clear()
            if _stop: break
            handler:Callable = _signal_handlers[signal]
            if handler is not SIG_DFL:
                handler(signal, None)
        event.unlink()

    _is_new_signal:bool = (_signal_handlers.get(signal, None) is None)
    _signal_handlers[signal] = handler
    # Create event and start loop
    if _is_new_signal:
        event:NamedSemaphore = NamedSemaphore(f"_signal_{SELF_PID}_{signal}",
                                              create=True)
        _events.append(event)
        Thread(target=call_loop, daemon=True).start()

def signal_get(signal:int) -> Callable:
    if _stop: return None
    return _signal_handlers.get(signal, SIG_DFL)

def signal_send(pid:int, signal:int) -> None:
    assert signal != 0, "Use `pid_exists(pid:int) -> bool` instead"
    NamedSemaphore(f"_signal_{pid}_{signal}", create=False).set().close()

def signal_cleanup() -> None:
    global _stop
    if _stop: return None
    _stop = True
    while _events:
        _events.pop().set()


_namedlock_dict:dict = {"acquire":NamedSemaphore.wait_clear,
                        "release":NamedSemaphore.set}
NamedLock:type = type("NamedLock", (NamedSemaphore,), _namedlock_dict)
NamedEvent:type = type("NamedEvent", (NamedSemaphore,), {})
