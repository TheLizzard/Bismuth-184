import os


if os.name == "posix":
    try:
        from .os_tools_unix import *
    except ImportError:
        from os_tools_unix import *
elif os.name == "nt":
    try:
        from .os_tools_win import *
    except ImportError:
        from os_tools_win import *
else:
    raise OSError(f"Unknown OS: {os.name!r}")