from __future__ import annotations
from threading import Thread, Lock, Event
import tempfile
import signal
import json
import os

try:
    from .runner import RunManager
except ImportError:
    from runner import RunManager

# Import: lock_file, unlock_file, signal_register, signal_send, signal_cleanup,
#         pid_exists, SIGUSR1, SIGUSR2
#   from appropriate file
if os.name == "posix":
    try:
        from .signal_unix import *
    except ImportError:
        from signal_unix import *
elif os.name == "nt":
    try:
        from .signal_win import *
    except ImportError:
        from signal_win import *
else:
    raise RuntimeError(f"Unsupported OS: {os.name!r}")


MsgQueue:type = "Reference[list[object]]"
Writer:type = "Callable[str,bool]"
OnClose:type = "Callable[None]"

TMP_FOLDER:str = tempfile.gettempdir()
MASTER_PIPE:str = os.path.join(TMP_FOLDER, "bismuth-184.master.pipe")
SLAVE_PIPE:str = os.path.join(TMP_FOLDER, "bismuth-184.slave.pipe")
SLAVE_LOCK:str = os.path.join(TMP_FOLDER, "bismuth-184.slave.lock")

_slave_lock:File = None
_master_pid:int = 0
_self_pid:int = os.getpid()
_event:Event = Event()


def singleton() -> tuple[bool,Writer|MsgQueue,OnClose]:
    global _master_pipe, _slave_pipe, _slave_lock, _master_pid
    buffer:MsgQueue = []

    def _write_to_buffer(signum, frame) -> None:
        try:
            with open(SLAVE_PIPE, "br") as file:
                child_pid, data = json.loads(file.read().decode("utf-8"))
            buffer.append(data)
            signal_send(child_pid, SIGUSR1)
        except:
            RunManager().report_exc(critical=True)

    def _data_read(signum:int, frame:Frame) -> None:
        _event.set()

    def check_is_main() -> bool:
        global _slave_lock, _master_pipe, _slave_pipe, _master_pid
        if os.path.exists(MASTER_PIPE):
            # Check if master pid exists
            master_exists:bool = False
            try:
                with open(MASTER_PIPE, "r") as _master_pipe:
                    _master_pid = int(_master_pipe.read())
                    master_exists:bool = pid_exists(_master_pid)
            except ValueError:
                pass
            if not master_exists:
                os.remove(MASTER_PIPE)
                return check_is_main()
            # If master pid is alive, open slave stuff and return False
            signal_register(SIGUSR1, _data_read)
            _slave_lock = open(SLAVE_LOCK, "bw")
            lock_file(_slave_lock)
            _slave_pipe = open(SLAVE_PIPE, "bw")
            return False
        else:
            # If we are the master, set up and return True
            _master_pipe = open(MASTER_PIPE, "w")
            _master_pipe.write(str(_self_pid))
            _master_pipe.flush()
            signal_register(SIGUSR1, _write_to_buffer)
            return True

    is_main:bool = check_is_main()

    def on_close() -> None:
        signal_cleanup()
        if is_main:
            _master_pipe.close()
            os.remove(MASTER_PIPE)
        else:
            unlock_file(_slave_lock)
            _slave_lock.close()
            _slave_pipe.close()

    def write_message(message:object) -> bool:
        if not pid_exists(_master_pid):
            raise ProcessLookupError("Master died") from None
        _slave_pipe.seek(0)
        _slave_pipe.truncate(0)
        _slave_pipe.write(json.dumps((_self_pid, message)).encode("utf-8"))
        _slave_pipe.flush()
        try:
            signal_send(_master_pid, SIGUSR1)
            _event.wait()
            _event.clear()
            return True
        except OSError:
            raise ProcessLookupError("Master died") from None

    return is_main, (buffer if is_main else write_message), on_close


if __name__ == "__main__":
    is_main, buffer_or_writer, on_close = singleton()
    print(is_main)