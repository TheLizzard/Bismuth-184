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
                           **kwargs
                        })


def get_builtins() -> Iterable[str]:
    return (
             "System.out.print", "System.err.print",
             "System.out.println", "System.err.println",
             "Sytem.out", "System.err", "System.in",
           ) + (
             "Throwable", "Exception", "CloneNotSupportedException",
             "InterruptedException", "ReflectiveOperationException",
             "ClassNotFoundException", "IllegalAccessException",
             "InstantiationException", "NoSuchFieldException",
             "NoSuchMethodException", "RuntimeException", "ArithmeticException",
             "ArrayStoreException", "ClassCastException",
             "EnumConstantNotPresentException", "IllegalArgumentException",
             "IllegalThreadStateException", "NumberFormatException",
             "IllegalCallerException", "IllegalMonitorStateException",
             "IllegalStateException", "IndexOutOfBoundsException",
             "ArrayIndexOutOfBoundsException",
             "StringIndexOutOfBoundsException", "LayerInstantiationException",
             "NegativeArraySizeException", "NullPointerException",
             "SecurityException", "TypeNotPresentException",
             "UnsupportedOperationException", "Error", "AssertionError",
             "LinkageError", "BootstrapMethodError", "ClassCircularityError",
             "ClassFormatError", "UnsupportedClassVersionError",
             "ExceptionInInitializerError", "IncompatibleClassChangeError",
             "AbstractMethodError", "IllegalAccessError", "InstantiationError",
             "NoSuchFieldError", "NoSuchMethodError", "NoClassDefFoundError",
             "UnsatisfiedLinkError", "VerifyError", "ThreadDeath",
             "VirtualMachineError", "InternalError", "OutOfMemoryError",
             "StackOverflowError", "UnknownError",
           ) + (
             "String", "Integer", "Float", "Boolean", "Byte", "Short",
             "Character", "Long", "Double",
             # "ArrayList", "HashSet", "HashMap",
           )

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
            "record", "null", "false", "true"}

def make_pat() -> re.compile:
    kw = r"\b" + idleany("keyword", get_keywords()) + r"\b"

    builtins = r"([^.'\"\\#]\b|^)" + idleany("builtins", get_builtins()) + r"\b"

    multiline_comment = r"/\*[^\*]*((\*(?!/))[^\*]*)*(\*/)?"
    comment = idleany("comment", [r"//[^\n]*", multiline_comment])

    sstring = r"'[^'\\\n]*(\\.[^'\\\n]*)*(?:'|\n|$)"
    dstring = r'"[^"\\\n]*(\\.[^"\\\n]*)*(?:"|\n|$)'
    string = idleany("string", [sstring, dstring])

    reg:str = kw + "|" + builtins + "|" + comment + "|" + \
              string + "|" + idleany("SYNC", [r"\n"])

    return re.compile(reg, re.M|re.S)


class ColourManager(BaseColourManager):
    __slots__ = ()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig()
        self.idprog = re.compile(r"\s+(\w+)")
        self.prog = make_pat()