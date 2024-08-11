from __future__ import annotations
from time import sleep, perf_counter
from PIL import Image, ImageTk
from threading import Thread
from typing import Callable
import tkinter as tk
import signal
import os


try:
    from .sprites.creator import init as create_sprites
    from .terminal import Terminal, Event, kill_proc
except ImportError:
    from sprites.creator import init as create_sprites
    from terminal import Terminal, Event, kill_proc
from bettertk import BetterTk


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


Cmd:type = tuple[str]
CmdPredicate:type = Callable[int,bool]
METHODS_TO_COPY_TERMINAL:tuple[str] = "close", "bind", "running", "clear", \
                                      "send_signal", "ipc", "send_event"
METHODS_TO_COPY_TERMINAL_FRAME:tuple[str] = "queue", "queue_clear", "restart", \
                                            "_term_bind"


class TerminalFrame(tk.Frame):
    def __init__(self, master:tk.Misc, **kwargs) -> TerminalFrame:
        self.curr_cmd = self._last_cmd = None
        self.started:bool = False
        self._cmd_queue:list[tuple[Cmd,CmdPredicate]] = []
        super().__init__(master, bg="black", bd=0, highlightthickness=0,
                         **kwargs)
        super().focus_set()

    def start(self, *, use_signal_catcher:bool=True) -> None:
        tk_wait_for_map(self)
        self.term:Terminal = Terminal(into=self)
        if self.term.resizable:
            super().bind("<Configure>", self._on_resize)

        for attr_name in METHODS_TO_COPY_TERMINAL:
            setattr(self, attr_name, getattr(self.term, attr_name))

        self._term_bind("finished", self._queue, threaded=True)
        self._term_bind("error", self._raise_error, threaded=True)
        self.started:bool = True

        # As python signals can only happen between bytecodes, we need
        # to constantly run some python code.
        # This assumes that tkinter is in the main thread or the main thread
        # if taking up CPU resources.
        def signal_catcher() -> None:
            self.after(100, signal_catcher)
        if use_signal_catcher:
            self.after(100, signal_catcher)

    def _term_bind(self, event:str, handler:Callable, *, threaded:bool) -> None:
        self.term.bind(event, handler, threaded=threaded)

    def _on_resize(self, event:tk.Event) -> None:
        self.term.resize(width=super().winfo_width(),
                         height=super().winfo_height())

    def queue(self, cmd:Cmd, condition:CmdPredicate=lambda*x:1) -> None:
        if not self.started:
            raise RuntimeError("First call .start() after grid managering us")
        assert isinstance(cmd, tuple|list), "TypeError"
        self._cmd_queue.append((cmd, condition))
        if self.curr_cmd is None:
            self._queue()

    def _queue(self, event:Event=None) -> None:
        self.curr_cmd:Cmd = None
        if len(self._cmd_queue) == 0:
            return None
        cmd, predicate = self._cmd_queue[0]
        if event is not None:
            if not predicate(event.data):
                return None
        self._cmd_queue.pop(0)
        self.curr_cmd = self._last_cmd = cmd
        self.send_event("run", data=cmd)

    def restart(self) -> None:
        if self.curr_cmd is not None:
            return None
        if self._last_cmd is None:
            return None
        self._cmd_queue.insert(0, (self._last_cmd, lambda*x:1))
        self._queue()

    def _raise_error(self, event:Event) -> None:
        raise RuntimeError(repr(event.data))

    def queue_clear(self, stop_cur_proc:bool) -> None:
        self._cmd_queue.clear()
        if stop_cur_proc and (self.curr_cmd is not None):
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
        self.term.start(use_signal_catcher=False)

        attr_names:str = METHODS_TO_COPY_TERMINAL + \
                         METHODS_TO_COPY_TERMINAL_FRAME
        for attr_name in attr_names:
            setattr(self, attr_name, getattr(self.term, attr_name))
        super().protocol("WM_DELETE_WINDOW", self.destroy)

        self._term_bind("finished", self._finished_proc, threaded=False)
        self._term_bind("running", self._running_proc, threaded=False)
        self._handle_msg_loop()

    def destroy(self) -> None:
        self.close()
        super().destroy()

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

    def _toggle_pause(self) -> None:
        if self.pause_button.cget("text") == "Pause":
            self.pause_button.config(text="Play", image=self.sprites["play"])
            self.send_event("pause")
        else:
            self.pause_button.config(text="Pause", image=self.sprites["pause"])
            self.send_event("unpause")

    def _toggle_close(self) -> None:
        if self.close_button.cget("text") == "Close":
            self.send_signal(signal.SIGTERM)
        else:
            self.restart()

    def _settings(self) -> None:
        pass

    def _kill(self) -> None:
        self.send_signal(signal.SIGABRT)

    def _running_proc(self, event:Event) -> None:
        self.kill_button.config(state="normal")
        self.pause_button.config(state="normal")
        self.close_button.config(text="Close", image=self.sprites["close"])

    def _finished_proc(self, event:Event) -> None:
        self.pause_button.config(text="Pause", image=self.sprites["pause"])
        self.kill_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.close_button.config(image=self.sprites["restart"], text="Restart")

    def _handle_msg_loop(self) -> None:
        self.ipc.call_queued_events()
        self.after(100, self._handle_msg_loop)


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