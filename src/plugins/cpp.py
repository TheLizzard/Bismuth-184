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
    from rules.cpp.commentmanager import CommentManager
    from rules.cpp.colourmanager import ColourManager
    from rules.cpp.whitespacemanager import WhiteSpaceManager
    from rules.cpp.saveloadmanager import SaveLoadManager
    from rules.cpp.runmanager import RunManager
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
    from .rules.cpp.commentmanager import CommentManager
    from .rules.cpp.colourmanager import ColourManager
    from .rules.cpp.whitespacemanager import WhiteSpaceManager
    from .rules.cpp.saveloadmanager import SaveLoadManager
    from .rules.cpp.runmanager import RunManager


class CppPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = '#include <iostream>\n\nusing namespace std;\n\nint main(){\n    // comment\n    cout << "Hello, world!" << endl;\n    return 0;\n}'

    def __init__(self, *args:tuple) -> CppPlugin:
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
        if filepath.endswith(".cpp") or filepath.endswith(".c++"):
            return True
        if filepath.endswith(".hpp") or filepath.endswith(".h++"):
            return True
        if filepath.endswith(".h"):
            if os.path.exists(filepath.removesuffix("h") + "c"):
                return False
            if os.path.exists(filepath.removesuffix("h") + "cpp"):
                return True
            if os.path.exists(filepath.removesuffix("h") + "c++"):
                return True
            files:list[str] = os.listdir(os.path.dirname(filepath))
            c:int = 0
            cpp:int = 0
            for file in files:
                if file.endswith(".c"):
                    c += 1
                if file.endswith(".cpp") or file.endswith(".c++"):
                    cpp += 1
                if file.endswith(".hpp"):
                    cpp += 1
            if cpp > c:
                return True
        return False