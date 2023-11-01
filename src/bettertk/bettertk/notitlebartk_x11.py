# Mostly taken from: https://www.tonyobryan.com//index.php?article=9
# Inspired by: https://github.com/EDCD/EDMarketConnector/blob/main/theme.py
# TODO?: Implement _NET_WM_STATE_SKIP_TASKBAR
from __future__ import annotations
from time import sleep
import tkinter as tk
import ctypes

# Defining types
CHAR = ctypes.c_char
UCHAR = ctypes.c_ubyte
BOOL = ctypes.c_bool
INT = ctypes.c_int
UINT = ctypes.c_uint
LONG = ctypes.c_long
ULONG = ctypes.c_ulong
PTR = ctypes.c_void_p

CHAR_PTR = ctypes.POINTER(CHAR)
UINT_PTR = ctypes.POINTER(UINT)
ULONG = ctypes.c_ulong


VISUAL = UCHAR*56
DISPLAY = PTR
ATOM = LONG
WINDOW = LONG
SCREEN = INT
VISUALID = LONG # Not sure?
COLORMAP = LONG # Not sure?
CURSOR = LONG   # Not sure?
PIXMAP = LONG   # Not sure?
WINDOW_PTR = ctypes.POINTER(WINDOW)
VISUAL_PTR = ctypes.POINTER(VISUAL)
class HINTS(ctypes.Structure):
    _fields_ = (("flags", ULONG),
                ("functions", ULONG),
                ("decorations", ULONG),
                ("inputMode", LONG),
                ("status", ULONG))
HINTS_PTR = ctypes.POINTER(HINTS)
class XSETWINDOWATTRIBUTES(ctypes.Structure):
    _fields_ = (("background_pixmap", PIXMAP),
                ("background_pixel", ULONG),
                ("border_pixmap", PIXMAP),
                ("border_pixel", ULONG),
                ("bit_gravity", INT),
                ("win_gravity", INT),
                ("backing_store", INT),
                ("backing_planes", ULONG),
                ("backing_pixel", ULONG),
                ("save_under", BOOL),
                ("event_mask", LONG),
                ("do_not_propagate_mask", LONG),
                ("override_redirect", BOOL),
                ("colormap", COLORMAP),
                ("cursor", CURSOR))
XSETWINDOWATTRIBUTES_PTR = ctypes.POINTER(XSETWINDOWATTRIBUTES)
class XVISUALINFO(ctypes.Structure):
    _fields_ = (("visual", VISUAL_PTR),
                ("visualid", VISUALID),
                ("screen", INT),
                ("depth", INT),
                ("class", INT),
                ("red_mask", ULONG),
                ("green_mask", ULONG),
                ("blue_mask", ULONG),
                ("colormap_size", INT),
                ("bits_per_rgb", INT))
XVISUALINFO_PTR = ctypes.POINTER(XVISUALINFO)

def errcheck_not_zero(value, func, args):
    if value == 0:
        args_str = ", ".join(map(str, args))
        raise OSError(f"{func.__name__}({args_str}) => {value}")
    return args

def errcheck_zero(value, func, args):
    if value != 0:
        args_str = ", ".join(map(str, args))
        raise OSError(f"{func.__name__}({args_str}) => {value}")
    return args

def string_to_c(data:str) -> CHAR_PTR:
    return ctypes.create_string_buffer(data.encode())

libx11 = ctypes.cdll.LoadLibrary("libX11.so.6")

# Constants
PropModeReplace = 0
XA_ATOM = 4

ALLOCNONE = 0
TRUECOLOR = 4
CWCOLORMAP = 8192

# Defining functions
XInternAtom = libx11.XInternAtom
XInternAtom.argtypes = (PTR, CHAR_PTR, BOOL)
XInternAtom.restype = ATOM
XInternAtom.errcheck = errcheck_not_zero

XOpenDisplay = libx11.XOpenDisplay
XOpenDisplay.argtypes = (CHAR_PTR, )
XOpenDisplay.restype = DISPLAY
XOpenDisplay.errcheck = errcheck_not_zero

XChangeProperty = libx11.XChangeProperty
XChangeProperty.argtypes = (DISPLAY, WINDOW, ATOM, ATOM, INT, INT, HINTS_PTR, INT)
XChangeProperty.restype = INT
XChangeProperty.errcheck = errcheck_not_zero

XQueryTree = libx11.XQueryTree
XQueryTree.argtypes = (DISPLAY, WINDOW, WINDOW_PTR, WINDOW_PTR, WINDOW_PTR, UINT_PTR)
XQueryTree.restype = INT
XQueryTree.errcheck = errcheck_not_zero

XFlush = libx11.XFlush
XFlush.argtypes = (DISPLAY, )
XFlush.restype = INT
XFlush.errcheck = errcheck_not_zero

XCloseDisplay = libx11.XCloseDisplay
XCloseDisplay.argtypes = (DISPLAY, )
XCloseDisplay.restype = INT
XCloseDisplay.errcheck = errcheck_zero

XDefaultScreen = libx11.XDefaultScreen
XDefaultScreen.argtypes = (DISPLAY, )
XDefaultScreen.restype = SCREEN

XDefaultRootWindow = libx11.XDefaultRootWindow
XDefaultRootWindow.argtypes = (DISPLAY, )
XDefaultRootWindow.restype = WINDOW

XChangeWindowAttributes = libx11.XChangeWindowAttributes
XChangeWindowAttributes.argtypes = (DISPLAY, WINDOW, ULONG, XSETWINDOWATTRIBUTES_PTR)
XChangeWindowAttributes.restype = INT
XChangeWindowAttributes.errcheck = errcheck_not_zero

XCreateColormap = libx11.XCreateColormap
XCreateColormap.argtypes = (DISPLAY, WINDOW, VISUAL_PTR, INT)
XCreateColormap.restype = COLORMAP
XCreateColormap.errcheck = errcheck_not_zero

XMatchVisualInfo = libx11.XMatchVisualInfo
XMatchVisualInfo.argtypes = (DISPLAY, SCREEN, INT, INT, XVISUALINFO_PTR)
XMatchVisualInfo.restype = BOOL
XMatchVisualInfo.errcheck = errcheck_not_zero

XMapWindow = libx11.XMapWindow
XMapWindow.argtypes = (DISPLAY, WINDOW)
XMapWindow.restype = INT
XMapWindow.errcheck = errcheck_not_zero

XUnmapWindow = libx11.XUnmapWindow
XUnmapWindow.argtypes = (DISPLAY, WINDOW)
XUnmapWindow.restype = INT
XUnmapWindow.errcheck = errcheck_not_zero

XReparentWindow = libx11.XReparentWindow
XReparentWindow.argtypes = (DISPLAY, WINDOW, WINDOW, INT, INT)
XReparentWindow.restype = INT
XReparentWindow.errcheck = errcheck_not_zero

XSync = libx11.XSync
XSync.argtypes = (DISPLAY, BOOL)
XSync.restype = INT
XSync.errcheck = errcheck_not_zero

XAddToSaveSet = libx11.XAddToSaveSet
XAddToSaveSet.argtypes = (DISPLAY, WINDOW)
XAddToSaveSet.restype = INT
XAddToSaveSet.errcheck = errcheck_not_zero

XClearArea = libx11.XClearArea
XClearArea.argtypes = (DISPLAY, WINDOW, INT, INT, UINT, UINT, BOOL)
XClearArea.restype = INT
XClearArea.errcheck = errcheck_not_zero

XResizeWindow = libx11.XResizeWindow
XResizeWindow.argtypes = (DISPLAY, WINDOW, UINT, UINT)
XResizeWindow.restype = INT
XResizeWindow.errcheck = errcheck_not_zero

XMoveWindow = libx11.XMoveWindow
XMoveWindow.argtypes = (DISPLAY, WINDOW, INT, INT)
XMoveWindow.restype = INT
XMoveWindow.errcheck = errcheck_not_zero

XMoveResizeWindow = libx11.XMoveResizeWindow
XMoveResizeWindow.argtypes = (DISPLAY, WINDOW, INT, INT, UINT, UINT)
XMoveResizeWindow.restype = INT
XMoveResizeWindow.errcheck = errcheck_not_zero

XClearArea = libx11.XClearArea
XClearArea.argtypes = (DISPLAY, WINDOW, INT, INT, UINT, UINT, BOOL)
XClearArea.restype = INT
XClearArea.errcheck = errcheck_not_zero


_display_owners:set[NoTitlebarTk] = set()
DEBUG:bool = False
TEST:bool = False


class CleanupTk(tk.Tk):
    def destroy(self) -> None:
        super().destroy()
        self.cleanup()
    def cleanup(self) -> None:
        ...

class CleanupToplevel(tk.Toplevel):
    def destroy(self) -> None:
        super().destroy()
        self.cleanup()
    def cleanup(self) -> None:
        ...


class NoTitlebarTk:
    def __init__(self, master=None, withdraw:bool=False, **kwargs):
        # Figure out the master.
        if master is None:
            self.root = CleanupTk(**kwargs)
        elif isinstance(master, (tk.Misc, NoTitlebarTk)):
            self.wait_for_func(True, master.winfo_ismapped)
            self.root = CleanupToplevel(master, **kwargs)
        else:
            raise ValueError("Invalid `master` argument. It must be " \
                             "`None` or a tkinter widget")

        self._fullscreen:bool = False
        self._maximised:bool = False
        self._cleanedup:bool = False

        dir_self:list = dir(self)
        for attribute_name in dir(self.root):
            if attribute_name[-2:] == "__":
                continue
            attribute = getattr(self.root, attribute_name)
            if attribute_name not in dir_self:
                setattr(self, attribute_name, attribute)

        self.display:DISPLAY = self._get_display(master)
        self.wait_for_func(True, self.root.winfo_ismapped)
        self.window:WINDOW = self._get_parent(self.root.winfo_id())
        self._overrideredirect()
        self.wait_for_func(True, self.root.winfo_ismapped)

    def _get_display(self, widget:tk.Misc) -> DISPLAY:
        self.root.cleanup = self.cleanup
        _display_owners.add(self)
        if DEBUG: print(f"[DEBUG]: display_owners = {len(_display_owners)}")
        for notitlebartk in _display_owners:
            if notitlebartk is not self:
                return notitlebartk.display
        if DEBUG: print(f"[DEBUG]: Opening display")
        return XOpenDisplay(None)

    def cleanup(self) -> None:
        if self._cleanedup:
            # BetterTk calls self.destroy() twice.
            return None
        assert self in _display_owners, "InternalError"
        self._cleanedup:bool = True
        _display_owners.remove(self)
        if DEBUG: print(f"[DEBUG]: display_owners = {len(_display_owners)}")
        if len(_display_owners) == 0:
            if DEBUG: print(f"[DEBUG]: Closing display")
            XCloseDisplay(self.display)

    def _get_parent(self, winid:int) -> WINDOW:
        parent:WINDOW = WINDOW()
        root:WINDOW = WINDOW()
        children:WINDOW = WINDOW()
        num_children:UINT = UINT()
        XQueryTree(self.display, winid, ctypes.byref(root),
                   ctypes.byref(parent), ctypes.byref(children),
                   ctypes.byref(num_children))
        if num_children != 0:
            # Free children because it is a non-empty array of WINDOWs
            # WINDOW* children;
            pass
        return parent

    def _overrideredirect(self) -> None:
        # Change the motif hints of the window
        motif_hints = XInternAtom(self.display, string_to_c("_MOTIF_WM_HINTS"),
                                  False)
        hints = HINTS()
        hints.flags = 2 # Specify that we're changing the window decorations.
        hints.decorations = False
        XChangeProperty(self.display, self.window, motif_hints, XA_ATOM, 32,
                        PropModeReplace, ctypes.byref(hints), 5)
        # Flush the changes
        XFlush(self.display)

    def reparent_window(self, child:WINDOW, x:int, y:int) -> None:
        self._reparent_window(child, self.window, x, y)

    def _reparent_window(self, child:WINDOW, parent:WINDOW, x:int, y:int):
        #raise NotImplementedError("Right now this doesn't handle events " \
        #                          "or repaints correctly.")
        XUnmapWindow(self.display, child)
        XSync(self.display, False)
        XReparentWindow(self.display, child, parent, x, y)
        XMapWindow(self.display, child)
        sleep(0.1)
        XSync(self.display, False)
        XAddToSaveSet(self.display, child)
        XFlush(self.display) # Might be unneeded?

    """
    def transparentcolor(self, colour:str) -> None:
        vinfo = XVISUALINFO()
        XMatchVisualInfo(self.display, XDefaultScreen(self.display), 32,
                         TRUECOLOR, ctypes.byref(vinfo))

        attr = XSETWINDOWATTRIBUTES()
        attr.colormap = XCreateColormap(self.display,
                                        XDefaultRootWindow(self.display),
                                        vinfo.visual, ALLOCNONE)
        attr.border_pixel = 0
        attr.background_pixel = 0

        # print(self.display, self.window, CWCOLORMAP, attr)
        XChangeWindowAttributes(self.display, self.window, CWCOLORMAP,
                                ctypes.byref(attr))
        XFlush(self.display)
    # Please kill me, it doesn't do anything for some reason"""

    def overrideredirect(self, boolean:bool=None) -> None:
        raise RuntimeError("This window must stay as `overrideredirect`")
    wm_overrideredirect = overrideredirect

    def attributes(self, *args) -> None:
        if len(args) == 2:
            if args[0] == "-type":
                raise RuntimeError("You will mess up the work I did.")
            elif args[0] == "-fullscreen":
                value = args[1]
                if isinstance(value, str):
                    value = value.lower() in ("1", "true")
                if value:
                    return self.fullscreen()
                return self.notfullscreen()
        return self.root.attributes(*args)
    wm_attributes = attributes

    def fullscreen(self, *, wait:bool=False) -> None:
        assert not wait, "NotImplemented"
        if self._fullscreen:
            return None
        self._fullscreen:bool = True
        self.notmaximised()
        self.root.attributes("-fullscreen", True)

    def notfullscreen(self, *, wait:bool=False) -> None:
        assert not wait, "NotImplemented"
        if not self._fullscreen:
            return None
        self._fullscreen:bool = False
        self.root.attributes("-fullscreen", False)

    def toggle_fullscreen(self, *, wait:bool=False) -> None:
        if self._fullscreen:
            self.notfullscreen(wait=wait)
        else:
            self.fullscreen(wait=wait)

    def maximised(self, *, wait:bool=False) -> None:
        if self._maximised:
            return None
        self._maximised:bool = True
        self.notfullscreen()
        self.root.attributes("-zoomed", True)
        if wait:
            self.wait_for_func(True, self.root.attributes, "-zoomed")

    def notmaximised(self, *, wait:bool=False) -> None:
        if not self._maximised:
            return None
        self._maximised:bool = False
        self.root.attributes("-zoomed", False)
        if wait:
            self.wait_for_func(False, self.root.attributes, "-zoomed")

    def toggle_maximised(self, *, wait:bool=False) -> None:
        if self._maximised:
            self.notmaximised(wait=wait)
        else:
            self.maximised(wait=wait)

    def wait_for_func(self, waiting_for:T, func:Function[Args,T], *args:Args):
        def inner() -> None:
            if func(*args) == waiting_for:
                self.root.quit()
            else:
                self.root.after(10, inner)
        if func(*args) != waiting_for:
            inner()
            self.root.mainloop()


class Draggable(NoTitlebarTk):
    def __init__(self):
        super().__init__()
        self.dragging:bool = False
        self.bind("<Button-1>" ,self.clickwin)
        self.bind("<B1-Motion>", self.dragwin)
        self.bind("<ButtonRelease-1>", self.releasewin)

    def dragwin(self, event:tk.Event) -> None:
        if self.dragging:
            x:int = self.winfo_pointerx() - self._offsetx
            y:int = self.winfo_pointery() - self._offsety
            self.geometry(f"+{x}+{y}")

    def releasewin(self, event:tk.Event) -> None:
        self.dragging:bool = False

    def clickwin(self, event:tk.Event) -> None:
        self._offsetx:int = self.winfo_pointerx() - self.winfo_rootx()
        self._offsety:int = self.winfo_pointery() - self.winfo_rooty()
        self.dragging:bool = True


# Example 1
if __name__ == "__main__":
    root = NoTitlebarTk()
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
if __name__ == "__main__":
    root = NoTitlebarTk()
    root.geometry("150x150")
    child = NoTitlebarTk(root)
    child.geometry("150x150")

    tk.Label(root, text="Master").pack(fill="x")
    tk.Button(root, text="Exit", command=root.destroy).pack(fill="x")
    tk.Button(root, text="Minimise", command=root.iconify).pack(fill="x")
    tk.Button(root, text="Fullscreen", command=root.toggle_fullscreen).pack(fill="x")

    tk.Label(child, text="Child").pack(fill="x")
    tk.Button(child, text="Exit", command=child.destroy).pack(fill="x")
    tk.Button(child, text="Minimise", command=child.iconify).pack(fill="x")
    tk.Button(child, text="Fullscreen", command=child.toggle_fullscreen).pack(fill="x")

    root.mainloop()


# Test 1
if (__name__ == "__main__") and TEST:
    from time import sleep
    for i in range(1000):
        root = NoTitlebarTk()
        root.geometry("10x10+0+0")
        for j in range(1000):
            root.update()
        root.destroy()

        if i % 20 == 0:
            print(f"Passed {i}th test")


# Test 2
if (__name__ == "__main__") and TEST:
    print("Creating root")
    root = tk.Tk()
    print("Creating child a")
    childa = NoTitlebarTk(root)
    print("Creating child b")
    childb = NoTitlebarTk(root)


"""
UCHAR_PTR = ctypes.POINTER(UCHAR)


def uchar_ptr(data:tuple[int]) -> PTR:
    data = (UCHAR * len(data))(*data)
    return data

class EVENT(ctypes.Structure):
    _fields_ = [("no idea what this is", LONG*24)]
EVENT_PTR = ctypes.POINTER(EVENT)


XRootWindow = libx11.XRootWindow
XRootWindow.argtypes = (DISPLAY, SCREEN)
XRootWindow.restype = WINDOW
XRootWindow.errcheck = errcheck_not_zero

XBlackPixel = libx11.XBlackPixel
XBlackPixel.argtypes = (DISPLAY, SCREEN)
XBlackPixel.restype = ULONG

XWhitePixel = libx11.XWhitePixel
XWhitePixel.argtypes = (DISPLAY, SCREEN)
XWhitePixel.restype = ULONG

XCreateSimpleWindow = libx11.XCreateSimpleWindow
XCreateSimpleWindow.argtypes = (DISPLAY, WINDOW, INT, INT, UINT, UINT, UINT,
                                ULONG)
XCreateSimpleWindow.restype = SCREEN
XCreateSimpleWindow.errcheck = errcheck_not_zero

XNextEvent = libx11.XNextEvent
XNextEvent.argtypes = (DISPLAY, EVENT_PTR)
XNextEvent.restype = INT
XNextEvent.errcheck = errcheck_not_zero


root = tk.Tk()
root.update_idletasks()
handle = root.winfo_id()

display = XOpenDisplay(None)

parent = WINDOW()
XQueryTree(display, handle, ctypes.byref(WINDOW()), ctypes.byref(parent),
           ctypes.byref(WINDOW()), ctypes.byref(UINT()))

motif_hints = XInternAtom(display, string_to_c("_MOTIF_WM_HINTS"), False)
hints = uchar_ptr((2, 0, 0, 0, 0))
XChangeProperty(display, parent, motif_hints, XA_ATOM, 32, PropModeReplace,
                hints, 5)

XFlush(display)
"""