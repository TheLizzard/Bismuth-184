from __future__ import annotations
from time import sleep, perf_counter
from threading import Thread, RLock
from PIL import Image, ImageTk
from typing import Callable
import tkinter as tk
import signal
import os


try:
    from .sprites.creator import TkSpriteCache, SPRITES_REMAPPING
    from .terminal import Terminal, Event, kill_proc, close_all_ipcs
except ImportError:
    from sprites.creator import TkSpriteCache, SPRITES_REMAPPING
    from terminal import Terminal, Event, kill_proc, close_all_ipcs
from bettertk import BetterTk


BKWARGS:dict = dict(activeforeground="white", activebackground="grey", bd=0,
                    bg="black", relief="flat", fg="white", compound="left",
                    highlightthickness=0)
ICON:str = os.path.join(os.path.dirname(__file__), "sprites", "terminal.ico")
if not os.path.exists(ICON): ICON:str = None


def tk_wait_for_map(widget:tk.Misc) -> None:
    def inner() -> None:
        if widget.winfo_ismapped():
            widget.quit()
        else:
            widget.after(100, inner)
    widget.after(100, inner)
    widget.mainloop()


Cmd:type = tuple[str]
CmdPredicate:type = Callable[int,bool]
METHODS_TO_COPY_TERMINAL:tuple[str] = "bind", "running", "clear", "ipc", \
                                      "send_signal", "send_event", "sep_window"
METHODS_TO_COPY_TERMINAL_FRAME:tuple[str] = "queue", "queue_clear", "restart", \
                                            "_term_bind", "close"


class TerminalFrame(tk.Frame):
    def __init__(self, master:tk.Misc, **kwargs) -> TerminalFrame:
        self.curr_cmd = self._last_cmd = self.term = None
        self._to_call:list[Callable] = []
        self.started:bool = False
        self._ignore_exit_code:bool = False
        self._cmd_queue:list[tuple[Cmd,CmdPredicate]] = []
        self._state_lock:RLock = RLock()
        super().__init__(master, bg="black", bd=0, highlightthickness=0,
                         **kwargs)
        super().focus_set()

    def start(self) -> None:
        tk_wait_for_map(self)
        self.term:Terminal = Terminal(into=self)
        if self.term.resizable:
            super().bind("<Configure>", self._on_resize)

        for attr_name in METHODS_TO_COPY_TERMINAL:
            setattr(self, attr_name, getattr(self.term, attr_name))

        self._term_bind("finished", self._queue, threaded=True)
        self._term_bind("error", self._raise_error, threaded=False)
        self.started:bool = True
        self._handle_msg_loop()

    def _handle_msg_loop(self) -> None:
        self.ipc.call_queued_events()
        while self._to_call:
            self._to_call.pop(0)()
        if self.running():
            super().after(100, self._handle_msg_loop)

    def close(self) -> None:
        try:
            super().event_generate("<<Closing-Terminal>>")
        except tk.TclError:
            pass
        if self.term is not None:
            self.term.close()

    def _term_bind(self, event:str, handler:Callable, *, threaded:bool) -> None:
        self.term.bind(event, handler, threaded=threaded)

    def _on_resize(self, event:tk.Event) -> None:
        width, height = super().winfo_width(), super().winfo_height()
        self.term.resize(width=width, height=height)

    def queue(self, cmd:Cmd, condition:CmdPredicate=lambda*x:1) -> None:
        if not self.started:
            raise RuntimeError("First call .start() after grid managering us")
        assert callable(cmd) or isinstance(cmd, tuple|list), "TypeError"
        assert callable(condition), "TypeError"
        with self._state_lock:
            self._cmd_queue.append((cmd, condition))
            if self.curr_cmd is None:
                self._queue()

    def _queue(self, event:Event=None) -> None:
        with self._state_lock:
            self.curr_cmd:Cmd = None
            if len(self._cmd_queue) == 0: return None
            cmd, predicate = self._cmd_queue[0]
            if not self._ignore_exit_code:
                if (event is not None) and (not predicate(event.data)):
                    return None
            self._ignore_exit_code:bool = False
            self._cmd_queue.pop(0)
            self.curr_cmd = self._last_cmd = cmd
            if callable(cmd):
                self._to_call.append(cmd)
                self.queue()
            else:
                if (cmd[0] == "print!") and (len(cmd) > 1):
                    self.send_event("print", data=" ".join(cmd[1:]))
                    self._queue() # prints don't generate "finished" events
                else:
                    self.send_event("run", data=cmd)

    def restart(self) -> None:
        with self._state_lock:
            if self.curr_cmd is not None: return None
            if self._last_cmd is None: return None
            self._cmd_queue.insert(0, (self._last_cmd, lambda*x:1))
            self._queue()

    def _raise_error(self, event:Event) -> None:
        raise RuntimeError(f"Slave reported error: {event.data!r}")

    def queue_clear(self, *, stop_cur_proc:bool) -> None:
        with self._state_lock:
            self._cmd_queue.clear()
            if stop_cur_proc and (self.curr_cmd is not None):
                self._ignore_exit_code:bool = True
                kill_proc(self.send_signal, lambda: self.curr_cmd)


class TerminalTk(BetterTk):
    def __init__(self, master:tk.Misc=None, **kwargs) -> TerminalTk:
        super().__init__(master, **kwargs)
        if ICON is not None:
            super().iconphoto(False, ICON)
        super().title("TerminalTk")
        self.setup_buttons()
        self.term:TerminalFrame = TerminalFrame(self, width=815, height=460)
        self.term.pack(side="bottom", fill="both", expand=True)
        self.term.start()
        if self.term.sep_window:
            self.term.config(width=1, height=1)
            self.sep.destroy()
            super().resizable(False, False)

        attr_names:str = METHODS_TO_COPY_TERMINAL + \
                         METHODS_TO_COPY_TERMINAL_FRAME
        for attr_name in attr_names:
            setattr(self, attr_name, getattr(self.term, attr_name))
        super().protocol("WM_DELETE_WINDOW", self.destroy)

        self._term_bind("finished", self._finished_proc, threaded=False)
        self._term_bind("running", self._running_proc, threaded=False)
        self._die_with_slave()

    def _die_with_slave(self) -> None:
        if self.running():
            super().after(1, self.term._to_call.append, self._die_with_slave)
        else:
            self.destroy()

    def destroy(self) -> None:
        getattr(self, "close", lambda:None)()
        super().destroy()

    def setup_buttons(self) -> None:
        self.sprites:TkSpriteCache = TkSpriteCache(self, size=32,
                                                   compute_size=128)

        frame = tk.Frame(self, bg="black", bd=0, highlightthickness=0)
        frame.pack(side="top", fill="x")
        self.sep = tk.Frame(self, bg="grey", bd=0, highlightthickness=0,
                            width=1, height=3)
        self.sep.pack(side="top", fill="x")

        self.pause_button = tk.Button(frame, image=self.sprites["pause-green"],
                                      command=self._toggle_pause, **BKWARGS,
                                      width=70, text="Pause")
        self.close_button = tk.Button(frame, image=self.sprites["x-orange"],
                                      command=self._toggle_close, **BKWARGS,
                                      width=70, text="Close")
        self.kill_button = tk.Button(frame, image=self.sprites["io-red"],
                                     command=self._kill, **BKWARGS,
                                     width=70, text="Kill")
        self.settings_button = tk.Button(frame, command=self._settings,
                                         image=self.sprites["gear-grey"],
                                         **BKWARGS)
        self.pause_button.grid(row=1, column=1)
        self.close_button.grid(row=1, column=2)
        self.kill_button.grid(row=1, column=3)
        self.settings_button.grid(row=1, column=5)
        frame.grid_columnconfigure(4, weight=1)

    def _toggle_pause(self) -> None:
        if not self.running(): return None
        if self.pause_button.cget("text") == "Pause":
            sprite:ImageTk.PhotoImage = self.sprites["play-green"]
            self.pause_button.config(text="Play", image=sprite)
            self.send_event("pause")
        else:
            sprite:ImageTk.PhotoImage = self.sprites["pause-green"]
            self.pause_button.config(text="Pause", image=sprite)
            self.send_event("unpause")

    def _toggle_close(self) -> None:
        if not self.running(): return None
        if self.close_button.cget("text") == "Close":
            self.send_signal(signal.SIGTERM)
        else:
            self.restart()

    def _settings(self) -> None:
        pass

    def _kill(self) -> None:
        if not self.running(): return None
        self.send_signal(signal.SIGTERM)

    def _running_proc(self, event:Event) -> None:
        if not self.running(): return None
        self.kill_button.config(state="normal")
        self.pause_button.config(state="normal")
        self.close_button.config(text="Close", image=self.sprites["x-orange"])

    def _finished_proc(self, event:Event) -> None:
        if not self.running(): return None
        sprite:ImageTk.PhotoImage = self.sprites["pause-green"]
        self.pause_button.config(text="Pause", image=sprite)
        self.kill_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.close_button.config(image=self.sprites["restart"], text="Restart")


if __name__ == "__main__":
    term = TerminalTk()
    term.queue(("python3",))
    term.queue(("bash",), (0).__eq__)


if __name__ == "__main__a":
    root = tk.Tk()
    root.geometry("500x500")
    term_frame = TerminalFrame(root)
    term_frame.pack(fill="both", expand=True)
    term_frame.start()

    term_frame.queue(("python3",))
    term_frame.queue(("bash",), (0).__eq__)
