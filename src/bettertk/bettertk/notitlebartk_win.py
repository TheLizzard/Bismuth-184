# Partially taken from: https://stackoverflow.com/a/2400467/11106801
from __future__ import annotations
from ctypes.wintypes import BOOL, HWND, LONG, HDWP, RECT, HRGN
import tkinter as tk
import ctypes

# Defining types
INT = ctypes.c_int
UINT = ctypes.c_uint
LONG_PTR = ctypes.c_long
RECT_PTR = ctypes.POINTER(RECT)

def _errcheck_not_zero(value, func, args):
    if value in (0, None):
        raise ctypes.WinError()
    return args

# Defining functions
GetWindowLongPtrW = ctypes.windll.user32.GetWindowLongPtrW
GetWindowLongPtrW.argtypes = (HWND, INT)
GetWindowLongPtrW.restype = LONG_PTR
GetWindowLongPtrW.errcheck = _errcheck_not_zero

SetWindowLongPtrW = ctypes.windll.user32.SetWindowLongPtrW
SetWindowLongPtrW.argtypes = (HWND, INT, LONG_PTR)
SetWindowLongPtrW.restype = LONG_PTR
SetWindowLongPtrW.errcheck = _errcheck_not_zero

SetWindowPos = ctypes.windll.user32.SetWindowPos
SetWindowPos.argtypes = (HWND, HWND, INT, INT, INT, INT, UINT)
SetWindowPos.restype = BOOL
SetWindowPos.errcheck = _errcheck_not_zero

# TODO: https://youtu.be/1YGD94lSor8?si=EE-p__2fh9Ws5_X4&t=1526
DeferWindowPos = ctypes.windll.user32.DeferWindowPos
DeferWindowPos.argtypes = (HDWP, HWND, HWND, INT, INT, INT, INT, UINT)
DeferWindowPos.restype = BOOL
DeferWindowPos.errcheck = _errcheck_not_zero

BeginDeferWindowPos = ctypes.windll.user32.BeginDeferWindowPos
BeginDeferWindowPos.argtypes = (INT,)
BeginDeferWindowPos.restype = HDWP
BeginDeferWindowPos.errcheck = _errcheck_not_zero

EndDeferWindowPos = ctypes.windll.user32.EndDeferWindowPos
EndDeferWindowPos.argtypes = (HDWP,)
EndDeferWindowPos.restype = BOOL
EndDeferWindowPos.errcheck = _errcheck_not_zero

InvalidateRect = ctypes.windll.user32.InvalidateRect
InvalidateRect.argtypes = (HWND, RECT_PTR, BOOL)
InvalidateRect.restype = BOOL
InvalidateRect.errcheck = _errcheck_not_zero

RedrawWindow = ctypes.windll.user32.RedrawWindow
RedrawWindow.argtypes = (HWND, RECT_PTR, HRGN, UINT)
RedrawWindow.restype = BOOL
RedrawWindow.errcheck = _errcheck_not_zero

def get_handle(root:tk.Tk) -> int:
    root.update_idletasks()
    # This gets the window's parent same as `ctypes.windll.user32.GetParent`
    return GetWindowLongPtrW(root.winfo_id(), GWLP_HWNDPARENT)


# Constants
GWL_STYLE = -16
GWLP_HWNDPARENT = -8
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOREDRAW = 0x0008
SWP_NOACTIVATE = 0x0010
SWP_DRAWFRAME = 0x0020
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080
SWP_NOCOPYBITS = 0x0100
SWP_NOOWNERZORDER = 0x0200
SWP_NOREPOSITION = 0x0200
SWP_NOSENDCHANGING = 0x0400
SWP_DEFERERASE = 0x2000
SWP_ASYNCWINDOWPOS = 0x4000

RDW_INVALIDATE = 0x0001
RDW_UPDATENOW = 0x0100


# Only needed for the `NotImplementedError` error.
_default_root:NoTitlebarTk = None


class NoTitlebarTk:
    def __init__(self, master=None, **kwargs):
        # Figure out the master.
        global _default_root
        if master is None:
            if _default_root is None:
                _default_root = self
            else:
                raise NotImplementedError("You can't have 2 `tk.Tk`s right " + \
                                          "now. I am trying to fix that.")
            self.root = tk.Tk(**kwargs)
        elif isinstance(master, (tk.Misc, NoTitlebarTk)):
            self.root = tk.Toplevel(master, **kwargs)
        else:
            raise ValueError("Invalid `master` argument. It must be " \
                             "`None` or a tkinter widget")

        self._fullscreen:bool = False

        dir_self:set[str] = set(dir(self))
        for attribute_name in dir(self.root):
            if (attribute_name[-2:] == "__") or (attribute_name in dir_self):
                continue
            attribute = getattr(self.root, attribute_name)
            setattr(self, attribute_name, attribute)

        self._overrideredirect()

    @property
    def report_callback_exception(self) -> object:
        return self.root.report_callback_exception

    @report_callback_exception.setter
    def report_callback_exception(self, new:object) -> None:
        raise RuntimeError("Only set report_callback_exception using " \
                           "tk.Tk.report_callback_exception = ···")

    def _overrideredirect(self) -> None:
        self.hwnd:int = get_handle(self.root)
        style:int = GetWindowLongPtrW(self.hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME)
        SetWindowLongPtrW(self.hwnd, GWL_STYLE, style)

    def overrideredirect(self, boolean:bool=None) -> None:
        raise RuntimeError("This window must stay as `overrideredirect`")
    wm_overrideredirect = overrideredirect

    def attributes(self, *args) -> None:
        if (len(args) == 2) and (args[0] == "-fullscreen"):
            value = args[1]
            if isinstance(value, str):
                value = value.lower() in ("1", "true")
            if value:
                return self.fullscreen()
            return self.notfullscreen()
        return self.root.attributes(*args)
    wm_attributes = attributes

    def fullscreen(self, *, wait:bool=False) -> None:
        if self._fullscreen:
            return None
        self._fullscreen:bool = True
        self.root.attributes("-fullscreen", True)
    maximised = fullscreen

    def notfullscreen(self, *, wait:bool=False) -> None:
        if not self._fullscreen:
            return None
        self._fullscreen:bool = False
        self.root.attributes("-fullscreen", False)
        self._overrideredirect()
    notmaximised = notfullscreen

    def toggle_fullscreen(self, *, wait:bool=False) -> None:
        if self._fullscreen:
            self.notfullscreen(wait=wait)
        else:
            self.fullscreen(wait=wait)
    toggle_maximised = toggle_fullscreen

    @property
    def _maximised(self) -> bool:
        """
        There is no difference between fullscreen and maximised window
        on Windows as far as I am aware.
        """
        return self._fullscreen

    def _move_window_to(self, x:int, y:int) -> None:
        flags = SWP_NOZORDER | SWP_NOSIZE
        SetWindowPos(self.hwnd, 0, x, y, 0, 0, flags)

    def _resize_window_to(self, width:int, height:int) -> None:
        flags = SWP_NOZORDER | SWP_NOMOVE
        # Tried to stop stuttering when resizing nw
        # flags |= SWP_NOCOPYBITS | SWP_NOREDRAW
        SetWindowPos(self.hwnd, 0, 0, 0, width, height, flags)

    def _geometry_window_to(self, *, width:int, height:int, x:int, y:int):
        SetWindowPos(self.hwnd, 0, x, y, width, height, SWP_NOZORDER)

    def geometry(self, geometry:str=None) -> str:
        if geometry is None:
            return self.root.geometry()

        x = y = width = height = 0
        flags = SWP_NOZORDER
        if "+" in geometry:
            geometry, x, y = geometry.split("+")
            x, y = int(x), int(y)
        else:
            flags |= SWP_NOMOVE
        if "x" in geometry:
            width, height = geometry.split("x")
            width, height = int(width), int(height)
        else:
            flags |= SWP_NOSIZE
        SetWindowPos(self.hwnd, 0, x, y, width, height, flags)

    def destroy(self) -> None:
        global _default_root
        if _default_root == self:
            _default_root = None
        self.root.destroy()

    def move_to_current_workspace(self) -> Success:
        return False # Implement me

    def resizable(self, x:bool=None, y:bool=None) -> None:
        # Windows strips away our overrideredirect if we call `.resizable`
        #   in tkinter. Caused by commit: Bismuth 4.3.6@bettertk/__init__.py
        # TODO: Fix me. (Not urgent since BetterTk handles it pretty well)
        return None


class Draggable(NoTitlebarTk):
    def __init__(self, master:tk.Misc=None):
        super().__init__(master)
        self.dragging:bool = False
        self.bind("<Button-1>" ,self.clickwin)
        self.bind("<B1-Motion>", self.dragwin)
        self.bind("<ButtonRelease-1>", self.releasewin)

    def dragwin(self, event:tk.Event) -> None:
        if self.dragging:
            x:int = self.winfo_pointerx() - self._offsetx
            y:int = self.winfo_pointery() - self._offsety
            super()._move_window_to(x, y)

    def releasewin(self, event:tk.Event) -> None:
        self.dragging:bool = False

    def clickwin(self, event:tk.Event) -> None:
        self._offsetx:int = self.winfo_pointerx() - self.winfo_rootx()
        self._offsety:int = self.winfo_pointery() - self.winfo_rooty()
        self.dragging:bool = True


# Example 1
if __name__ == "__main__":
    root = Draggable()
    root.title("AppWindow Test")
    root.geometry("100x100")

    button = tk.Button(root, text="Exit", command=root.destroy)
    button.pack(fill="x")

    button = tk.Button(root, text="Minimise", command=root.iconify)
    button.pack(fill="x")

    button = tk.Button(root, text="Fullscreen", command=root.toggle_fullscreen)
    button.pack(fill="x")

    root.mainloop()


# Example 2
if __name__ == "__main__a":
    root = tk.Tk()
    child = Draggable(root) # A toplevel
    child.title("AppWindow Test")
    child.geometry("100x100")

    button = tk.Button(child, text="Exit", command=child.destroy)
    button.pack(fill="x")

    button = tk.Button(child, text="Minimise", command=child.iconify)
    button.pack(fill="x")

    button = tk.Button(child, text="Fullscreen", command=child.toggle_fullscreen)
    button.pack(fill="x")

    root.mainloop()