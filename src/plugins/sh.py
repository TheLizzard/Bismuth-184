from __future__ import annotations
import tkinter as tk

from .baseplugin import BasePlugin
from .common_rules import COMMON_RULES
from .rules.sh.runmanager import RunManager
from .rules.sh.colourmanager import ColourManager
from .rules.sh.commentmanager import CommentManager
from .rules.sh.saveloadmanager import SaveLoadManager
from .rules.sh.whitespacemanager import WhiteSpaceManager


class ShPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = '#!/bin/bash\nset -e\n\necho "Hello world"'

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
        # Check file extension
        if filepath.endswith(".sh") or filepath.endswith(".run"):
            return True
        # Check shebang
        try:
            with open(filepath, "r") as file:
                if (file.read(2) == "#!") and ("sh" in file.readline()):
                    return True
        except:
            pass
        return False