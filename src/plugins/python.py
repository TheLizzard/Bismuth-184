from __future__ import annotations
import tkinter as tk

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
    from rules.python.commentmanager import CommentManager
    from rules.python.colourmanager import ColourManager
    from rules.python.whitespacemanager import WhiteSpaceManager
    from rules.python.saveloadmanager import SaveLoadManager
    from rules.python.runmanager import RunManager
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
    from .rules.undomanager import UndoManager
    from .rules.findreplacemanager import FindReplaceManager
    from .rules.reparentmanager import ReparentManager
    from .rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from .rules.xrawidgets import MenuManager
    from .rules.python.commentmanager import CommentManager
    from .rules.python.colourmanager import ColourManager
    from .rules.python.whitespacemanager import WhiteSpaceManager
    from .rules.python.saveloadmanager import SaveLoadManager
    from .rules.python.runmanager import RunManager


class PythonPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = 'import this\n\nprint("Hello world")'

    def __init__(self, *args:tuple) -> PythonPlugin:
        rules:list[Rule] = [
                             RunManager,
                             WrapManager,
                             UndoManager,
                             ColourManager,
                             SelectManager,
                             BracketManager,
                             CommentManager,
                             SaveLoadManager,
                             RemoveShortcuts,
                             ClipboardManager,
                             SeeInsertManager,
                             WhiteSpaceManager,
                             ControlIJKLManager,
                             InsertDeleteManager,
                             FindReplaceManager,
                             # Other widgets:
                             BarManager,
                             LineManager,
                             ScrollbarManager,
                             ReparentManager,
                             # MenuManager,
                           ]
        super().__init__(*args, rules)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        if filepath is None:
            return False
        return filepath.endswith(".py")