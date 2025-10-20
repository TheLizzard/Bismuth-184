from __future__ import annotations
import tkinter as tk

from .baseplugin import BasePlugin
from .common_rules import COMMON_RULES
from .rules.colourmanager import ColourManager
from .rules.all.bracketmanager import BracketManager
from .rules.saveloadmanager import SaveLoadManager
from .rules.whitespacemanager import WhiteSpaceManager


class BasicPlugin(BasePlugin):
    __slots__ = ()

    def __init__(self, *args:tuple) -> BasicPlugin:
        rules:list[Rule] = [
                             ColourManager,
                             BracketManager,
                             SaveLoadManager,
                             WhiteSpaceManager,
                           ]
        super().__init__(*args, rules+COMMON_RULES)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        return True
