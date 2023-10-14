from __future__ import annotations
import tkinter as tk

try:
    from baseplugin import AllPlugin
    # from rules.seeinsertmanager import SeeInsertManager
    from rules.wrapmanager import WrapManager
    from rules.clipboardmanager import ClipboardManager
    from rules.shortcutmanager import RemoveShortcuts
    from rules.selectmanager import SelectManager
    from rules.bracketmanager import BracketManager
    from rules.commentmanager import CommentManager
    from rules.undomanager import UndoManager
    from rules.findreplacemanager import FindReplaceManager
    from rules.reparentmanager import WidgetReparenterManager
    from rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from rules.xrawidgets import MenuManager
    from rules.java.commentmanager import CommentManager
    from rules.java.colourmanager import ColourManager
    from rules.java.whitespacemanager import WhiteSpaceManager
    from rules.java.saveloadmanager import SaveLoadManager
    from rules.java.runmanager import RunManager
except ImportError:
    from .baseplugin import AllPlugin
    # from .rules.seeinsertmanager import SeeInsertManager
    from .rules.wrapmanager import WrapManager
    from .rules.clipboardmanager import ClipboardManager
    from .rules.shortcutmanager import RemoveShortcuts
    from .rules.selectmanager import SelectManager
    from .rules.bracketmanager import BracketManager
    from .rules.commentmanager import CommentManager
    from .rules.undomanager import UndoManager
    from .rules.findreplacemanager import FindReplaceManager
    from .rules.reparentmanager import WidgetReparenterManager
    from .rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from .rules.xrawidgets import MenuManager
    from .rules.java.commentmanager import CommentManager
    from .rules.java.colourmanager import ColourManager
    from .rules.java.whitespacemanager import WhiteSpaceManager
    from .rules.java.saveloadmanager import SaveLoadManager
    from .rules.java.runmanager import RunManager


class JavaPlugin(AllPlugin):
    __slots__ = ()
    DEFAULT_CODE:str = 'import java.util.Scanner;\n\npublic class Main{\n    public static void main(String[] args){\n        /* comment */\n        System.out.println("Hello World!"); // comment\n    }\n}'

    def __init__(self, text:tk.Text) -> PythonPlugin:
        rules:list[Rule] = [
                             WrapManager,
                             UndoManager,
                             ColourManager,
                             SelectManager,
                             ClipboardManager,
                             WhiteSpaceManager,
                             BracketManager,
                             CommentManager,
                             FindReplaceManager,
                             SaveLoadManager,
                             RunManager,
                             # FindReplaceManager,
                             RemoveShortcuts,
                             # Other widgets:
                             WidgetReparenterManager,
                             BarManager,
                             ScrollbarManager,
                             LineManager,
                             # MenuManager,
                           ]
        super().__init__(text, rules)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        if filepath is None:
            return False
        return filepath.endswith(".java")