from __future__ import annotations
from traceback import format_exc
from threading import Thread
from typing import Callable
import tkinter as tk

try:
    from .terminaltk.sprites.creator import TkSpriteCache, GifDisplay
    from .bettertk import BetterTk
    from .messagebox import tell
except ImportError:
    from terminaltk.sprites.creator import TkSpriteCache, GifDisplay
    from bettertk import BetterTk
    from messagebox import tell


ESuccess:type = bool|None # Optional[bool]
Task:type = Callable[[], ESuccess|tuple[ESuccess,str]]
DisplayText:type = Callable[str,None]
OnDone:type = Callable[[int,ESuccess,str],None]

ESUCCESS_RANK:Callable[[ESuccess],int] = (False, None, True).index


def worst(*esuccesses:ESuccess) -> ESuccess:
    return min(esuccesses, key=ESUCCESS_RANK)


class Result:
    __slots__ = "done", "esuccess", "text"

    def __init__(self) -> None:
        self.done:bool = False
        self.esuccess:ESuccess = False
        self.text:str|None = None

    def __repr__(self) -> str:
        esuccess, text = self.esuccess, self.text
        if self.done:
            return f"Result(done=True, self.{esuccess=}, self.{text=!r})"
        else:
            return f"Result(done=False)"


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

    A task may be given a `cleanup`, which is a `Task` as well. Every
    cleanup of a task that was started is called once the list is done,
    in reverse, whether the list succeeded or failed. One that doesn't
    return true marks its own task's row.

    Methods:
        add(name:str, func:Task, *, threaded:bool=True, cleanup:Task=None)
        start()

    Properties:
        idx:int # 1-indexed index of the task being run or cleaned up.
                # Only valid from inside a task's callback.
    """

    __slots__ = "_sprites", "_fg", "_font", \
                "_spinner", "_correct", "_wrong", "_sprite_size", \
                "_continue_on_fail", "_display_text", \
                "_idx", "_widgets", "_tasks", "_results", \
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
        self._tasks:list[tuple[str,Task,bool,Task|None]] = []
        self._results:list[tuple[ESuccess,str]] = []
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

    def add(self, task_name:str, func:Task, *, threaded:bool=True,
            cleanup:Task=None) -> None:
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
        self._tasks.append((task_name, func, threaded, cleanup))
        self._results.append((True, ""))

    def _mark(self, idx:int, esuccess:ESuccess, text:str) -> None:
        row_esuccess, row_text = self._results[idx]
        row_esuccess:ESuccess = worst(row_esuccess, esuccess)
        if text:
            row_text += "\n\n"*bool(row_text) + text.strip("\n")
        self._results[idx] = (row_esuccess, row_text)
        self.esuccess:ESuccess = worst(self.esuccess, esuccess)
        if row_esuccess:
            sprite:str = self._correct
        elif row_esuccess is None:
            sprite:str = self._zero
        else:
            sprite:str = self._wrong
        _, spinner = self._widgets[idx]
        spinner.config(image=self._sprites[sprite])
        if row_text:
            spinner.config(command=lambda: self._display_text(row_text))

    def _call(self, func:Task, result:Result) -> None:
        try:
            returned:tuple[ESuccess,str]|ESuccess = func()
            if isinstance(returned, ESuccess):
                returned:tuple[ESuccess,str] = returned, ""
            result.esuccess, result.text = returned
        except Exception:
            result.text = format_exc()
        except BaseException:
            result.text = format_exc()
            raise
        finally:
            result.done = True

    def _run(self, idx:int, func:Task, threaded:bool, on_done:OnDone) -> None:
        _, spinner = self._widgets[idx]
        gif:GifDisplay = self._sprites.display_gif(self._spinner, 300,
                                        lambda img: spinner.config(image=img))
        gif.start()
        result:Result = Result()
        thread:Thread = Thread(target=self._call, args=(func,result),
                               daemon=True)
        getattr(thread, "start" if threaded else "run")()
        self._wait(idx, gif, result, on_done)

    def _wait(self, idx:int, gif:GifDisplay, result:Result,
              on_done:OnDone) -> None:
        if not result.done:
            self.after(100, self._wait, idx, gif, result, on_done)
            return None
        gif.stop()
        on_done(idx, result.esuccess, result.text)

    def start(self) -> None:
        assert self._state == 0, "RuntimeError"
        self._state:int = 1
        self._next()

    def _next(self) -> None:
        assert self._state == 1, "RuntimeError"
        idx, self._idx = self._idx, self._idx+1
        _, func, threaded, _ = self._tasks[idx]
        self._run(idx, func, threaded, self._task_done)

    def _task_done(self, idx:int, esuccess:ESuccess, text:str) -> None:
        self._mark(idx, esuccess, text)
        # Check if we should continue or not
        _continue:bool = ((esuccess in (True,None)) or \
                          self._continue_on_fail) and \
                         (self._idx < len(self._tasks))
        if _continue:
            self._next()
        else:
            self._cleanup(self._idx)

    def _cleanup(self, end:int) -> None:
        has_cleanup:Callable[[int],object] = lambda i: self._tasks[i][3]
        idx:int|None = next(filter(has_cleanup, reversed(range(end))), None)
        if idx is None:
            if self._waiting: self.quit()
            self._state:int = 2
            self.on_finished()
            return None
        self._idx:int = idx + 1
        *_, threaded, cleanup = self._tasks[idx]
        self._run(idx, cleanup, threaded, self._cleanup_done)

    def _cleanup_done(self, idx:int, esuccess:ESuccess, text:str) -> None:
        self._mark(idx, esuccess, text)
        super().after(100, self._cleanup, idx)

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

    def add(self, task_name:str, func:Task, *, threaded:bool=True,
            cleanup:Task=None) -> None:
        assert self.tasklist._state == 0, "RuntimeError"
        self.tasklist.add(task_name, func, threaded=threaded, cleanup=cleanup)

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

    def task_sleep(sleep_time:float, cleanup:bool=False) -> Task:
        def inner() -> ESuccess|tuple[ESuccess,str]:
            print(f"Starting {tl.idx-1} {cleanup=}")
            sleep(sleep_time)
            return [False, None, True][sleep_time], str(sleep_time)
        return inner

    tl:TaskList = TaskListWindow(autoclose=True)
    tl.add("Sleep 2", task_sleep(2), cleanup=task_sleep(1, True))
    tl.add("Sleep 2", task_sleep(2), cleanup=task_sleep(2, True))
    tl.add("Sleep 1", task_sleep(0), cleanup=task_sleep(1, True))
    print(tl.wait())
