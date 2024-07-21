from __future__ import annotations
import tkinter as tk

try:
    from baseplugin import AllPlugin
    # from rules.seeinsertmanager import SeeInsertManager
    from rules.wrapmanager import WrapManager
    from rules.clipboardmanager import ClipboardManager
    from rules.shortcutmanager import RemoveShortcuts
    from rules.selectmanager import SelectManager
    from rules.commentmanager import CommentManager
    from rules.undomanager import UndoManager
    from rules.findreplacemanager import FindReplaceManager
    from rules.reparentmanager import WidgetReparenterManager
    from rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from rules.xrawidgets import MenuManager
    from rules.whitespacemanager import WhiteSpaceManager
    from rules.colourmanager import ColourManager
    from rules.saveloadmanager import SaveLoadManager
    from rules.all.bracketmanager import BracketManager
except ImportError:
    from .baseplugin import AllPlugin
    # from .rules.seeinsertmanager import SeeInsertManager
    from .rules.wrapmanager import WrapManager
    from .rules.clipboardmanager import ClipboardManager
    from .rules.shortcutmanager import RemoveShortcuts
    from .rules.selectmanager import SelectManager
    from .rules.commentmanager import CommentManager
    from .rules.undomanager import UndoManager
    from .rules.findreplacemanager import FindReplaceManager
    from .rules.reparentmanager import WidgetReparenterManager
    from .rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from .rules.xrawidgets import MenuManager
    from .rules.whitespacemanager import WhiteSpaceManager
    from .rules.colourmanager import ColourManager
    from .rules.saveloadmanager import SaveLoadManager
    from .rules.all.bracketmanager import BracketManager


class BasicPlugin(AllPlugin):
    __slots__ = ()

    def __init__(self, text:tk.Text) -> PythonPlugin:
        rules:list[Rule] = [
                             WrapManager,
                             UndoManager,
                             ColourManager,
                             SelectManager,
                             ClipboardManager,
                             WhiteSpaceManager,
                             BracketManager,
                             FindReplaceManager,
                             SaveLoadManager,
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
        return True