from __future__ import annotations
from threading import Thread, Lock
from PIL import ImageTk
from time import sleep
import tkinter as tk
import os

try:
    from .terminal import Terminal, encode_run, encode_print
    from .sprites.creator import init as create_sprites
    from ..bettertk import BetterTk
except ImportError:
    from terminal import Terminal, encode_run, encode_print
    from sprites.creator import init as create_sprites
    from bettertk import BetterTk


CHUNK_SIZE:int = 5*1024
MSG_QUEUE_RATE:int = 200 # sleep in milliseconds after parsing all new msgs
READ_MSG_RATE:int = 200  # sleep in milliseconds after consuming a msg
PING_SIGNAL:bytes = b"="
PONG_SIGNAL:bytes = b"#"
ERRORS:dict[bytes:str] = {
                           b"\x00\x01": "ERR_CMDS_QUEUE_NOT_EMPTY",
                           b"\x00\x02": "ERR_NO_LAST_CMD",
                           b"\x00\x03": "ERR_NO_PROC",
                         }
BKWARGS:dict = dict(activeforeground="white", activebackground="grey", bd=0,
                    bg="black", relief="flat", fg="white", compound="left",
                    highlightthickness=0)
ICON:str = os.path.join(os.path.dirname(__file__), "sprites", "terminal.ico")
if not os.path.exists(ICON): ICON:str = None

SPRITES_NEEDED:set[str] = {"pause", "play", "stop", "close", "restart",
                           "kill", "settings"}


def tk_wait_for_map(widget:tk.Misc) -> None:
    def inner() -> None:
        if widget.winfo_ismapped():
            widget.quit()
        else:
            widget.after(100, inner)
    widget.after(100, inner)
    widget.mainloop()


class Buffer:
    __slots__ = "under", "buffer", "msg_queue", "buffer_lock", "queue_lock", \
                "running", "msg_handler"

    def __init__(self, under:PipePair) -> Buffer:
        self.msg_handler:Function = None
        self.msg_queue:list[tuple] = []
        self.under:PipePair = under
        self.running:bool = True
        self.buffer:bytes = b""
        self.buffer_lock:Lock = Lock()
        self.queue_lock:Lock = Lock()
        Thread(target=self._read_under, daemon=True).start()
        Thread(target=self._write_queue, daemon=True).start()

    def _read_under(self) -> None:
        while True:
            new_data:bytes = self.under.read(CHUNK_SIZE)
            if len(new_data) == 0:
                self.running:bool = False
                return None
            with self.buffer_lock:
                self.buffer += new_data

    def _read(self, length:int) -> bytes:
        assert isinstance(length, int), "TypeError"
        assert length > 0, "ValueError"
        with self.buffer_lock:
            ret, self.buffer = self.buffer[:length], self.buffer[length:]
        return ret

    def write(self, data:bytes) -> None:
        assert isinstance(data, bytes), "TypeError"
        self.under.write(data)

    def send_force_print(self, data:str) -> None:
        self.write(encode_print(data))

    def _write_queue(self) -> None:
        while self.running:
            buff:bytes = b""
            while self.running:
                buff += self._read(1)
                if len(buff) == 0:
                    break
                elif buff == b"STARTED":
                    self.msg_queue_append(("STARTED",))
                    break
                elif buff == PING_SIGNAL:
                    self.msg_queue_append(("PING",))
                    break
                elif buff == PONG_SIGNAL:
                    self.msg_queue_append(("PONG",))
                    break
                elif buff == b"EXITCODE":
                    cmd_id:int = int.from_bytes(self._read(2), "big")
                    exit_code:int = int.from_bytes(self._read(4), "big")
                    self.msg_queue_append(("EXITCODE", cmd_id, exit_code))
                    break
                elif buff == b"ERR":
                    error:bytes = self._read(2)
                    self.msg_queue_append(("ERR", ERRORS[error]))
                    break
                elif buff == b"RUNNING":
                    cmd_id:int = int.from_bytes(self._read(2), "big")
                    self.msg_queue_append(("RUNNING", cmd_id))
                    break
                elif buff == b"OUTPUT":
                    cmd_id:int = int.from_bytes(self._read(2), "big")
                    output:str = self._read_char_star()[:-1].decode("utf-8")
                    self.msg_queue_append(("OUTPUT", cmd_id, output))
                    break
                elif len(buff) == 15:
                    raise RuntimeError("Buffer error")
                    # print(f"Unknown [too large] buffer: {buff+self.buffer!r}")
                    break
            sleep(MSG_QUEUE_RATE/1000)

    def _read_char_star(self) -> bytes:
        buffer:bytes = b""
        while True:
            buffer += self._read(1)
            if buffer[-1] == 0:
                return buffer

    def bind(self, msg_handler:Function) -> None:
        self.msg_handler:Function = msg_handler
        with self.queue_lock:
            while len(self.msg_queue) != 0:
                msg_handler(*self.msg_queue.pop())

    def msg_queue_append(self, args:tuple) -> None:
        if self.msg_handler is None:
            with self.queue_lock:
                self.msg_queue.append(args)
        else:
            self.msg_handler(*args)


class TerminalFrame(tk.Frame):
    def __init__(self, master:tk.Misc, **kwargs) -> TerminalFrame:
        self.started:bool = False
        super().__init__(master, bg="black", bd=0, highlightthickness=0,
                         **kwargs)
        super().focus_set()

    @property
    def running(self) -> bool:
        if not self.started:
            return False
        return self.terminal.running

    def start(self) -> None:
        tk_wait_for_map(self)
        self.terminal:Terminal = Terminal(into=self)
        self.buffer:Buffer = Buffer(self.terminal.pipe)
        if self.terminal.resizable:
            super().bind("<Configure>", self._on_resize)
        else:
            pass # ???
        self.started:bool = True

    def cancel_all(self) -> None:
        assert self.started, 'Call ".start()" first.'
        self.terminal.cancel_all()

    def close(self, signal:bytes=b"KILL") -> None:
        assert self.started, 'Call ".start()" first.'
        self.terminal.close(signal)

    def send_signal(self, signal:bytes) -> None:
        assert self.started, 'Call ".start()" first.'
        self.terminal.send_signal(signal)

    def _on_resize(self, event:tk.Event) -> None:
        if not self.started: return None
        width, height = super().winfo_width(), super().winfo_height()
        self.terminal.resize(width=width, height=height)

    def queue(self, cmd_id:int, command:tuple[str], to_print:str) -> None:
        assert self.started, 'Call ".start()" first.'
        self.buffer.write(encode_run(cmd_id, command, to_print))

    def destroy(self) -> None:
        if self.started:
            self.close()
        super().destroy()

    def bind(self, msg_handler:Function) -> None:
        self.buffer.bind(msg_handler)


class TerminalTk(BetterTk):
    __slots__ = "terminal", "pause_button", "close_button", "sprites", \
                "running_state", "chk_output", "closing_state", \
                "running_something", "_iqueue", "cmd_names", "waiting_pong"

    def __init__(self, master:tk.Misc=None, **kwargs) -> TerminalTk:
        self.running_state:tuple[int,int] = (None, None)
        self.chk_output:tuple[int,str] = (None, None)
        self.cmd_names:dict[int:str] = dict()
        self.running_something:bool = False
        self.waiting_pong:bool = False
        self._iqueue:list[tuple] = []
        super().__init__(master, **kwargs)
        if ICON is not None:
            super().iconphoto(True, ICON)
        super().title("TerminalTk")
        self.setup_buttons()
        self.terminal:TerminalFrame = TerminalFrame(self, width=815, height=460)
        self.terminal.pack(side="bottom", fill="both", expand=True)
        self.terminal.start()
        self.handle_msg_loop()

    @property
    def running(self) -> bool:
        return self.terminal.running

    def cancel_all(self) -> None:
        self._iqueue.clear()
        self.terminal.cancel_all()

    def setup_buttons(self) -> None:
        self.sprites:dict[str,ImageTk.PhotoImage] = dict()
        sprites = create_sprites(256>>1, 256>>3, 220, SPRITES_NEEDED)
        for name, image in sprites.items():
            self.sprites[name] = ImageTk.PhotoImage(image, master=self)

        frame = tk.Frame(self, bg="black", bd=0, highlightthickness=0)
        frame.pack(side="top", fill="x")
        sep = tk.Frame(self, bg="grey", bd=0, highlightthickness=0, width=1,
                       height=3)
        sep.pack(side="top", fill="x")

        self.pause_button = tk.Button(frame, image=self.sprites["pause"],
                                      command=self._toggle_pause, **BKWARGS,
                                      width=70, text="Pause")
        self.close_button = tk.Button(frame, image=self.sprites["close"],
                                      command=self._toggle_close, **BKWARGS,
                                      width=70, text="Close")
        self.kill_button = tk.Button(frame, image=self.sprites["kill"],
                                     command=self._kill, **BKWARGS,
                                     width=70, text="Kill")
        self.settings_button = tk.Button(frame, command=self._settings,
                                         image=self.sprites["settings"],
                                         **BKWARGS)
        self.pause_button.grid(row=1, column=1)
        self.close_button.grid(row=1, column=2)
        self.kill_button.grid(row=1, column=3)
        self.settings_button.grid(row=1, column=5)
        frame.grid_columnconfigure(4, weight=1)

    def queue(self, cmd_id:int, cmd:tuple[str], print_str:str) -> None:
        assert len(cmd) > 0, "ValueError"
        self.cmd_names[cmd_id] = cmd[0]
        self.terminal.queue(cmd_id, cmd, print_str)

    def iqueue(self, cmd_id, cmd, print_str, condition:Predicate[int]=None):
        assert len(cmd) > 0, "ValueError"
        self.cmd_names[cmd_id] = cmd[0]
        self._iqueue.append(((cmd_id, cmd, print_str), condition))
        if not self.running_something:
            self.iqueue_next()

    def iqueue_next(self) -> None:
        if len(self._iqueue) == 0:
            return None
        condition = self._iqueue[0][1]
        if (condition is None) or condition(self.running_state[1]):
            self.terminal.queue(*self._iqueue.pop(0)[0])
            self.running_something:bool = True

    def close(self, signal:bytes=b"KILL") -> None:
        self.terminal.close(signal)

    def send_signal(self, signal:bytes) -> None:
        self.terminal.send_signal(signal)

    def handle_msg_loop(self) -> None:
        while len(self.terminal.buffer.msg_queue) > 0:
            with self.terminal.buffer.queue_lock:
                self.handle_msg(*self.terminal.buffer.msg_queue.pop())
        super().after(READ_MSG_RATE, self.handle_msg_loop)

    def send_ping(self, *, wait:bool) -> None:
        assert wait, "No point in sending ping if you aren't going to wait."
        self.waiting_pong:bool = True
        self.send_signal(PING_SIGNAL)
        super().mainloop()

    def handle_msg(self, msg:str, *args) -> None:
        if msg == "STARTED":
            ...
        elif msg == "PING":
            self.terminal.send_signal(PONG_SIGNAL)
        elif msg == "PONG":
            if self.waiting_pong:
                super().quit()
        elif msg == "ERR":
            if args[0] == "ERR_CMDS_QUEUE_NOT_EMPTY":
                print("ERR_CMDS_QUEUE_NOT_EMPTY")
            elif args[0] == "ERR_NO_LAST_CMD":
                print("ERR_NO_LAST_CMD")
            elif args[0] == "ERR_NO_PROC":
                print("ERR_NO_PROC")
            else:
                print(f"No handler for ERR {args[0]!r}")
        elif msg == "RUNNING":
            assert len(args) == 1, "SanityCheck"
            self.running_something:bool = True
            self.running_state:tuple[int,int] = (args[0], None)
            name:str = self.cmd_names.get(args[0], "???")
            super().title(f"TerminalTk[{name}]")
            self._proc_running()
        elif msg == "EXITCODE":
            assert len(args) == 2, "SanityCheck"
            assert self.running_state[0] == args[0], "SanityCheck"
            self.running_state:tuple[int,int] = args
            self.running_something:bool = False
            #text:str = f" Process Ended [{args[1]}] ".center(80, "#")+"\n"
            #self.terminal.buffer.send_force_print(text)
            super().title("TerminalTk")
            self._no_proc_running()
            self.iqueue_next()
        elif msg == "OUTPUT":
            assert len(args) == 2, "SanityCheck"
            self.chk_output:tuple[int,int] = args
        else:
            print(f"No handler for {name} with {args=}")

    def _toggle_pause(self, *, send_signal:bool=True) -> None:
        if self.pause_button.cget("text") == "Pause":
            self.pause_button.config(text="Play", image=self.sprites["play"])
            if send_signal:
                self.terminal.send_signal(b"PAUSE")
        else:
            self.pause_button.config(text="Pause", image=self.sprites["pause"])
            if send_signal:
                self.terminal.send_signal(b"UNPAUSE")

    def _toggle_close(self) -> None:
        if self.close_button.cget("text") == "Close":
            self.terminal.send_signal(b"STOP")
        else:
            self.terminal.send_signal(b"RESTART")

    def _kill(self) -> None:
        self.terminal.send_signal(b"KILL")

    def _settings(self) -> None:
        pass

    def _proc_running(self) -> None:
        self.kill_button.config(state="normal")
        self.pause_button.config(state="normal")
        self.close_button.config(text="Close", image=self.sprites["close"])

    def _no_proc_running(self) -> None:
        if self.pause_button.cget("text") == "Play":
            self._toggle_pause(send_signal=False)
        self.kill_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.close_button.config(image=self.sprites["restart"], text="Restart")


if __name__ == "__main__":
    """
    root:tk.Tk = tk.Tk()
    root.geometry("815x460")
    root.config(bg="black")
    term:TerminalFrame = TerminalFrame(root)
    term.pack(fill="both", expand=True)
    term.start()
    term.queue(["bash"], " bash started ".center(80, "="))
    term.queue(["python3"], " python3 started ".center(80, "="))
    """
    term:TerminalTk = TerminalTk(className="TerminalTk")
    term.iqueue(0, ["bash"], " bash started ".center(80, "="))
    term.iqueue(1, ["python3"], " python3 started ".center(80, "="),
                condition=(0).__eq__)
