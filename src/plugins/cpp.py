from __future__ import annotations
import tkinter as tk
import os

from .baseplugin import BasePlugin
from .common_rules import COMMON_RULES
from .rules.cpp.runmanager import RunManager
from .rules.cpp.colourmanager import ColourManager
from .rules.cpp.commentmanager import CommentManager
from .rules.cpp.saveloadmanager import SaveLoadManager
from .rules.cpp.stdinsertmanager import StdInsertManager
from .rules.cpp.whitespacemanager import WhiteSpaceManager


class CppPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = '#include <iostream>\n\nint main() {\n    // comment\n    std::cout << "Hello, world!" << std::endl;\n    return 0;\n}'

    def __init__(self, *args:tuple) -> CppPlugin:
        rules:list[Rule] = [
                             RunManager,
                             ColourManager,
                             CommentManager,
                             SaveLoadManager,
                             StdInsertManager,
                             WhiteSpaceManager,
                           ]
        super().__init__(*args, rules+COMMON_RULES)

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
