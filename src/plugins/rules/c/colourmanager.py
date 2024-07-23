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
                           "iostream":   dict(foreground="#ff75ff"),
                           "string":     dict(foreground="lime"),
                           "definition": dict(foreground="cyan"), # parial use
                           "include":    dict(foreground="cyan"),
                           "comment":    dict(foreground="red"),
                           **kwargs
                        })


def get_iostream() -> Iterable[str]:
    return {
             "clearerr", "clrmemf", "fclose", "fdelrec", "feof", "ferror",
             "fflush", "fgetc", "fgetpos", "fgets", "fldata", "flocate",
             "fprintf", "fputc", "fputs", "fread", "freopen", "fscanf", "fseek",
             "fseeko", "fsetpos", "ftell", "ftello", "fupdate", "fwrite",
             "getchar", "gets", "perror", "printf", "putc", "putchar", "puts",
             "remove", "rename", "rewind", "scanf", "setbuf", "setvbuf",
             "sprintf", "sscanf", "svc99", "tmpfile", "tmpnam", "ungetc",
             "vfprintf", "vprintf", "vsprintf", "fopen", "getc",
             "EOF", "malloc", "calloc", "realloc", "free", "BUFSIZ",
             "STDERR_FILENO", "STDOUT_FILENO", "STDIN_FILENO", "stderr",
             "stdout", "stdin",
           }

def get_keywords() -> Iterable[str]:
    return {
             "auto", "bool", "break", "case", "char", "const", "continue",
             "default", "do", "double", "else", "enum", "extern", "float",
             "for", "goto", "if", "inline", "int", "long", "NULL", "register",
             "return", "short", "signed", "sizeof", "static", "struct",
             "switch", "typedef", "union", "unsigned", "void", "volatile",
             "while", "restrict",
           }

def make_pat() -> re.compile:
    kw = r"\b" + idleany("keyword", get_keywords()) + r"\b"

    iostream = r"([^.'\"\\#]\b|^)" + idleany("iostream", get_iostream()) + r"\b"

    include = idleany("include", [r"#(include *|(?:\\\n|[^\n])*?(?=/(?:/|\*)|\n|$))"])

    multiline_comment = r"/\*[^\*]*((\*(?!/))[^\*]*)*(\*/)?"
    comment = idleany("comment", [r"//[^\n]*", multiline_comment])

    sstring = r"'[^'\\\n]*(\\.[^'\\\n]*)*(?:'|\n|$)"
    dstring = r'"[^"\\\n]*(\\.[^"\\\n]*)*(?:"|\n|$)'
    includestr = '(?<=include )\<[^\n>]*>'
    string = idleany("string", [sstring, dstring, includestr])

    reg:str = kw + "|" + iostream + "|" + comment + "|" + include + "|" + \
              string + "|" + idleany("SYNC", [r"\n"])

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