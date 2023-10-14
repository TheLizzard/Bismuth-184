from __future__ import annotations
pipe = None
try:
    from sys import stdin, stdout, stderr, argv
    from subprocess import Popen, check_output
    from threading import Thread, Lock
    import array, fcntl, termios
    import signal as _signal
    from time import sleep
    import traceback
    import signal
    import os

    # This file should never be imported just ran from python's interpreter
    from piper import PipePair
    IS_UNIX:bool = (os.name == "posix")
    IS_WINDOWS:bool = (os.name == "nt")


    """
    # https://www.ibm.com/docs/en/zos/2.4.0?topic=keyboard-escape-sequences-control-characters
    # https://wiki.linuxquestions.org/wiki/List_of_Keysyms_Recognised_by_Xmodmap
    # https://invisible-island.net/xterm/manpage/xterm.html
    # https://www.delorie.com/djgpp/doc/libc/libc_495.html
    # https://stackoverflow.com/a/59807248/11106801
    # https://docs.python.org/3/library/signal.html

    Signals [master => slave]:
    +------+--------------------+---------+--------------------------------------+
    | UWIN | NAME               | SIGNAL  | DESC                                 |
    +------+--------------------+---------+--------------------------------------+
    | ###  | RUN<args><char*>   |         | put the command in the queue         |
    | #M # | PAUSE              | SIGSTOP | pause immediately                    |
    | #M # | UNPAUSE            | SIGCONT | unpause after PAUSE                  |
    | ###? | RESTART            |         | Re-run the last command if ended     |
    | #### | STOP               | SIGTERM | clean up and stop asap               |
    | #### | KILL               | SIGABRT | clean up and stop immediately        |
    | #M # | FORCE_KILL         | SIGKILL | halt immediately and drop everything |
    | #M## | INT                | SIGINT  | KeyboardInterrupt                    |
    | ###  | EXIT               |         | Kill self when done                  |
    | ###  | =                  |         | ping                                 |
    | ###  | #                  |         | pong                                 |
    | ###  | PRINTSTR<char*>    |         | String to print immediately          |
    | ###  | CHECK_STDOUT<args> |         | Run a command and return the output  |
    | ###  | CANCEL_ALL         |         | Cancels all procs in queue           |
    +------+--------------------+---------+--------------------------------------+
    Notes:
        UWIN = Exists in Unix, Exists in Windows, Implemented, Need a proc running
        args = (<uint_2>) (<uint_2>)       [(<char*>)*]
             = cmd_id     number of args   [args*]

    Signals [master <= slave]:
        STARTED                    # The slave was born
        EXITCODE<uint_2><uint_4>   # A proc has returned an exit code
        OUTPUT<uint_2><char*>      # The output from CHECK_STDOUT
        ERR<uint_2>                # Error (look at error codes)
        RUNNING<uint_2>            # Running command with cmd_id
        "$PONG_SIGNAL"             # Responce to ping
        "$PING_SIGNAL"             # Requesting master to write "$PONG_SIGNAL"

    Error Codes:
        ERR_CMDS_QUEUE_NOT_EMPTY = 1
        ERR_NO_LAST_CMD = 2
        ERR_NO_PROC = 3

    Notes for windows:
        for SIGINT use CTRL_C_EVENT signal
        for FORCE_KILL [SIGKILL] use "taskkill /f"
        for pause use DebugActiveProcess [debugapi.h (include Windows.h)]
        for unpause use DebugActiveProcessStop
        also helpfull: GetProcessId
    """

    def allisinstance(iterable:Iterable, T:type) -> bool:
        return all(map(lambda elem: isinstance(elem, T), iterable))


    SIGNALS:tuple[bytes] = (b"RUN", b"PAUSE", b"UNPAUSE", b"RESTART", b"STOP",
                            b"KILL", b"FORCE_KILL", b"INT", b"EXIT", b"=", b"#",
                            b"PRINTSTR", b"CHECK_STDOUT", b"CANCEL_ALL")
    MAX_SIGNAL_LENGTH:int = max(map(len, SIGNALS))
    assert allisinstance(SIGNALS, bytes), "Not all signal are bytes"
    PING_SIGNAL:bytes = b"="
    PONG_SIGNAL:bytes = b"#"
    for a in SIGNALS:
        for b in SIGNALS:
            assert a.startswith(b) == (a==b), "Invalid set of signals [not LL(1)]"
    assert PING_SIGNAL in SIGNALS, "Ping signal not in SIGNALS"
    assert PONG_SIGNAL in SIGNALS, "Pong signal not in SIGNALS"

    CHUNK_SIZE:int = 5*1024    # pipe read chunk size (no point above 4096)
    REFRESH_RATE:int = 200     # milliseconds to sleep at each iteration
    END_REFRESH_RATE:int = 200 # milliseconds checking if term has exited


    ERR_CMDS_QUEUE_NOT_EMPTY:bytes = b"\x00\x01" # RESTART signal failed
    ERR_NO_LAST_CMD:bytes = b"\x00\x02"          # RESTART signal failed
    ERR_NO_PROC:bytes = b"\x00\x03"              # a proc signal failed

    TRUE_PATH:str = "/bin/true"
    FALSE_PATH:str = "/bin/false"


    class CorruptedSignal(RuntimeError): ...


    class Buffer:
        __slots__ = "data", "lock"

        def __init__(self) -> Buffer:
            self.lock:Lock = Lock()
            self.data:bytes = b""

        def __len__(self) -> int:
            return len(self.data)

        def __repr__(self) -> str:
            return f'Buffer("{repr(self.data)[2:-1]}")'

        def read(self, length:int, blocking:bool=False) -> bytes:
            buffer:bytes = self._read(length)
            while blocking and (len(buffer) < length):
                buffer += self._read(length-len(buffer))
            assert (not blocking) | (len(buffer) == length), "InternalError"
            assert len(buffer) <= length, "InternalError"
            return buffer

        def _read(self, length:int) -> bytes:
            assert isinstance(length, int), "TypeError"
            assert length >= 0, "Length must be >= 0"
            with self.lock:
                ret, self.data = self.data[:length], self.data[length:]
            return ret

        def write(self, data:bytes) -> None:
            assert isinstance(data, bytes), "TypeError"
            with self.lock:
                self.data += data

        def peek(self, length:int) -> bytes:
            assert isinstance(length, int), "TypeError"
            assert length >= 0, "Length must be >= 0"
            return self.data[:length]

        def read_char_star(self) -> bytes:
            buffer:bytes = b""
            while True:
                buffer += self.read(1, blocking=True)
                if buffer[-1] == 0:
                    return buffer

        def read_uint_inf(self, *, end:bytes) -> int:
            assert isinstance(end, bytes), "TypeError"
            buffer:bytes = b""
            while buffer[-len(end):] != end:
                buffer += self.read(1, blocking=True)
            return int(buffer[:-len(end)].decode("utf-8"))

        def parse_signal(self) -> str|None:
            buffer:bytes = b""
            while len(self)-len(buffer) > 0:
                buffer:bytes = self.peek(len(buffer)+1)
                if len(buffer) == 0: return None
                if buffer in SIGNALS:
                    return self.read(len(buffer))
                if len(buffer) == MAX_SIGNAL_LENGTH:
                    raise CorruptedSignal(f"Corrupted signal {buffer!r}, " \
                                          "can't recover.")
            return None

        def read_run_args(self) -> tuple[str]:
            length:int = int.from_bytes(self.read(2, blocking=True), "big")
            commands:list[str] = []
            for i in range(length):
                command:bytes = self.read_char_star()[:-1]
                commands.append(command.decode("utf-8"))
            return tuple(commands)


    class ProcManager:
        __slots__ = "cmds_queue", "proc", "last_command"

        def __init__(self) -> ProcManager:
            self.last_command:tuple[int,tuple[str],str] = None
            self.cmds_queue:list[(int,tuple[str],str)] = []
            self.proc:Popen = None

        def start_proc(self, cmd_id:int, command:tuple[str], string:str) -> None:
            assert self.proc is None, "Proc already running"
            assert isinstance(cmd_id, int), "TypeError"
            assert isinstance(command, tuple), "TypeError"
            assert allisinstance(command, str), "TypeError"
            assert isinstance(string, str), "TypeError"
            print(string, end="", flush=True)
            if command[0] == "cd":
                command:tuple[str] = self.cd(command[1:])
            self.proc:Popen = Popen(command, stdin=stdin, stdout=stdout,
                                    stderr=stderr, shell=False)
            self.last_command:tuple[int,tuple[str],str] = (cmd_id, command, string)
            pipe.write(b"RUNNING" + cmd_id.to_bytes(2,"big"))

        def cd(self, args:tuple[str]) -> tuple[str]:
            if len(args) == 0:
                print("slave: cd: no argument")
            elif len(args) == 1:
                try:
                    os.chdir(args[0])
                    return (TRUE_PATH,)
                except OSError as error:
                    print(error)
                    pass
            elif len(args) >= 3:
                print("slave: cd: too many arguments")
            return (FALSE_PATH,)

        def cancel_all(self) -> None:
            self.cmds_queue.clear()

        def send_signal(self, sig:bytes) -> None:
            global running, wants_exit
            assert isinstance(sig, bytes), "TypeError"
            if sig == b"EXIT":
                wants_exit = True
                return None
            elif sig == PING_SIGNAL:
                pipe.write(PONG_SIGNAL)
                return None
            elif sig == PONG_SIGNAL:
                ...
                return None
            if sig == b"RESTART":
                if self.last_command is None:
                    pipe.write(b"ERR" + ERR_NO_LAST_CMD)
                    return None
                if len(self.cmds_queue) != 0:
                    pipe.write(b"ERR" + ERR_CMDS_QUEUE_NOT_EMPTY)
                    return None
                self.cmds_queue.append(self.last_command)
                return None
            if sig == b"INT":
                if IS_UNIX:
                    self._send_signal(_signal.SIGINT)
                    return None
                if IS_WINDOWS:
                    self._send_signal(_signal.CTRL_C_EVENT)
                    return None
            if sig == b"STOP":
                self._send_signal(_signal.SIGTERM)
                print() # Empty line after proc ends
                return None
            if sig == b"KILL":
                self._send_signal(_signal.SIGABRT)
                print() # Empty line after proc ends
                return None
            if sig == b"PAUSE":
                if IS_UNIX:
                    self._send_signal(_signal.SIGSTOP)
                    return None
                if IS_WINDOWS:
                    ...
            if sig == b"UNPAUSE":
                if IS_UNIX:
                    self._send_signal(_signal.SIGCONT)
                    return None
                if IS_WINDOWS:
                    ...
            if sig == b"FORCE_KILL":
                if IS_UNIX:
                    self._send_signal(_signal.SIGKILL)
                    return None
                if IS_WINDOWS:
                    ...
            print(f"NotImplementedError({sig})", flush=True)

        def _send_signal(self, signal:int) -> None:
            if self.proc is None:
                pipe.write(b"ERR" + ERR_NO_PROC)
            else:
                self.proc.send_signal(signal)

        def append(self, cmd_id:int, command:tuple[str], str_to_print:str) -> None:
            if wants_exit: return None
            assert isinstance(cmd_id, int), "TypeError"
            assert isinstance(command, tuple), "TypeError"
            assert allisinstance(command, str), "TypeError"
            assert isinstance(str_to_print, str), "TypeError"
            self.cmds_queue.append((cmd_id, command, str_to_print))
            self.tickle()

        def tickle(self) -> None:
            global running
            if wants_exit and (self.proc is None):
                running = False
                return None
            elif self.proc is not None:
                exit_code:int = self.proc.poll()
                if exit_code is not None:
                    if IS_UNIX:
                        exit_code %= 256
                    if IS_WINDOWS:
                        exit_code %= 2**32
                    cmd_id:bytes = self.last_command[0].to_bytes(2, "big")
                    exit_code_encoded:bytes = exit_code.to_bytes(4, "big")
                    pipe.write(b"EXITCODE" + cmd_id + exit_code_encoded)
                    self.proc:Popen = None
                    self.reset_stdin()
                    self.tickle()
            elif len(self.cmds_queue) != 0:
                self.start_proc(*self.cmds_queue.pop(0))

        def reset_stdin(self) -> None:
            if IS_UNIX:
                # https://docs.python.org/3/library/termios.html#example
                termios.tcsetattr(stdin.fileno(), termios.TCSADRAIN,
                                  default_stdin_state)


    def parse_buffer(buffer, proc_manager, signals_queue:list[str]) -> None:
        global running, wants_exit
        while running and (not wants_exit): # read full buffer, return None
            signal:bytes = buffer.parse_signal()
            if signal == b"RUN":
                cmd_id:int = int.from_bytes(buffer.read(2, blocking=True), "big")
                command:tuple[str] = buffer.read_run_args()
                string_to_print:str = buffer.read_char_star()[:-1].decode("utf-8")
                proc_manager.append(cmd_id, command, string_to_print)
            #elif signal == REPORT_SIGNAL:
            #    buf = array.array("H", [0,0,0,0])
            #    fcntl.ioctl(1, termios.TIOCGWINSZ, buf)
            #    output:bytes = b"REPORT"
            #    for i in buf:
            #        output += i.to_bytes(2,"big")
            #    pipe.write(output)
            elif signal == b"CANCEL_ALL":
                proc_manager.cancel_all()
            elif signal == b"CHECK_STDOUT":
                cmd_id:int = int.from_bytes(buffer.read(2, blocking=True), "big")
                command:tuple[str] = buffer.read_run_args()
                output:bytes = check_output(command, shell=False)
                if b"\x00" in output:
                    output:bytes = b"ERROR_INVALID_CHAR"
                pipe.write(b"OUTPUT" + cmd_id.to_bytes(2,"big") + output + b"\x00")
            elif signal == b"PRINTSTR":
                string:str = buffer.read_char_star()[:-1].decode("utf-8")
                print(string, end="", flush=True)
            elif signal is None:
                return None
            else:
                signals_queue.append(signal)

    def read_pipe(buffer:Buffer) -> None:
        global running
        while running:
            data:bytes = pipe.read(CHUNK_SIZE)
            if len(data) == 0:
                running = False
            buffer.write(data)

    def deal_with_buffer(buffer:Buffer) -> None:
        global signals_queue, running
        proc_manager:ProcManager = ProcManager()
        last_signal:bytes = None
        signals_queue = []
        while running:
            try:
                parse_buffer(buffer, proc_manager, signals_queue)
                while len(signals_queue) != 0:
                    last_signal:bytes = signals_queue.pop(0)
                    proc_manager.send_signal(last_signal)
                proc_manager.tickle()
                sleep(REFRESH_RATE/1000)
            except CorruptedSignal:
                print(f"[DEBUG]: {signals_queue=} {last_signal=}", flush=True)
                raise

    def main() -> None:
        global pipe, running, wants_exit

        assert len(argv) == 3, "Wrong number of args"
        pipe = PipePair(*argv[1:], owns=False)
        pipe.start()
        assert IS_UNIX | IS_WINDOWS, "Invalid OS type"
        pipe.write(b"STARTED")

        buffer:bytes = Buffer()
        running = True
        wants_exit = False
        threada:Thread = Thread(target=read_pipe, args=(buffer,), daemon=True)
        threada.start()
        threadb:Thread = Thread(target=deal_with_buffer, args=(buffer,),
                                daemon=True)
        threadb.start()
        while running:
            try:
                sleep(END_REFRESH_RATE/1000)
            except KeyboardInterrupt:
                pass

    if __name__ == "__main__":
        if IS_UNIX:
            import termios
            # https://docs.python.org/3/library/termios.html#example
            default_stdin_state = termios.tcgetattr(stdin.fileno())
        exit_str:str = None
        main()
except BaseException:
    import os, traceback
    path = os.path.dirname(__file__)
    with open(path+"/error_traceback.txt", "w") as file:
        file.write(traceback.format_exc())
finally:
    if pipe is not None:
        pipe.close()