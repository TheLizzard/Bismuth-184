from __future__ import annotations
from idlelib.colorizer import make_pat
import re

from ..colourmanager import ColourManager as BaseColourManager
from ..colourmanager import ColourConfig as BaseColourConfig

"""
from idlelib.colorizer import matched_named_groups
from idlelib.colorizer import any as idleany
import builtins
import keyword
"""


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self) -> ColourConfig:
        super().__init__()
        super().update({
                         "comment":    dict(foreground="red"),
                         "keyword":    dict(foreground="orange"),
                         "builtin":    dict(foreground="#ff75ff"),
                         "string":     dict(foreground="lime"),
                         "definition": dict(foreground="cyan"),
                       })


class ColourManager(BaseColourManager):
    __slots__ = ()

    def init_colorizer(self) -> None:
        self.colorizer.tagdefs:dict[str,str] = ColourConfig()
        self.colorizer.idprog = re.compile(r"\s+(\w+)")
        self.colorizer.prog = make_pat()

    def attach(self) -> None:
        super().attach()
        self.init_colorizer()
        self.colorizer.config_colors()
        self.turnon_colorizer()
        self.colorizer.notify_range("1.0", "end")

    def detach(self) -> None:
        super().detach()
        self.turnoff_colorizer()
        self.colorizer.removecolors()

    def turnon_colorizer(self) -> None:
        if self.colorizer.colorizer_on:
            return None
        self.colorizer.toggle_colorize_event()

    def turnoff_colorizer(self) -> None:
        self.colorizer.close()

    """
    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        if on == "focusout":
            self.turnoff_colorizer()
        elif on == "focusin":
            self.turnon_colorizer()
        return False
    """