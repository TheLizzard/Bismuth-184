from __future__ import annotations
from threading import Thread
import tkinter as tk

try:
    from .terminaltk.sprites.creator import TkSpriteCache
    from .bettertk import BetterTk
    from .messagebox import tell
except ImportError:
    from terminaltk.sprites.creator import TkSpriteCache
    from bettertk import BetterTk
    from messagebox import tell


Success:type = bool

class TaskList(tk.Frame):
    """
    A list of tasks. Each task has a name and is associated with a
    function. The function must return a tuple of:
        * A boolean (true if it succeeded, false otherwise)
        * A string or none (extra info to be shown)
    The `display_text` option must be a `Callable[str,None]`

    Options:
        bg, background, fg, foreground, font, display_text
    Options only on __init__:
        continue_on_fail, wait_sprite, tick_sprite,
        cross_sprite, sprite_size

    Methods:
        add(name:str, func:Callable[tuple[bool,str|None]]) -> None
        start() -> None
    """

    __slots__ = "_sprites", "_fg", "_font", \
                "_spinner", "_correct", "_wrong", "_sprite_size", \
                "_continue_on_fail", "_display_text", \
                "_idx", "_widgets", "_tasks", \
                "_done_setup", "_waiting", "_success"

    def __init__(self, master:tk.Misc=None, **kwargs:dict) -> TaskList:
        self._done_setup:bool = False
        # Defaults
        self._display_text:Callable[str,None] = lambda text: None
        self._continue_on_fail:bool = False
        self._font:Font = "TkDefaultFont"
        self._fg:str = "white"
        self._spinner:str = "spinner6-black"
        self._correct:str = "tick-green"
        self._wrong:str = "x-red"
        self._sprite_size:int = 13
        # State variables
        self._idx:int = 0
        self._state:int = 0 # 0 => 1(running) => 2(done)
        self._waiting:bool = False
        self._success:Success = False
        self._widgets:list[tuple[tk.Misc,tk.Misc]] = []
        self._tasks:list[tuple[str,Callable]] = []
        # Create self and configure
        super().__init__(master, bg="black")
        self.config(**kwargs)
        self.grid_columnconfigure(1, weight=1)
        self._sprites:TkSpriteCache = TkSpriteCache(self,
                                                    size=self._sprite_size)
        self._done_setup:bool = True

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
            elif key == "sprite_size" and (not self._done_setup):
                self._sprite_size = kwargs.pop(key)
            elif key == "tick_sprite" and (not self._done_setup):
                self._correct = kwargs.pop(key)
            elif key == "cross_sprite" and (not self._done_setup):
                self._wrong = kwargs.pop(key)
            elif key == "wait_sprite" and (not self._done_setup):
                self._spinner = kwargs.pop(key)
            elif key == "continue_on_fail" and (not self._done_setup):
                self._continue_on_fail = kwargs.pop(key)
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

    def add(self, task_name:str, func:Callable[Success,str|None]) -> None:
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
        self._tasks.append((task_name, func))

    def start(self) -> None:
        if self._state != 0:
            raise RuntimeError("Already started")
        self._state:int = 1
        self._next()

    def _next(self) -> None:
        success, text = True, None

        def call() -> None:
            nonlocal success, text, _state
            result:object = func()
            if isinstance(result, bool):
                result:tuple[bool,str|None] = (result, None)
            success, text = result
            _state = 1 # Done

        def wait_done() -> None:
            nonlocal success, text, name, _state
            if _state == 0:
                self.after(100, wait_done)
                return None
            gif.stop()
            sprite:str = self._correct if success else self._wrong
            spinner.config(image=self._sprites[sprite])
            if text:
                spinner.config(command=lambda: self._display_text(text))
            if success or self._continue_on_fail:
                if self._idx < len(self._tasks):
                    self._next()
                else:
                    if self._waiting:
                        self.quit()
                    self._state:int = 2
                    self._success:Success = True
                    self.on_finished_success()
            else:
                self._state:int = 2
                self._success:Success = False
                self.on_finished_fail()

        idx, self._idx = self._idx, self._idx+1
        _state:int = 0 # Waiting
        name, func = self._tasks[idx]
        label, spinner = self._widgets[idx]
        gif = self._sprites.display_gif(self._spinner, 300,
                                        lambda img: spinner.config(image=img))
        gif.start()
        thread:Thread = Thread(target=call, daemon=True)
        thread.start()
        wait_done()

    def wait(self) -> Success:
        if self._state != 2:
            self._waiting:bool = True
            if self._state == 0:
                super().after(1, self.start)
            super().mainloop()
        return self._success

    def on_finished_success(self) -> None:
        pass

    def on_finished_fail(self) -> None:
        pass


class TaskListWindow(BetterTk):
    __slots__ = "tasklist", "autoclose", "_finished"

    def __init__(self, master:tk.Misc=None, *, autoclose:bool=False,
                 display_text:Callable[str,None]=None,
                 **kwargs:dict) -> TaskListWindow:
        def default_display_text(text:str) -> None:
            tell(self, title="Info", message=text, multiline=True, icon="info")

        self._finished:bool = False
        def _check_autoclose_loop() -> None:
            if not self._finished:
                self.after(100, _check_autoclose_loop)
                return None
            if self.autoclose:
                self.destroy()

        super().__init__(master)
        super().resizable(False, False)
        kwargs["display_text"] = display_text or default_display_text
        self.autoclose:bool = autoclose
        self.tasklist:TaskList = TaskList(self, **kwargs)
        self.tasklist.pack(fill="both", expand=True)
        self.tasklist.on_finished_success = self._maybe_autoclose
        _check_autoclose_loop()

    def _maybe_autoclose(self) -> None:
        self._finished:bool = True

    def add(self, task_name:str, func:Callable[Success,str|None]) -> None:
        self.tasklist.add(task_name, func)

    def start(self) -> None:
        self.tasklist.start()

    def wait(self) -> Success:
        return self.tasklist.wait()


if __name__ == "__main__":
    from time import sleep

    def task_sleep(sleep_time:float) -> Callable:
        def inner() -> tuple[Success,str|None]:
            sleep(sleep_time)
            return sleep_time > 1, str(sleep_time)
        return inner

    tl:TaskList = TaskListWindow(autoclose=True)
    tl.add("Sleep 2", task_sleep(2))
    tl.add("Sleep 1", task_sleep(1))
    tl.start()
    print(tl.wait())
