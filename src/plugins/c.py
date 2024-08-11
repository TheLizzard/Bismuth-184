from __future__ import annotations
import tkinter as tk
import os

try:
    from baseplugin import BasePlugin
    from rules.insertdeletemanager import InsertDeleteManager
    from rules.seeinsertmanager import SeeInsertManager
    from rules.controlijklmanager import ControlIJKLManager
    from rules.wrapmanager import WrapManager
    from rules.clipboardmanager import ClipboardManager
    from rules.shortcutmanager import RemoveShortcuts
    from rules.selectmanager import SelectManager
    from rules.bracketmanager import BracketManager
    from rules.commentmanager import CommentManager
    from rules.undomanager import UndoManager
    from rules.findreplacemanager import FindReplaceManager
    from rules.reparentmanager import ReparentManager
    from rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from rules.xrawidgets import MenuManager
    from rules.c.commentmanager import CommentManager
    from rules.c.colourmanager import ColourManager
    from rules.c.whitespacemanager import WhiteSpaceManager
    from rules.c.saveloadmanager import SaveLoadManager
    from rules.c.runmanager import RunManager
except ImportError:
    from .baseplugin import BasePlugin
    from .rules.insertdeletemanager import InsertDeleteManager
    from .rules.seeinsertmanager import SeeInsertManager
    from .rules.controlijklmanager import ControlIJKLManager
    from .rules.wrapmanager import WrapManager
    from .rules.clipboardmanager import ClipboardManager
    from .rules.shortcutmanager import RemoveShortcuts
    from .rules.selectmanager import SelectManager
    from .rules.bracketmanager import BracketManager
    from .rules.commentmanager import CommentManager
    from .rules.undomanager import UndoManager
    from .rules.findreplacemanager import FindReplaceManager
    from .rules.reparentmanager import ReparentManager
    from .rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from .rules.xrawidgets import MenuManager
    from .rules.c.commentmanager import CommentManager
    from .rules.c.colourmanager import ColourManager
    from .rules.c.whitespacemanager import WhiteSpaceManager
    from .rules.c.saveloadmanager import SaveLoadManager
    from .rules.c.runmanager import RunManager


class CPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = '#include <stdio.h>\n\nint main(){\n    // comment\n    printf("Hello, World!\\n");\n    return 0;\n}'

    def __init__(self, *args:tuple) -> CPlugin:
        rules:list[Rule] = [
                             InsertDeleteManager,
                             WrapManager,
                             UndoManager,
                             ControlIJKLManager,
                             ColourManager,
                             SelectManager,
                             ClipboardManager,
                             SeeInsertManager,
                             WhiteSpaceManager,
                             BracketManager,
                             CommentManager,
                             FindReplaceManager,
                             SaveLoadManager,
                             RunManager,
                             RemoveShortcuts,
                             # Other widgets:
                             ReparentManager,
                             BarManager,
                             ScrollbarManager,
                             LineManager,
                             # MenuManager,
                           ]
        super().__init__(*args, rules)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        if filepath is None:
            return False
        if filepath.endswith(".c"):
            return True
        if filepath.endswith(".h"):
            if os.path.exists(filepath.removesuffix("h") + "cpp"):
                return False
            if os.path.exists(filepath.removesuffix("h") + "c++"):
                return False
            if os.path.exists(filepath.removesuffix("h") + "c"):
                return True
            c:int = 0
            cpp:int = 0
            for file in os.listdir(os.path.dirname(filepath)):
                if file.endswith(".c"):
                    c += 1
                if file.endswith(".cpp") or file.endswith(".c++"):
                    cpp += 1
                if file.endswith(".hpp"):
                    cpp += 1
            if c >= cpp:
                return True
        return False