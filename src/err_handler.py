from __future__ import annotations
from traceback import format_exception, format_exc
from subprocess import Popen, DEVNULL
from functools import partial
from threading import Thread
from sys import executable
import tkinter as tk
import sys
import os


if os.name == "posix":
    DETACH_PROC_KWARGS:dict = dict(start_new_session=True)
elif os.name == "nt":
    from subprocess import DETACHED_PROCESS
    DETACH_PROC_KWARGS:dict = dict(creation_flags=DETACHED_PROCESS)
else:
    DETACH_PROC_KWARGS:dict = dict()


THIS:str = os.path.abspath(__file__)
PATH:str = os.path.dirname(THIS)
ERR_PATH_FORMAT:str = os.path.join(PATH, "error_logs", "error.{n}.txt")

def get_err_path() -> str:
    os.makedirs(os.path.dirname(ERR_PATH_FORMAT), exist_ok=True)
    i:int = 0
    while True:
        err_path:str = ERR_PATH_FORMAT.format(n=str(i).zfill(4))
        if not os.path.exists(err_path):
            return err_path
        try:
            with open(err_path, "rb") as file:
                if file.read(1) == b"":
                    return err_path
        except:
            pass
        if i == 9999:
            raise RuntimeError("No file could be accessed to save error")
        i += 1


HasErrorer:type = bool
BUTTON_KWARGS:dict = dict(activeforeground="white", activebackground="grey",
                          bg="black", fg="white", highlightthickness=0,
                          takefocus=False)


def get_full_traceback(err:Exception) -> Traceback:
    """
    Returns the full traceback of `err` from the very start of the program.
    """
    class FakeTraceback:
        def __init__(self, frame, lasti, lineno, next):
            self.tb_lineno = lineno
            self.tb_frame = frame
            self.tb_lasti = lasti
            self.tb_next = next
        def reverse(self, new_last):
            self, _next = new_last, self
            while _next:
                _next.tb_next, _next, self = self, _next.tb_next, _next
            return self

    raw_traceback = err.__traceback__
    err_traceback = None
    while raw_traceback:
        err_traceback = FakeTraceback(raw_traceback.tb_frame,
                                      raw_traceback.tb_lasti,
                                      raw_traceback.tb_lineno, err_traceback)
        raw_traceback = raw_traceback.tb_next

    raw_traceback = sys._getframe().f_back.f_back
    main_traceback = err_traceback.reverse(None)
    while raw_traceback:
        main_traceback = FakeTraceback(raw_traceback, raw_traceback.f_lasti,
                                       raw_traceback.f_lineno, main_traceback)
        raw_traceback = raw_traceback.f_back

    return main_traceback

def report_full_exception(widget:tk.Misc, err:BaseException) -> None:
    assert isinstance(widget, tk.Misc), "widget must be a tk.Misc"
    assert isinstance(err, BaseException), "err must be a BaseException"
    root:tk.Tk = widget._root()
    root.report_callback_exception(type(err), err, get_full_traceback(err))
tk.Misc.report_full_exception = report_full_exception


class ErrorCatcher:
    __slots__ = "inside", "handler"

    def __init__(self, handler:Callable[None]) -> ErrorCatcher:
        self.handler:Callable[None] = handler
        self.inside:bool = False

    def __enter__(self) -> ErrorCatcher:
        assert not self.inside, "Already inside this ErrorCatcher"
        self.inside:bool = True
        return self

    def __exit__(self, exc:type, val:Exception, tb:object) -> bool:
        if exc:
            return self.handler(exc, val, tb)
        else:
            return False


class RunManager:
    __slots__ = "funcs", "started_exec"

    def __init__(self) -> None:
        tk.Tk.report_callback_exception = lambda root, *args: \
                                      self.report_exc(*args, critical=False)
        self.funcs:list[tuple[Callable,bool]] = []
        self.started_exec:bool = False

    def __new__(Class:type, *args:tuple, **kwargs:dict) -> RunManager:
        singleton:Class|None = getattr(Class, "singleton", None)
        if singleton is None:
            Class.singleton:Class = super().__new__(Class, *args, **kwargs)
            _init = getattr(Class, "_init", None)
            if _init is not None:
                _init(Class.singleton, *args, **kwargs)
        return Class.singleton
    _init, __init__ = __init__, lambda self: None

    def error_chatcher(self, critical:bool=True, *,
                       ign_err:bool=True) -> ErrorCatcher:
        def inner(exc:type, val:Exception, tb:object) -> None:
            self.report_exc(exc, val, tb, critical=critical,
                            msg="Exception caught by ErrorCatcher")
            return ign_err
        return ErrorCatcher(inner)

    def register(self, func:Callable, *, exit_on_error:bool=False) -> None:
        assert not self.started_exec, "Can't register any functions after " \
                                      "calling .exec()"
        self.funcs.append((func, exit_on_error))

    def exec(self) -> None:
        def _format_args(args:object) -> tuple[object]:
            if args is None: return ()
            return tuple(args) if isinstance(args, tuple|list) else (args,)

        assert not self.started_exec, "You already called .exec()"
        self.started_exec:bool = True
        args:object = ()
        for func, exit_on_error in self.funcs:
            try:
                args:object = func(*_format_args(args))
            except BaseException as error:
                if isinstance(error, SystemExit):
                    return None
                self.report_exc(type(error), error, get_full_traceback(error),
                                critical=exit_on_error)
                if not exit_on_error:
                    continue
                return None

    def report_exc(self, *exc:tuple, critical:bool, msg:str="") -> None:
        assert len(exc) == 3, "exc must be a tuple of (type, err, tb)"
        if critical:
            pre_string:str = " Critical error ".center(80, "=")
        else:
            pre_string:str = " Non critical error ".center(80, "=")
        try:
            tb:str = "".join(format_exception(*exc)).rstrip("\n")
        except BaseException:
            tb:str = "Couldn't generate traceback in " \
                     "err_handler.py@RunManager.report_exc"
        string:str = pre_string + "\n" + tb + "\n"
        if msg:
            string += msg + "\n"
        string += "="*80
        string:str = string.replace("\x00", "\\x00")
        proc:Popen = Popen([executable, THIS], shell=False, stdin=DEVNULL,
                           stdout=DEVNULL, stderr=DEVNULL, **DETACH_PROC_KWARGS,
                           env=os.environ|{"_display_err":string})
        Thread(target=proc.wait, name="subproc-reaper", daemon=True).start()


# Main display dispatcher
def _display(string:str) -> None:
    try_n:int = 0
    while True:
        try:
            if try_n == 0:
                _display0(string)
            elif try_n == 1:
                _display1(string)
            elif try_n == 2:
                _display2(string)
            else:
                pass # No display, ignore the error
            break
        except Exception as error:
            print(error)
            try_n += 1

# Different displays
def _display0(string:str) -> None:
    from bettertk import BetterTk, make_scrolled

    root:BetterTk = BetterTk(className="Error")
    frame, text = _setup_window(root, string)
    make_scrolled(frame, text, vscroll=True, hscroll=True,
                  lines_numbers=True)
    root.mainloop()


def _display1(string:str) -> None:
    root:tk.Tk = tk.Tk(className="Error")
    frame, text = _setup_window(root, string)
    text.pack(fill="both", expand=True)
    root.mainloop()


def _display2(string:str) -> None:
    filepath:str = get_err_path()
    with open(filepath, "w") as file:
        file.write(string)


# Helpers:
def _setup_window(root, string:str) -> tuple[tk.Frame,tk.Text]:
    def close() -> None:
        root.destroy()
    def write_to_file() -> None:
        nonlocal string
        try:
            string = text.get("1.0", "end")
        except Exception as error:
            new_err:str = "Error when getting text from tkinter to save"
            string += "\n\n" + " Non critical error ".center(80, "=") + "\n"
            string += new_err + "\n" + "-"*len(new_err) + "\n" + \
                      format_exc().rstrip("\n") + "\n" + "="*80 + "\n"
        _display2(string)
        button.destroy()

    root.title("Error")
    root.protocol("WM_DELETE_WINDOW", close)
    if _try_set_iconphoto(root):
        string += "\nAlso `root.iconphoto` on error window failed :/"

    frame:tk.Frame = tk.Frame(root, bg="black")
    frame.pack(fill="both", expand=True)
    button:tk.Button = tk.Button(root, text="Write error to file",
                                 command=write_to_file, **BUTTON_KWARGS)
    button.pack(fill="x")

    text:tk.Text = tk.Text(frame, bg="black", fg="white", width=80,
                           height=20, bd=0, highlightthickness=0,
                           insertbackground="white", wrap="none")
    text.insert("end", string)
    return frame, text

def _try_set_iconphoto(root:tk.Tk|BetterTk) -> HasErrorer:
    try:
        from bettertk.terminaltk.sprites.creator import SpriteCache
        cache:SpriteCache = SpriteCache(size=128)
        try:
            sprite:Image.Image = cache["error"]
        except KeyError:
            sprite:Image.Image = cache["x-red"]
        root.iconphoto(False, sprite)
        return False
    except:
        pass
    try:
        from PIL import Image, ImageTk
        from io import BytesIO
        img:Image.Image = Image.open("sprites/error_icon.png")
        try:
            root.iconphoto(False, img)
        except:
            root.tk_img_895644 = ImageTk.PhotoImage(img, master=root)
            root.iconphoto(False, root.tk_img_895644)
        return False
    except:
        pass
    return True


if __name__ == "__main__":
    string:str|None = os.environ.get("_display_err", None)
    if string:
        _display(string)
        sys.exit(0)

    def start() -> int:
        root = tk.Tk()
        root.after(2000, lambda: 1/0) # Raise error
        root.bind("<Delete>", lambda e: 1/0)
        return 100

    def init(arg:int) -> tuple[str,bool]:
        assert arg == 100
        return ("123", False)

    def run(arg1:str, arg2:bool) -> None:
        # Can't run this test in python versions between (3.13.0, 3.13.7]
        #   because of: https://github.com/python/cpython/issues/132744
        # This will have to wait until Debian Trixie gets python3>=3.13.8
        def stack_overflow(idx:int=0) -> None:
            if idx == 1000:
                raise RecursionError()
            if idx < 0:
                raise RuntimeError()
            try:
                stack_overflow(idx+1)
            except RecursionError:
                stack_overflow(-1)
        stack_overflow() # Raise error

    import sys
    sys.setrecursionlimit(45)
    manager:RunManager = RunManager()
    manager.register(start, exit_on_error=True)
    manager.register(init, exit_on_error=False)
    manager.register(run, exit_on_error=False)
    manager.exec()
