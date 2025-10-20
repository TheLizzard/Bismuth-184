from __future__ import annotations
from idlelib.colorizer import any as idleany
import re

from ..colourmanager import ColourManager as BaseColourManager
from ..colourmanager import ColourConfig as BaseColourConfig


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "keyword":    dict(foreground="orange"),
                           "builtins":   dict(foreground="#ff75ff"),
                           "string":     dict(foreground="lime"),
                           "definition": dict(foreground="cyan"), # parial use
                           "include":    dict(foreground="cyan"),
                           "comment":    dict(foreground="red"),
                           **kwargs
                        })


def get_builtins() -> Iterable[str]:
    return {
             "clearerr", "clrmemf", "fclose", "fdelrec", "feof", "ferror",
             "fflush", "fgetc", "fgetpos", "fgets", "fldata", "flocate",
             "fprintf", "fputc", "fputs", "fread", "freopen", "fscanf", "fseek",
             "fseeko", "fsetpos", "ftell", "ftello", "fupdate", "fwrite",
             "getchar", "gets", "perror", "printf", "putc", "putchar", "puts",
             "remove", "rename", "rewind", "scanf", "setbuf", "setvbuf",
             "sprintf", "sscanf", "svc99", "tmpfile", "tmpnam", "ungetc",
             "vfprintf", "vprintf", "vsprintf", "fopen", "getc",
             "EOF", "malloc", "calloc", "realloc", "alloca", "free", "BUFSIZ",
             "STDERR_FILENO", "STDOUT_FILENO", "STDIN_FILENO", "stderr",
             "stdout", "stdin", "time", "srand", "memcpy", "tolower", "strcmp",
           }

def get_keywords() -> Iterable[str]:
    return {
             "auto", "bool", "break", "case", "char", "const", "continue",
             "default", "do", "double", "else", "enum", "extern", "float",
             "for", "goto", "if", "inline", "int", "long", "NULL", "register",
             "return", "short", "signed", "sizeof", "static", "struct",
             "switch", "typedef", "union", "unsigned", "void", "volatile",
             "while", "restrict", "true", "false",
             "uint8_t", "uint16_t", "uint32_t", "uint64_t", "int8_t", "int16_t",
             "int32_t", "int64_t", "__uint128_t", "size_t",
           }

def make_pat() -> re.compile:
    kw = r"\b" + idleany("keyword", get_keywords()) + r"\b"

    iostream = r"([^.'\"\\#]\b|^)" + idleany("builtins", get_builtins()) + r"\b"

    include = idleany("include", [r"#(include *|(?:\\\n|[^\n])*?(?=/(?:/|\*)|\n|$))"])

    multiline_comment = r"/\*[^\*]*((\*(?!/))[^\*]*)*(\*/)?"
    comment = idleany("comment", [r"//[^\n]*", multiline_comment])

    sstring = r"'[^'\\\n]*(\\.[^'\\\n]*)*(?:'|\n|$)"
    dstring = r'"[^"\\\n]*(\\.[^"\\\n]*)*(?:"|\n|$)'
    includestr = '(?<=include )\\<[^\n>]*>'
    string = idleany("string", [sstring, dstring, includestr])

    reg:str = comment + "|" + include + "|" + string + "|" + kw + "|" + \
              iostream + "|" + idleany("SYNC", [r"\n"])

    return re.compile(reg, re.M|re.S)


class ColourManager(BaseColourManager):
    __slots__ = ()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig()
        self.idprog = re.compile(r"\s+(\w+)")
        self.prog = make_pat()
