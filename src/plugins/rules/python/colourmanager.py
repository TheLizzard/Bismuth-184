from __future__ import annotations
from idlelib.colorizer import any as idleany
import builtins
import keyword
import re

from ..colourmanager import ColourManager as BaseColourManager
from ..colourmanager import ColourConfig as BaseColourConfig


def make_pat():
    kw = r"\b" + idleany("KEYWORD", keyword.kwlist) + r"\b"
    match_softkw = (
        r"^[ \t]*" +  # at beginning of line + possible indentation
        r"(?P<MATCH_SOFTKW>match)\b" +
        r"(?![ \t]*(?:" + "|".join([  # not followed by ...
            r"[:,;=^&|@~)\]}]",  # a character which means it can't be a
                                 # pattern-matching statement
            r"\b(?:" + r"|".join(keyword.kwlist) + r")\b",  # a keyword
        ]) +
        r"))"
    )
    case_default = (
        r"^[ \t]*" +  # at beginning of line + possible indentation
        r"(?P<CASE_SOFTKW>case)" +
        r"[ \t]+(?P<CASE_DEFAULT_UNDERSCORE>_\b)"
    )
    case_softkw_and_pattern = (
        r"^[ \t]*" +  # at beginning of line + possible indentation
        r"(?P<CASE_SOFTKW2>case)\b" +
        r"(?![ \t]*(?:" + "|".join([  # not followed by ...
            r"_\b",  # a lone underscore
            r"[:,;=^&|@~)\]}]",  # a character which means it can't be a
                                 # pattern-matching case
            r"\b(?:" + r"|".join(keyword.kwlist) + r")\b",  # a keyword
        ]) +
        r"))"
    )
    builtinlist = [str(name) for name in dir(builtins)
                   if not name.startswith('_') and
                   name not in keyword.kwlist]
    builtin = r"([^.'\"\\#]\b|^)" + idleany("BUILTIN", builtinlist) + r"\b"
    comment = idleany("COMMENT", [r"#[^\n]*"])
    prestring = r"(?i:r|u|f|fr|rf|b|br|rb)?"
    sqstring = prestring + r"'[^'\\\n]*(\\.[^'\\\n]*)*(?:'|\n|$)"
    dqstring = prestring + r'"[^"\\\n]*(\\.[^"\\\n]*)*(?:"|\n|$)'
    sq3string = prestring + r"'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(?:(''')|\n|$)"
    dq3string = prestring + r'"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(?:(""")|\n|$)'
    string = idleany("STRING", (sq3string, dq3string, sqstring, dqstring))
    reg = "|".join((builtin, comment, string, kw, match_softkw, case_default,
                    case_softkw_and_pattern, idleany("SYNC", [r"\n"])))
    return re.compile(reg, re.DOTALL|re.MULTILINE)


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "comment":    dict(foreground="red"),
                           "keyword":    dict(foreground="orange"),
                           "builtin":    dict(foreground="#ff75ff"),
                           "string":     dict(foreground="lime"),
                           "definition": dict(foreground="cyan"),
                           **kwargs
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