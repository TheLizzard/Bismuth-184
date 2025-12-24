from __future__ import annotations
from threading import Thread
from typing import Callable
import tkinter as tk

try:
    from .terminaltk.sprites.creator import TkSpriteCache
    from .bettertk import BetterTk
    from .messagebox import tell
except ImportError:
    from terminaltk.sprites.creator import TkSpriteCache
    from bettertk import BetterTk
    from messagebox import tell


ESuccess:type = bool|None # Optional[bool]
Task:type = Callable[[], ESuccess|tuple[ESuccess,str]]
DisplayText:type = Callable[str,None]

class TaskList(tk.Frame):
    """
    A list of tasks. Each task has a name and is associated with a
    function. The function must return a tuple of:
        * A boolean (true if it succeeded, false otherwise)
        * A string or none (extra info to be shown)
    The `display_text` option must be a `DisplayText`

    Options:
        bg, background, fg, foreground, font, display_text
    Options only on __init__:
        wait_sprite, tick_sprite, warn_sprite, cross_sprite, sprite_size
        continue_on_fail grab_set

    Methods:
        add(name:str, func:Task)
        start()

    Properties:
        idx:int # The index of the next task to be run
    """

    __slots__ = "_sprites", "_fg", "_font", \
                "_spinner", "_correct", "_wrong", "_sprite_size", \
                "_continue_on_fail", "_display_text", \
                "_idx", "_widgets", "_tasks", \
                "_done_setup", "_waiting", "esuccess"

    def __init__(self, master:tk.Misc=None, **kwargs:dict) -> None:
        self._done_setup:bool = False
        # Defaults
        self._display_text:DisplayText = lambda text: None
        self._continue_on_fail:bool = False
        self._font:Font = "TkDefaultFont"
        self._fg:str = "white"
        self._spinner:str = "spinner6-black"
        self._correct:str = "tick-green"
        self._zero:str = "warning"
        self._wrong:str = "x-red"
        self._sprite_size:int = 13
        # State variables
        self._idx:int = 0
        self._state:int = 0 # 0(settingup) => 1(running) => 2(done)
        self._waiting:bool = False
        self.esuccess:ESuccess = True
        self._widgets:list[tuple[tk.Misc,tk.Misc]] = []
        self._tasks:list[tuple[str,Task,bool]] = []
        # Create self and configure
        super().__init__(master, bg="black")
        self.config(**{"grab_set":True, **kwargs})
        self.grid_columnconfigure(1, weight=1)
        self._sprites:TkSpriteCache = TkSpriteCache(self,
                                                    size=self._sprite_size)
        self._done_setup:bool = True

    @property
    def idx(self) -> int:
        return self._idx

    def _toplevel(self) -> tk.Toplevel|tk.Tk:
        widget:tk.Misc = self
        while not isinstance(widget, tk.Tk|tk.Toplevel|BetterTk):
            widget:tk.Misc = widget.master
        return widget

    def config(self, **kwargs:dict) -> None:
        for key, value in list(kwargs.items()):
            if key in ("fg", "foreground"):
                self._fg:str = kwargs.pop(key)
                self._redraw()
            elif key in ("bg", "background"):
                super().config(bg=kwargs.pop(key))
                self._redraw()
            elif key == "font":
                self._font:Font = kwargs.pop(key)
                self._redraw()
            elif key == "display_text":
                self._display_text = kwargs.pop(key)
            elif (key == "sprite_size") and (not self._done_setup):
                self._sprite_size = kwargs.pop(key)
            elif (key == "tick_sprite") and (not self._done_setup):
                self._correct = kwargs.pop(key)
            elif (key == "warn_sprite") and (not self._done_setup):
                self._zero = kwargs.pop(key)
            elif (key == "cross_sprite") and (not self._done_setup):
                self._wrong = kwargs.pop(key)
            elif (key == "wait_sprite") and (not self._done_setup):
                self._spinner = kwargs.pop(key)
            elif (key == "continue_on_fail") and (not self._done_setup):
                self._continue_on_fail = kwargs.pop(key)
            elif (key == "grab_set") and (not self._done_setup):
                if not kwargs.pop("grab_set"): continue
                try:
                    self._toplevel().grab_set()
                except tk.TclError:
                    pass
        if kwargs:
            super().config(kwargs)

    configure = config

    def cget(self, key:str) -> object:
        if key in ("fg", "foreground"):
            return self._fg
        if key in ("bg", "background"):
            return super().cget("bg")
        if key == "font":
            return self._font
        if key == "sprite_size":
            return self._sprite_size
        if key == "tick_sprite":
            return self._correct
        if key == "warn_sprite":
            return self._zero
        if key == "cross_sprite":
            return self._wrong
        if key == "wait_sprite":
            return self._spinner
        if key == "continue_on_fail":
            return self._continue_on_fail
        if key == "display_text":
            return self._display_text
        return super().cget(key)

    def _redraw(self) -> None:
        pass # TODO

    def add(self, task_name:str, func:Task, *, threaded:bool=True) -> None:
        assert self._state == 0, "RuntimeError"
        idx:int = len(self._widgets)
        bg:str = self.cget("bg")
        sep:dict = dict(bd=0, highlightthickness=0, width=1, height=1,
                        bg=self._fg)
        # Top separator
        if not idx:
            tk.Canvas(self, **sep).grid(row=2+2*idx, column=1, columnspan=3,
                                        sticky="ew")
        # Create widgets
        label:tk.Label = tk.Label(self, fg=self._fg, bg=bg, text=task_name,
                                  font=self._font)
        label.grid(row=3+2*idx, column=1, sticky="w")
        spinner:tk.Button = tk.Button(self, bd=0, highlightthickness=0, bg=bg,
                                      relief="flat", activebackground=bg)
        spinner.grid(row=3+2*idx, column=3, sticky="ew")
        # Separators
        for col in (0, 2, 4):
            tk.Canvas(self, **sep).grid(row=3+2*idx, column=col, rowspan=1,
                                        sticky="ns")
        tk.Canvas(self, **sep).grid(row=4+2*idx, column=1, columnspan=3,
                                    sticky="ew")
        # Update state
        self._widgets.append((label, spinner))
        self._tasks.append((task_name, func, threaded))

    def start(self) -> None:
        assert self._state == 0, "RuntimeError"
        self._state:int = 1
        self._next()

    def _next(self) -> None:
        assert self._state == 1, "RuntimeError"
        esuccess, text = True, None

        def call() -> None:
            nonlocal esuccess, text, _state
            result:object = func()
            if isinstance(result, ESuccess):
                result:tuple[ESuccess,str] = (result, "")
            esuccess, text = result
            _state = 1 # Done

        def wait_done() -> None:
            nonlocal esuccess, text, name, _state
            if _state == 0:
                self.after(100, wait_done)
                return None
            # Update spinner
            gif.stop()
            if esuccess:
                sprite:str = self._correct
            elif esuccess is None:
                sprite:str = self._zero
            else:
                sprite:str = self._wrong
            spinner.config(image=self._sprites[sprite])
            if text:
                spinner.config(command=lambda: self._display_text(text))
            # Update self.esuccess
            if self.esuccess:
                self.esuccess:ESuccess = esuccess
            # Check if we should continue or not
            _continue:bool = ((esuccess in (True,None)) or \
                              self._continue_on_fail) and \
                             (self._idx < len(self._tasks))
            if _continue:
                self._next()
            else:
                if self._waiting: self.quit()
                self._state:int = 2
                self.on_finished()

        idx, self._idx = self._idx, self._idx+1
        _state:int = 0 # Waiting
        name, func, threaded = self._tasks[idx]
        label, spinner = self._widgets[idx]
        gif = self._sprites.display_gif(self._spinner, 300,
                                        lambda img: spinner.config(image=img))
        gif.start()
        thread:Thread = Thread(target=call, daemon=True)
        (thread.start if threaded else thread.run)()
        wait_done()

    def destroy(self) -> None:
        super().destroy()
        if self._waiting:
            super()._root().quit()

    def wait(self) -> ESuccess:
        if self._state != 2:
            assert not self._waiting, "Threaded tkinter is not allowed"
            self._waiting:bool = True
            if self._state == 0:
                super().after(1, self.start)
            super().mainloop()
            self._waiting:bool = False
        return self.esuccess

    def on_finished(self) -> None:
        pass


class TaskListWindow(BetterTk):
    __slots__ = "tasklist", "autoclose"

    def __init__(self, master:tk.Misc=None, *, autoclose:bool=False,
                 display_text:DisplayText=None, **kwargs:dict) -> None:
        def default_display_text(text:str) -> None:
            tell(self, title="Info", message=text, multiline=True, icon="info")

        super().__init__(master)
        super().resizable(False, False)
        kwargs["display_text"] = display_text or default_display_text
        self.autoclose:bool = autoclose
        self.tasklist:TaskList = TaskList(self, **kwargs)
        self.tasklist.pack(fill="both", expand=True)
        self.tasklist.on_finished = self._maybe_autoclose
        super().protocol("WM_DELETE_WINDOW", self._maybe_close)

    def _maybe_close(self) -> None:
        # Deny closing while tasks are running
        if self.tasklist._state == 1: return None
        super().destroy()

    def _maybe_autoclose(self) -> None:
        assert self.tasklist._state == 2, "RuntimeError"
        # If success is True, and autoclose and finished, close the window
        if self.autoclose and self.tasklist.esuccess:
            super().destroy()

    def add(self, task_name:str, func:Task, *, threaded:bool=True) -> None:
        assert self.tasklist._state == 0, "RuntimeError"
        self.tasklist.add(task_name, func, threaded=threaded)

    def start(self) -> None:
        assert self.tasklist._state == 0, "RuntimeError"
        self.tasklist.start()

    def wait(self) -> ESuccess:
        return self.tasklist.wait()

    @property
    def idx(self) -> int:
        return self.tasklist.idx


if __name__ == "__main__":
    from time import sleep

    def task_sleep(sleep_time:float, tkinter:bool) -> Task:
        def inner() -> ESuccess|tuple[ESuccess,str]:
            print(f"Starting {tl.idx-1}")
            if tkinter:
                tl.after(int(sleep_time*1000), tl.quit)
                tl.mainloop()
            else:
                sleep(sleep_time)
            print(f"Ending {tl.idx-1}")
            return True if sleep_time > 1 else None, str(sleep_time)
        return inner

    master:tk.Tk = tk.Tk()
    tk.Button(master, text="Button", command=lambda:print("Hi\r")).pack()
    tl:TaskList = TaskListWindow(master, autoclose=True)
    tl.add("Sleep 2", task_sleep(2, True), threaded=False)
    tl.add("Sleep 2", task_sleep(2, False))
    tl.add("Sleep 1", task_sleep(1, False))
    print(tl.wait())
