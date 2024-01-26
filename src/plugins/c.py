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
    from rules.c.commentmanager import CommentManager
    from rules.c.colourmanager import ColourManager
    from rules.c.whitespacemanager import WhiteSpaceManager
    from rules.c.saveloadmanager import SaveLoadManager
    from rules.c.runmanager import RunManager
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
    from .rules.c.commentmanager import CommentManager
    from .rules.c.colourmanager import ColourManager
    from .rules.c.whitespacemanager import WhiteSpaceManager
    from .rules.c.saveloadmanager import SaveLoadManager
    from .rules.c.runmanager import RunManager


class CPlugin(AllPlugin):
    __slots__ = ()
    DEFAULT_CODE:str = '#include <stdio.h>\n\nint main(){\n    // comment\n    printf("Hello, World!\\n");\n    return 0;\n}'

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
        return filepath.endswith(".c") or \
               filepath.endswith(".h")