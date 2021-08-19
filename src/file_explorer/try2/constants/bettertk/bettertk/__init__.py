from sys import platform
USING_WINDOWS = ("win" in platform)

if USING_WINDOWS:
    try:
        from .win import *
    except ImportError:
        from win import *
else:
    try:
        from .linux import *
    except ImportError:
        from linux import *


try:
    from .old_bettertk import BetterTk as BetterTkV1
except ImportError:
    from old_bettertk import BetterTk as BetterTkV1


if __name__ == "__main__":
    root = BetterTk()
    root.mainloop()
