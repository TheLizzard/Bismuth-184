from __future__ import annotations
import tkinter as tk

from .baseplugin import BasePlugin
from .common_rules import COMMON_RULES
from .rules.java.runmanager import RunManager
from .rules.java.colourmanager import ColourManager
from .rules.java.commentmanager import CommentManager
from .rules.java.saveloadmanager import SaveLoadManager
from .rules.java.whitespacemanager import WhiteSpaceManager


class JavaPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = 'import java.util.Scanner;\n\npublic class Main{\n    public static void main(String[] args){\n        /* comment */\n        System.out.println("Hello World!"); // comment\n    }\n}'

    def __init__(self, *args:tuple) -> JavaPlugin:
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
        return filepath.endswith(".java")
