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
    from rules.java.commentmanager import CommentManager
    from rules.java.colourmanager import ColourManager
    from rules.java.whitespacemanager import WhiteSpaceManager
    from rules.java.saveloadmanager import SaveLoadManager
    from rules.java.runmanager import RunManager
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
    from .rules.java.commentmanager import CommentManager
    from .rules.java.colourmanager import ColourManager
    from .rules.java.whitespacemanager import WhiteSpaceManager
    from .rules.java.saveloadmanager import SaveLoadManager
    from .rules.java.runmanager import RunManager


class JavaPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = 'import java.util.Scanner;\n\npublic class Main{\n    public static void main(String[] args){\n        /* comment */\n        System.out.println("Hello World!"); // comment\n    }\n}'

    def __init__(self, *args:tuple) -> JavaPlugin:
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
                             # FindReplaceManager,
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
        return filepath.endswith(".java")