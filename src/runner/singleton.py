from __future__ import annotations
from threading import Thread, Lock, Event
import pickle
import signal
import fcntl
import os

try:
    from .runner import RunManager
except ImportError:
    from runner import RunManager


MsgQueue:type = "Reference[list[object]]"
Writer:type = "Callable[str,bool]"
OnClose:type = "Callable[None]"

MASTER_FILE:str = "/tmp/bismuth-184.master.lock"
SLAVE_FILE:str = "/tmp/bismuth-184.slave.lock"


lock_file = lambda file: fcntl.flock(file, fcntl.LOCK_EX)
unlock_file = lambda file: fcntl.flock(file, fcntl.LOCK_UN)

_master_file:File = None
_slave_file:File = None
_master_pid:int = 0
_self_pid:int = os.getpid()
_event:Event = Event()


def singleton() -> tuple[bool,Writer|MsgQueue]:
    global _master_file, _slave_file, _master_pid
    buffer:MsgQueue = []

    def _write_to_buffer(signum, frame) -> None:
        try:
            with open(SLAVE_FILE, "br") as file:
                child_pid, data = pickle.loads(file.read())
            buffer.append(data)
            os.kill(child_pid, signal.SIGUSR1)
        except:
            RunManager().report_exc(critical=True)

    def _data_read(signum, frame) -> None:
        unlock_file(_slave_file)
        _event.set()

    def check_is_main() -> bool:
        global _master_file, _slave_file, _master_pid
        if os.path.exists(MASTER_FILE):
            with open(MASTER_FILE, "r") as _master_file:
                try:
                    _master_pid = int(_master_file.read())
                    os.kill(_master_pid, 0)
                except (ValueError, OSError):
                    os.remove(MASTER_FILE)
                    return check_is_main()
            signal.signal(signal.SIGUSR1, _data_read)
            _slave_file = open(SLAVE_FILE, "bw")
            return False
        else:
            _master_file = open(MASTER_FILE, "w")
            lock_file(_master_file)
            _master_file.write(str(_self_pid))
            _master_file.flush()
            signal.signal(signal.SIGUSR1, _write_to_buffer)
            with open(SLAVE_FILE, "w") as _slave_file:
                pass
            return True

    is_main:bool = check_is_main()

    def on_close() -> None:
        if is_main:
            _master_file.close()
            os.remove(MASTER_FILE)
        else:
            _slave_file.close()

    def write_message(message:object) -> bool:
        lock_file(_slave_file)
        _slave_file.seek(0)
        _slave_file.truncate(0)
        _slave_file.write(pickle.dumps((_self_pid, message)))
        _slave_file.flush()
        try:
            os.kill(_master_pid, signal.SIGUSR1)
            _event.wait()
            _event.clear()
            return True
        except OSError:
            RunManager().report_exc(True, "Master died")
            return False

    return is_main, (buffer if is_main else write_message), on_close


"""
def wrap_reader_into_queue(reader:Callable[object]) -> Reference[list[object]]:
    queue:Reference[list[str]] = []
    def read_append_loop() -> None:
        while True:
            try:
                queue.append(reader())
            except BaseException as error:
                if not isinstance(error, EOFError|SystemExit):
                    RunManager().report_exc(critical=False)
                break
    Thread(target=read_append_loop, daemon=True).start()
    return queue
"""


if __name__ == "__main__":
    is_main, func, onclose = singleton()
    # onclose()