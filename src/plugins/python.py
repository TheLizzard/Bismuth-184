from __future__ import annotations
import tkinter as tk

from .baseplugin import BasePlugin
from .common_rules import COMMON_RULES
from .rules.python.runmanager import RunManager
from .rules.python.colourmanager import ColourManager
from .rules.python.commentmanager import CommentManager
from .rules.python.saveloadmanager import SaveLoadManager
from .rules.python.whitespacemanager import WhiteSpaceManager


class PythonPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = 'import this\n\nprint("Hello world")'

    def __init__(self, *args:tuple) -> PythonPlugin:
        rules:list[Rule] = [
                             RunManager,
                             ColourManager,
                             CommentManager,
                             SaveLoadManager,
                             WhiteSpaceManager,
                           ]
        super().__init__(*args, rules+COMMON_RULES)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        if filepath is None:
            return False
        # Check if it's a .py file
        if filepath.endswith(".py"):
            return True
        # Check if there is a python shebang
        try:
            with open(filepath, "r") as file:
                if (file.read(2) == "#!") and ("python" in file.readline()):
                    return True
        except:
            pass
        return False