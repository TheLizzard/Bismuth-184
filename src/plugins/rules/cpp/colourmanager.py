from __future__ import annotations
from idlelib.colorizer import any as idleany
import re

from ..colourmanager import ColourManager as BaseColourManager
from ..colourmanager import ColourConfig as BaseColourConfig


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "comment":    dict(foreground="red"),
                           "keyword":    dict(foreground="orange"),
                           "builtins":   dict(foreground="#ff75ff"),
                           "string":     dict(foreground="lime"),
                           "definition": dict(foreground="cyan"), # parial use
                           "include":    dict(foreground="cyan"),
                           **kwargs
                        })


def get_builtins() -> Iterable[str]:
    main = ["cin", "cout", "cerr", "clog", "wcin", "wcout", "wcerr", "wclog",
            "printf", "malloc", "free", "calloc", "realloc", "alloca",
            "puts", "strlen", "strcpy", "string", "endl", "vector",
            "tuple", "tie", "countr_zero", "to_string", "rotl", "rotr",
            "shuffle", "begin", "end", "swap", "rand", "srand", "time",
            "time_t", "upper_bound", "hash", "sqrt", "tan", "sin", "cos",
            "unordered_set", "unordered_map", "bitset"]
    return main + [f"std::{builtin}" for builtin in main] + ["std::"]

def get_keywords() -> Iterable[str]:
    return ["asm", "else", "new", "this", "auto", "enum", "operator",
            "throw", "bool", "explicit", "private", "true", "break",
            "export", "protected", "try", "case", "extern", "public",
            "typedef", "catch", "false", "register", "typeid", "char",
            "float", "reinterpret_cast", "typename", "class", "for",
            "return", "union", "const", "friend", "short", "unsigned",
            "const_cast", "goto", "signed", "using", "continue", "if",
            "sizeof", "virtual", "default", "inline", "static", "void",
            "delete", "int", "static_cast", "volatile", "do", "long",
            "struct", "wchar_t", "double", "mutable", "switch", "while",
            "dynamic_cast", "namespace", "template", "NULL", "noexcept",
            "uint8_t", "uint16_t", "uint32_t", "uint64_t", "__uint128_t",
            "int8_t", "int16_t", "int32_t", "int64_t", "__int128",
            "size_t", "constexpr", "static_assert"]

def make_pat() -> re.compile:
    kw = r"\b" + idleany("keyword", get_keywords()) + r"\b"

    iostream = r"([^.'\"\\#]\b|^)" + idleany("builtins", get_builtins()) + r"\b"

    include = idleany("include", [r"#(include|[^\n]*?(?=//|/\*|\n|$))"])
    include = idleany("include", [r"#(include *|(?:\\\n|[^\n])*?(?=/(?:/|\*)|\n|$))"])

    multiline_comment = r"/\*[^\*]*((\*(?!/))[^\*]*)*(\*/)?"
    comment = idleany("comment", [r"//[^\n]*", multiline_comment])

    sstring = r"'[^'\\\n]*(\\.[^'\\\n]*)*(?:'|\n|$)"
    dstring = r'"[^"\\\n]*(\\.[^"\\\n]*)*(?:"|\n|$)'
    includestr = '(?<=include )\<[^\n>]*>'
    string = idleany("string", [sstring, dstring, includestr])

    reg:str = kw + "|" + comment + "|" + include + "|" + string + "|" + \
              iostream + "|" + idleany("SYNC", [r"\n"])

    return re.compile(reg, re.M|re.S)


class ColourManager(BaseColourManager):
    __slots__ = ()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig()
        self.idprog = re.compile(r"\s+(\w+)")
        self.prog = make_pat()