# Mostly taken from: https://stackoverflow.com/a/30819099/11106801
import tkinter as tk
from time import sleep

import ctypes
from ctypes.wintypes import BOOL, HWND, LONG

INT = ctypes.c_int
UINT = ctypes.c_uint
LONG_PTR = ctypes.c_uint

def _errcheck_not_zero(value, func, args):
    if value == 0:
        raise ctypes.WinError()
    return args

GetParent = ctypes.windll.user32.GetParent
GetParent.argtypes = (HWND, )
GetParent.restype = HWND
GetParent.errcheck = _errcheck_not_zero

GetWindowLongPtrW = ctypes.windll.user32.GetWindowLongPtrW
GetWindowLongPtrW.argtypes = (HWND, INT)
GetWindowLongPtrW.restype = LONG_PTR
GetWindowLongPtrW.errcheck = _errcheck_not_zero

SetWindowLongPtrW = ctypes.windll.user32.SetWindowLongPtrW
SetWindowLongPtrW.argtypes = (HWND, INT, LONG_PTR)
SetWindowLongPtrW.restype = LONG_PTR
SetWindowLongPtrW.errcheck = _errcheck_not_zero

GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080


class NoTitlebarTk:
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
        elif isinstance(master, tk.Misc):
            self.root = tk.Toplevel(master)
        else:
            raise ValueError("Invalid `master` argument. It must be " \
                             "`None` or a tkinter widget")

        self.locked = False
        self._fullscreen = False
        self.map_binding = self.root.bind("<Map>", self._overrideredirect)

        for method_name in dir(self.root):
            method = getattr(self.root, method_name)
            if (method_name not in dir(self)) and (method_name[-2:] != "__"):
                setattr(self, method_name, method)

    def _overrideredirect(self, event:tk.Event=None) -> None:
        if self.locked:
            return None
        self.locked = True
        if self.map_binding is not None:
            self.root.unbind("<Map>", self.map_binding)
            self.map_binding = None
        self.root.overrideredirect(True)
        self.root.update_idletasks()
        self.hwnd = GetParent(self.root.winfo_id())
        style = GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        res = SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, style)

        # re-assert the new window style
        self.root.withdraw()
        self.root.after(10, self.root.deiconify)
        # self.root.after(20, self.root.focus_force) # Might be useless

        # Apply the `.after` changes:
        sleep(0.1)
        self.root.update()

        self.locked = False

    def overrideredirect(self, boolean:bool=None) -> None:
        raise RuntimeError("This window must stay as `overrideredirect`")
    wm_overrideredirect = overrideredirect

    def attributes(self, *args) -> None:
        if (len(args) == 2) and (args[0] == "-fullscreen"):
            value = args[1]
            if isinstance(value, str):
                value = value.lower() in ("1", "true")
            if bool(value):
                return self.fullscreen()
            return self.notfullscreen()
        return self.root.attributes(*args)
    wm_attributes = attributes

    def iconify(self) -> None:
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.update()
        self.map_binding = self.root.bind("<Map>", self._overrideredirect)

    def fullscreen(self) -> None:
        if self._fullscreen:
            return None
        self._fullscreen = True
        self.root.overrideredirect(False)
        self.root.attributes("-fullscreen", True)

    def notfullscreen(self) -> None:
        if not self._fullscreen:
            return None
        self._fullscreen = False
        self.root.attributes("-fullscreen", False)
        self._overrideredirect()
        self.map_binding = self.root.bind("<Map>", self._overrideredirect)

    def toggle_fullscreen(self) -> None:
        if self._fullscreen:
            self.notfullscreen()
        else:
            self.fullscreen()


# Example 1
if __name__ == "__main__":
    root = NoTitlebarTk()
    root.title("AppWindow Test")
    root.geometry("100x78")

    button = tk.Button(root, text="Exit", command=root.destroy)
    button.pack(fill="x")

    button = tk.Button(root, text="Minimise", command=root.iconify)
    button.pack(fill="x")

    button = tk.Button(root, text="Fullscreen", command=root.toggle_fullscreen)
    button.pack(fill="x")

    root.mainloop()


# Example 2
if __name__ == "__main__":
    root = tk.Tk()
    child = NoTitlebarTk(root) # A toplevel
    child.title("AppWindow Test")
    child.geometry("100x78")

    button = tk.Button(child, text="Exit", command=child.destroy)
    button.pack(fill="x")

    button = tk.Button(child, text="Minimise", command=child.iconify)
    button.pack(fill="x")

    button = tk.Button(child, text="Fullscreen", command=child.toggle_fullscreen)
    button.pack(fill="x")

    root.mainloop()
