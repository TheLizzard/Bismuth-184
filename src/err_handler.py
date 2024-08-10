from __future__ import annotations
from traceback import format_exception, format_exc
import tkinter as tk
import traceback
import os

PATH:str = os.path.abspath(os.path.dirname(__file__))
ERR_PATH_FORMAT:str = os.path.join(PATH, "error_logs", "error.{n}.txt")

def get_err_path() -> str:
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


class RunManager:
    __slots__ = "funcs", "started_exec"

    def __init__(self) -> None:
        tk.Tk.report_callback_exception = lambda *a: self.report_exc(False)
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

    def register(self, func:Callable, *, exit_on_error:bool=False) -> None:
        assert not self.started_exec, "Can't register any functions after " \
                                      "calling .exec()"
        self.funcs.append((func, exit_on_error))

    def exec(self) -> None:
        def _format_args(args:object) -> tuple[object]:
            return tuple(args) if isinstance(args, tuple|list) else (args,)

        assert not self.started_exec, "You already called .exec()"
        self.started_exec:bool = True
        args:object = ()
        for func, exit_on_error in self.funcs:
            try:
                args:object = func(*_format_args(args))
            except BaseException as error:
                if not isinstance(error, SystemExit):
                    self.report_exc(critical=exit_on_error)
                    if not exit_on_error:
                        continue
                return None

    def report_exc(self, critical:bool, msg:str="") -> None:
        if critical:
            pre_string:str = " Critical error ".center(80, "=")
        else:
            pre_string:str = " Non critical error ".center(80, "=")
        string:str = pre_string + "\n" + format_exc().rstrip("\n") + "\n"
        if msg:
            string += msg + "\n"
        self._display(string + "="*80)

    def _display(self, string:str) -> None:
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
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as file:
        file.write(string)


# Helpers:
def _setup_window(root, string:str) -> tuple[tk.Frame,tk.Text]:
    def close() -> None:
        root.destroy()
    def write_to_file() -> None:
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
        from bettertk.terminaltk.sprites.creator import SpritesCache
        sprite:Image.Image = SpritesCache(256, 256>>1, 220)["error"] # warning
        root.iconphoto(False, sprite)
        return False
    except:
        pass
    try:
        from PIL import Image, ImageTk
        from io import BytesIO
        img:Image.Image = Image.open("sprites/error.png")
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
    def start() -> int:
        global root
        root = tk.Tk()
        root.after(200, lambda: 1/0)
        root.bind("<Delete>", lambda e: 1/0)
        return 1

    def init(arg:int) -> tuple[str,bool]:
        assert arg == 1
        return ("123", False)

    def run(arg1:str, arg2:bool) -> None:
        try:
            root.mainloop()
        except KeyboardInterrupt:
            return None

    manager:RunManager = RunManager()
    manager.register(start, exit_on_error=True)
    manager.register(init, exit_on_error=False)
    manager.register(run, exit_on_error=False)
    manager.exec()