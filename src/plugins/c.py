from __future__ import annotations
import tkinter as tk
import os

from .baseplugin import BasePlugin
from .common_rules import COMMON_RULES
from .rules.c.runmanager import RunManager
from .rules.c.colourmanager import ColourManager
from .rules.c.commentmanager import CommentManager
from .rules.c.saveloadmanager import SaveLoadManager
from .rules.c.whitespacemanager import WhiteSpaceManager


class CPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = '#include <stdio.h>\n\n\nint main() {\n    // Comment\n    puts("Hello, World!");\n    return 0;\n}'

    def __init__(self, *args:tuple) -> CPlugin:
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
