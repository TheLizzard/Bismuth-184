from __future__ import annotations
import tkinter as tk

from bettertk import BetterTk
from .baserule import Rule

from ..baseplugin import AllPlugin
from .undomanager import UndoManager
from .wrapmanager import WrapManager
from .colourmanager import ColourManager
from .selectmanager import SelectManager
from .shortcutmanager import RemoveShortcuts
from .clipboardmanager import ClipboardManager
from .whitespacemanager import WhiteSpaceManager

# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4



class MiniPlugin(AllPlugin):
    __slots__ = ()

    def __init__(self, text:tk.Text) -> PythonPlugin:
        rules:list[Rule] = [
                             WrapManager,
                             UndoManager,
                             ColourManager,
                             SelectManager,
                             ClipboardManager,
                             WhiteSpaceManager,
                             RemoveShortcuts,
                           ]
        super().__init__(text, rules)


class FindReplaceManager(Rule):
    __slots__ = "text", "window", "find", "replace", "regex", "matchcase", \
                "wholeword", "buttons", "shown", "geom"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> None:
        evs:tuple[str] = (
                           # Find
                           "<Control-F>", "<Control-f>",
                           # Replace
                           "<Control-R>", "<Control-r>",
                           "<Control-H>", "<Control-h>",
                         )
        super().__init__(plugin, text, evs)
        self.text:tk.Text = self.widget
        self.window:BetterTk = None
        self.geom:str = None

    def init(self) -> None:
        self.window:BetterTk = BetterTk(self.text)
        self.window.resizable(False, False)
        self.window.title("Find/Replace")
        self.window.topmost(True)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.buttons:list[tk.Button] = []
        self.replace:tk.Misc = None
        self.shown:bool = True

        self.find:tk.Misc = None
        self.regex:tk.Misc = None
        self.wholeword:tk.Misc = None
        self.matchcase:tk.Misc = None

    def __new__(Cls, plugin:BasePlugin, text:tk.Text, *args, **kwargs):
        self:FindReplaceManager = getattr(text, "findreplacemanager", None)
        if self is None:
            self:FindReplaceManager = super().__new__(Cls, *args, **kwargs)
            text.findreplacemanager:FindReplaceManager = self
        return self

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if event.state&SHIFT:
            return False
        return True

    def do(self, on:str) -> Break:
        if on == "control-f":
            self.open_find()
            return True
        if on in ("control-r", "control-h"):
            self.open_replace()
            return True
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def open_find(self) -> None:
        self.show()
        # Already setup correctly
        if self.replace is None:
            return None
        # Replace => Find
        else:
            self.replace.destroy()
            self.replace:tk.Misc = None
            for button in buttons:
                button.delstroy()
            buttons.clear()
        self.create_find_buttons()

    def open_replace(self) -> None:
        self.show()
        # Find => Replace
        if self.replace is None:
            self.create_replace_text()
            for button in buttons:
                button.delstroy()
            buttons.clear()
        self.create_replace_buttons()

    def create_find_buttons(self) -> None:
        ...

    def create_replace_buttons(self) -> None:
        ...

    def show(self) -> None:
        if self.window is None:
            self.init()
        if self.shown:
            return None
        self.window.deiconify()
        if self.geom is not None:
            self.window.geometry(self.geom)
        self.shown:bool = True

    def hide(self) -> None:
        if self.window is None:
            return None
        if not self.shown:
            return None
        geom:str = self.window.geometry()
        self.geom:str = geom[geom.index("+"):]
        self.window.withdraw()
        self.shown:bool = False
        self.text.focus_set()