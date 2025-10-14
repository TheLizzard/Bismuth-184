from __future__ import annotations
from idlelib.colorizer import any as idleany
import re

from ..colourmanager import ColourManager as BaseColourManager
from ..colourmanager import ColourConfig as BaseColourConfig


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "comment":      dict(foreground="red"),
                           "keyword":      dict(foreground="orange"),
                           "builtins":     dict(foreground="#ff75ff"),
                           "string":       dict(foreground="lime"),
                           "definition":   dict(foreground="cyan"),
                           "preprocessor": dict(foreground="cyan"),
                           **kwargs
                        })


def get_builtins() -> Iterable[str]:
    # At some point, I should prob put all of these in a file
    #   that gets reloaded every 1-2 min.
    c_funcs =[
               "open", "close", "flock", "assert", "getchar", "srand", "time",
               "rand",
             ]
    stdlib = [
               "cin", "cout", "cerr", "clog", "wcin", "wcout", "wcerr", "wclog",
               "printf", "malloc", "free", "calloc", "realloc", "alloca",
               "puts", "strlen", "strcpy", "string", "endl", "vector",
               "tuple", "tie", "countr_zero", "to_string", "rotl", "rotr",
               "shuffle", "begin", "end", "swap", "rand",
               "time_t", "upper_bound", "hash", "sqrt", "tan", "sin", "cos",
               "atan", "acos", "asin", "unordered_set", "unordered_map",
               "bitset", "min", "max", "find", "pair", "copy", "move",
               "memcpy", "isdigit", "pow", "isnan", "isinf", "tolower",
               "toupper", "wstring", "accumulate", "wstring_convert",
               "codecvt_utf8", "codecvt_utf8_utf16", "numeric_limits",
               "make_pair", "exp", "views", "views::chunk", "ranges",
               "ranges::view", "mutex", "ref", "thread", "this_thread",
               "this_thread::sleep_for", "chrono::milliseconds", "chrono",
               "thread::hardware_concurrency", "reverse", "chrono::seconds",
               "chrono::high_resolution_clock", "chrono::duration_cast",
               "chrono::high_resolution_clock::now", "from_chars", "getline",
               "errc", "errc::invalid_argument", "errc::result_out_of_range",
               "errc::broken_pipe", "filesystem", "filesystem::is_directory",
               "filesystem::exists", "filesystem::create_directory",
               "string::npos", "optional", "make_optional", "nullopt",
               "ranges::find", "uniform_int_distribution", "mt19937",
               "uniform_real_distribution", "random_device", "fixed",
               "setprecision", "get", "make_tuple", "bit_cast", "array",
               "abs", "all_of", "any_of", "none_of", "distance", "round",
               "chrono::steady_clock", "chrono::steady_clock::now",
               "this_thread::sleep_until", "chrono::duration",
               "ostringstream", "istringstream", "clamp", "stof",
               "fmod", "numbers", "numbers::e", "numbers::pi", "exit",
               "atan2", "signbit", "forward", "bind", "function", "deque",
               "aligned_alloc", "fill_n", "memset", "skipws", "noskipws",
               "unique_ptr", "shared_ptr", "make_unique", "make_shared",
               "div",
               # Type stuff
               "is_integral", "is_integral_v", "is_unsigned", "is_unsigned_v",
               "enable_if_t", "integral", "is_same_v", "conditional_t",
               "is_floating_point", "is_floating_point_v", "remove_reference",
               "true_type", "false_type",
               # IO/Streams
               "istreambuf_iterator", "fstream", "ifstream", "ofstream",
               "ios", "ios::binary", "ios::out", "ios::in", "stringstream",
               "hex", "setfill", "setw", "flush", "ostream", "istream",
               "uppercase", "dec", "ios_base::end", "ios_base",
               "ios_base::beg",
               # Exceptions
               "runtime_error", "invalid_argument",
             ] + c_funcs
    stdlib.sort(key=lambda s: -len(s)) # Longest first
    return [f"std::{builtin}" for builtin in stdlib] + ["std::"] + c_funcs

def get_keywords() -> Iterable[str]:
    return [
             "asm", "else", "new", "this", "auto", "enum", "operator",
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
             "size_t", "constexpr", "static_assert", "nullptr", "not",
             "override", "thread_local",
             # C++20 specific type stuff I have no idea how to use
             "concept", "requires",
           ]

def idleany(name:str, alternates:list[str]) -> str:
    return f"(?P<{name}>{'|'.join(alternates)})"

def make_pat() -> re.compile:
    kw = r"\b" + idleany("keyword", get_keywords()) + r"\b"

    # notlookbehind("::", "->", "//", ".", "#", ···) is equivalent to
    # noncapture(notlookbehind("::", "->", "//"), notlookbehind(".", "#", ···))
    builtins = r"((?:(?<!::|\->|//)(?<!\.|'|\"|#))\b|^)" + \
               idleany("builtins", get_builtins()) + r"\b"

    # Oh God. I am on my 4rd iteration of this regex...
    preprocessor = idleany("preprocessor",
                           [r"#(include|[^\n]*?(?=//|/\*|\n|$))"])
    preprocessor = idleany("preprocessor",
                           [r"#(include *|(?:\\\n|[^\n])*?(?=/(?:/|\*)|\n|$))"])
    preprocessor = idleany("preprocessor",
                        [r"#(?:include *|(?:[^\n]*?\\\n)*[^\n]*?(?=//|/\*|$))"])

    multiline_comment = r"/\*[^\*]*((\*(?!/))[^\*]*)*(\*/)?"
    comment = idleany("comment", [r"//[^\n]*", multiline_comment])

    strprefix = r"(?:L)?"
    sstring = strprefix + r"'[^'\\\n]*(\\.[^'\\\n]*)*(?:'|\n|$)"
    dstring = strprefix + r'"[^"\\\n]*(\\.[^"\\\n]*)*(?:"|\n|$)'
    includestr = r'(?<=include )\<[^\n>]*>'
    string = idleany("string", [sstring, dstring, includestr])

    reg = kw + "|" + preprocessor + "|" + string + "|" + comment + "|" + \
          builtins + "|" + idleany("SYNC", [r"\n"])

    return re.compile(reg, re.M|re.S)


class ColourManager(BaseColourManager):
    __slots__ = ()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig()
        self.idprog = re.compile(r"\s+(\w+)")
        self.prog = make_pat()