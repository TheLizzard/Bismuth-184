from __future__ import annotations
from idlelib.colorizer import any as idleany
import re

from ..colourmanager import ColourManager as BaseColourManager
from ..colourmanager import ColourConfig as BaseColourConfig

"""
from idlelib.colorizer import matched_named_groups
import builtins
import keyword
"""


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "comment":    dict(foreground="red"),
                           "keyword":    dict(foreground="orange"),
                           "iostream":   dict(foreground="#ff75ff"),
                           "string":     dict(foreground="lime"),
                           "definition": dict(foreground="cyan"), # parial use
                           "include":    dict(foreground="cyan"),
                           **kwargs
                        })


def get_iostream() -> Iterable[str]:
    return ("System.out.print", "System.err.print",
            "System.out.println", "System.err.println",
            "Sytem.out", "System.err", "System.in")

def get_keywords() -> Iterable[str]:
    return {"abstract", "assert", "boolean", "break", "byte", "case", "catch",
            "char", "class", "continue", "const", "default", "do", "double",
            "else", "enum", "exports", "extends", "final", "finally", "float",
            "for", "goto", "if", "implements", "import", "instanceof", "int",
            "interface", "long", "module", "native", "new", "package",
            "private", "protected", "public", "requires", "return", "short",
            "static", "strictfp", "super", "switch", "synchronized", "this",
            "throw", "throws", "transient", "try", "var", "void", "volatile",
            "while",
            "record", "null", "false", "true",
            "String", "Integer", "Float", "Boolean", "Byte", "Short",
            "Character", "Long", "Double"}

def make_pat() -> re.compile:
    kw = r"\b" + idleany("keyword", get_keywords()) + r"\b"

    iostream = r"([^.'\"\\#]\b|^)" + idleany("iostream", get_iostream()) + r"\b"

    #include = idleany("include", [r"#[^\n]*"])

    multiline_comment = r"/\*[^\*]*((\*(?!/))[^\*]*)*(\*/)?"
    comment = idleany("comment", [r"//[^\n]*", multiline_comment])

    sstring = r"'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dstring = r'"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    string = idleany("string", [sstring, dstring])

    reg:str = kw + "|" + iostream + "|" + comment + "|" + \
              string + "|" + idleany("SYNC", [r"\n"])# + "|" + include

    return re.compile(reg, re.M|re.S)


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