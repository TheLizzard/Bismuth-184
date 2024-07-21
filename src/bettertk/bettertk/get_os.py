from __future__ import annotations
import os


def does_x11_works() -> bool:
    import ctypes
    try:
        ctypes.cdll.LoadLibrary("libX11.so.6")
        return True
    except OSError:
        return False

IS_UNIX:bool = (os.name == "posix")
IS_WINDOWS:bool = (os.name == "nt")
HAS_X11:bool = IS_UNIX and does_x11_works()


assert not (IS_UNIX and IS_WINDOWS), "Both on linux and windows at the " \
                                     "same time?"
assert IS_UNIX or IS_WINDOWS, "OSNotImplemented"


"""
from sys import platform
USING_WINDOWS = ("win" in platform)
"""