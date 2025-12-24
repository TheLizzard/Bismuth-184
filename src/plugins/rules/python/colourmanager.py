from __future__ import annotations
from idlelib.colorizer import make_pat
import builtins
import keyword
import re

try:
    from ..colourmanager import ColourManager as BaseColourManager
    from ..colourmanager import ColourConfig as BaseColourConfig
    from ..colourmanager import Regex, Parser as BaseParser
except:
    from colourmanager import ColourManager as BaseColourManager
    from colourmanager import ColourConfig as BaseColourConfig
    from colourmanager import Regex, Parser as BaseParser


NUMBER_REGEX:re.Pattern = re.compile((
    r"(?:"
        r"0|" # The number zero or
        r"(?:"
            r"[1-9]" # Any non-zero integer
            r"\d*"   # Followed by any number of integers
        r")"
    r")"
    r"(?:" # Followed by 0 or 1 fractional parts
        r"\."  # A fractional part starts with a "."
        r"\d*" # Followed by any number of integers
    r")?"
    r"(?:" # Followed by 0 or 1 exponential parts
        r"[eE]" # A fractional part starts with an "e"
        r"\d*"  # Followed by any number of integers
    r")?"
))
VALID_NUMBER_ENDERS:set[str] = set("0123456789.eE")


def isnumber(data:str) -> bool:
    if data[-1:] not in VALID_NUMBER_ENDERS: return False
    try:
        float(data)
        return True
    except:
        return False


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        light_cyan:str = "#b0ffff" # Check if it's too dark/bright
        purple:str = "#ff75ff" # Maybe a touch lighter? (check night-time)
        grey:str = "#a0a0a0" # Maybe something lighter (check night-time)
        super().__init__({
                           "comment":          dict(foreground="red"),
                           "keyword":          dict(foreground="orange"),
                           "builtin":          dict(foreground=purple),
                           "string":           dict(foreground="lime"),
                           "definition":       dict(foreground="cyan"),
                           "f-string-format":  dict(foreground=grey),
                           # "identifier":        dict(foreground=light_cyan),
                           # "number":            dict(foreground=grey),
                           "decorator":        dict(foreground=purple),
                           "type-annotation":  dict(foreground=grey),
                           "f-string-bracket": dict(foreground="yellow"),
                           "self":             dict(foreground=grey),
                           # "walrus-operator":  dict(foreground="white"),
                           # "type-annotation-arrow": dict(foreground=grey),
                           **kwargs
                        })


EXPR_KWS:set[str] = {"lambda", "if", "for", "else", "False", "True", "None",
                     "and", "or", "not", "await", "in", "is", "yield"}
CMD_KWS:set[str] = {"assert", "with", "async", "def", "class", "break",
                    "continue", "del", "elif", "try", "except", "finally",
                    "from", "import", "nonlocal", "global", "pass", "raise",
                    "return", "while", "for"}
KWS_WITH_COLON:set[str] = {"lambda", "while", "if", "for", "else", "def",
                           "class", "elif", "try", "except", "finally",
                           "with"}
NOT_AFTER_SOFT_KW:set[str] = set(":.,;=^&|@~)]}")
KDS_WITH_IMMEDIATE_COLON:set[str] = {"else", "finally", "try"}

SPACES:str = " \t"
STRING_TYPES:set[str] = {"string", "f-string-format", "f-string-bracket"}
TYPE_ANNOTATION_IGNORETYPES:set[str] = {"comment", "decorator"}
# TYPE_ANNOTATION_IGNORETYPES += STRING_TYPES
DECORATOR_IGNORETYPES:set[str] = {"keyword", "comment"} | STRING_TYPES


# To speed up parsing, only check for these if we need to
config:dict[str:dict[str:str]] = ColourConfig()
CHECK_FSTRING_BRACKETS:bool = "f-string-bracket" in config
CHECK_TYPE_ANNOTATIONS:bool = "type-annotation" in config
CHECK_FSTRING_FORMATS:bool = "f-string-format" in config
CHECK_IDENTIFIERS:bool = "identifier" in config
CHECK_DECORATORS:bool = "decorator" in config
CHECK_NUMBERS:bool = "number" in config


if (not CHECK_NUMBERS) and (not CHECK_IDENTIFIERS):
    # Faster to just call str.isdigit
    isnumber:Callable[str,bool] = str.isdigit

FSTRING_BARCKET_TOKENTYPE:str = "string"
if CHECK_FSTRING_BRACKETS:
    FSTRING_BARCKET_TOKENTYPE:str = "f-string-bracket"


KEYWORDS:set[str] = set(keyword.kwlist)
BUILTINS:set[str] = {i
                      for i in dir(builtins)
                      if (i not in KEYWORDS) and (not i.startswith("_"))
                    }

STRING_PREFIXES:set[str] = {"r","u","f","t","b",
                            "fr","rf","tr","rt","br","rb"}


""" # TODO
Exports tags:
    def/class   The identifier in a def/class statement respectively
    identifier  An indentifier used
    setident    An indentifier used in setting a variable

Aliases:
    def               definition (cyan)
    class             definition (cyan)
    identifier        none
    setident          none
    f-string-format   string
    f-string-bracket  string
"""

class Parser(BaseParser):
    __slots__ = ()

    def __init__(self) -> Parser:
        super().__init__(isidentifier=str.isidentifier, isnumber=isnumber)

    def read(self) -> None:
        token:Token = self.peek_token()
        if not token: return None
        # Keywords
        if token in KEYWORDS:
            self.set("keyword")
            # Def/Class definition identifier
            if token in ("def", "class"):
                self.skip_whitespaces(SPACES) # Eat spaces
                if self.isidentifier(self.peek_token()):
                    self.set(token)
                # Def type-annotations
                if CHECK_TYPE_ANNOTATIONS and (token == "def"):
                    self.read_def_type_annotation()
            # Keyword colon
            if CHECK_TYPE_ANNOTATIONS and (token in KWS_WITH_COLON):
                orig_keyword:Token = token
                # Shortcut for tokens that must be immediately followed by
                #   a colon
                if token in KDS_WITH_IMMEDIATE_COLON:
                    if self.peek_token() != ":":
                        return None
                # Search for the next colon or command keyword
                waiting_for:set[str] = {":","]","}",")","else","\n"} | CMD_KWS
                while True:
                    token:Token = self.read_wait_for(waiting_for)
                    if token == ":":
                        start:Location = self.tell()
                        self.skip()
                        if self.peek_token() == "=":
                            self.set("walrus-operator", start) # ":"
                            self.set("walrus-operator") # "="
                            continue # Continue looking for colon keyword
                        else:
                            self.set("keyword", start) # ":"
                    elif (orig_keyword == "if") and (token == "else"):
                        # Don't look for the colon for the "else"
                        self.set("keyword")
                    break # Command keyword so stop looking for ":"
        # Builtins
        elif token in BUILTINS:
            if self.curr_line_seen(respect_slashes=True)[-1:] == ".":
                self.set("identifier")
            else:
                self.set("builtin")
        # Decorators
        elif CHECK_DECORATORS and (token == "@"):
            self.set("decorator") # "@"
            self.read_wait_for({"\n"}, "decorator",
                               ignoretypes=DECORATOR_IGNORETYPES)
        # Colon as keyword
        elif CHECK_TYPE_ANNOTATIONS and (token in ("{", "[", "(")):
            open:str = token
            close:str = {"(":")", "[":"]", "{":"}"}[open]
            self.set("container-bracket")
            while True:
                waiting_for:set[str] = {close, "=", ",", ":"} | CMD_KWS
                token:Token = self.read_wait_for(waiting_for)
                if token == close:
                    self.set("container-bracket")
                    break
                elif token not in ("=", ",", ":"):
                    break
                self.skip()
        elif CHECK_TYPE_ANNOTATIONS and (token == ":"):
            start:Location = self.tell()
            self.skip()
            if self.peek_token() == "=": # Walrus operator
                self.set("walrus-operator", start) # ":"
                self.set("walrus-operator") # "="
            else: # Type annotation
                self.set("type-annotation", start) # ":"
                self.read_type_annotation({"\n","="})
        # Check for {...} so f-strings work properly
        elif (not CHECK_TYPE_ANNOTATIONS) and (token == "{"):
            self.skip()
            if self.read_wait_for("}") == "}":
                self.skip()
        # Comment
        elif token == "#":
            while self.peek_token() != "\n": # Newline not in comment
                self.set("comment")
        # Strings:
        elif token.lower() in STRING_PREFIXES:
            start:Location = self.tell()
            self.set("identifier") # Jump over the string prefix
            new_token:Token = self.peek_token()
            if new_token in "'\"":
                self.set("string", start) # String prefix
                self.read_string(token)
        elif token in "'\"":
            self.read_string()
        # Match soft-keyword (MATCH_SOFTKW)
        elif token == "match":
            if self.curr_line_seen(respect_slashes=True).rstrip(" \t"):
                self.set("identifier")
            else:
                start:Location = self.tell()
                self.skip() # `match` but we aren't sure if keyword
                self.skip_whitespaces(SPACES)
                new_token:Token = self.peek_token()
                if new_token in NOT_AFTER_SOFT_KW:
                    self.set("identifier", start)
                elif new_token in KEYWORDS: # match followed by a keyword
                    self.set("identifier", start)
                else:
                    self.set("keyword", start)
        # Case soft-keyword
        elif token == "case":
            if self.curr_line_seen(respect_slashes=True).rstrip(" \t"):
                self.set("identifier")
            else:
                start:Location = self.tell()
                self.skip() # `case` but we aren't sure if keyword
                self.skip_whitespaces(SPACES)
                new_token:Token = self.peek_token()
                if new_token in NOT_AFTER_SOFT_KW:
                    self.set("identifier", start)
                elif new_token in KEYWORDS: # case followed by a keyword
                    self.set("identifier", start)
                elif new_token == "_": # case <underscore>
                    self.set("keyword", start)
                    self.set("keyword") # "_"
                else:
                    self.set("keyword", start)
        # Identifiers
        elif CHECK_IDENTIFIERS and self.isidentifier(token):
            self.set("identifier")
        # Numbers
        elif CHECK_NUMBERS and isnumber(token):
            self.set("number") # Leading -/+ signs aren't part of the token
        # Line continuations
        elif token == "\\":
            self.skip() # Read the "\"
            token:Token = self.peek_token()
            if token == "\n":
                self.set("no-sync-backslash") # Read the "\n"
            elif token == "\\":
                self.set("backslash") # Read the next "\"
        # Default
        else:
            self.skip()

    def read_def_type_annotation(self) -> None:
        self.skip_whitespaces(SPACES)
        # Opening bracket
        if self.peek_token() != "(": return None
        self.skip() # "("
        # Self argument if it's there
        self.skip_whitespaces(SPACES)
        if self.peek_token() == "self":
            self.set("self")
        # Inside the brackets
        while True:
            token:Token = self.read_wait_for({")", ":"})
            if not token:
                return None
            elif token == ")":
                break
            elif token == ":":
                self.set("type-annotation") # Set ":" keyword=>type-annotation
                self.read_type_annotation({"\n",")","=",",",":"})
                if self.peek_token() == ":": self.skip()
            else:
                raise NotImplementedError("Unreachable")
        # Closing bracket
        if self.peek_token() != ")":
            return None
        self.skip() # ")"
        # "->" type annotation
        self.skip_whitespaces(SPACES)
        start:Location = self.tell()
        if self.peek_token() == "-":
            self.skip()
            if self.peek_token() == ">":
                self.set("type-annotation-arrow", start)
                self.set("type-annotation-arrow")
                self.skip_whitespaces(SPACES)
                # Return type annotation
                self.read_type_annotation({"\n",":"})

    def read_type_annotation(self, ending_tokens:set[Token]) -> None:
        """
        Read a type annotation and colour it accordingly
        """
        self.read_wait_for(ending_tokens | CMD_KWS, "type-annotation",
                           ignoretypes=TYPE_ANNOTATION_IGNORETYPES)

    def read_string(self, prefix:Token="") -> None:
        fstring:bool = "f" in prefix
        single:Token = self.peek_token()
        assert single in "'\"", "InternalError"
        self.set("string") # starting quote
        triple:bool = False
        # Check for empty string/triple quotes
        if self.peek_token() == single:
            self.set("string")
            if self.peek_token() != single: # "" => return
                return None
            self.set("string")
            triple:bool = True
        # Actual string reading loop
        while True:
            token:Token = self.peek_token()
            if not token: # No data left => return
                break
            elif (not triple) and (token == "\n"): # Newline if not triple
                break
            elif token == "\\": # Slash + character
                self.set("string") # "\"
                if fstring and (self.peek_token() in "{}"):
                    continue # Curly brackets cannot be escaped with a \
                self.set("string") # Token after the \ (might be \n)
            elif token == single: # String-closing
                self.set("string") # quote
                if not triple: break
                if self.peek_token() == single:
                    self.set("string")
                    if self.peek_token() == single:
                        self.set("string")
                        break
            elif fstring and (token == "{"): # F-strings
                fstring_start:Location = self.tell()
                self.set("string") # "{"
                if self.peek_token() == "{": # second "{"
                    self.set("string")
                    continue
                self.set(FSTRING_BARCKET_TOKENTYPE, fstring_start) # open
                # Actual f-string recursive call
                token:Token = self.read_wait_for({"}", ":"} | CMD_KWS)
                if token not in ("}", ":"):
                    if not FSTRINGS_COLOURED:
                        self.set_from("string", fstring_start+len("{"))
                    return None # Command keyword in f-string => return
                format_start:Location = self._check_format()
                if format_start is None:
                    if not FSTRINGS_COLOURED:
                        self.set_from("string", fstring_start+len("{"))
                    return None # Command keyword in f-string => return
                if not FSTRINGS_COLOURED:
                    self.set_from("string", fstring_start+len("{"))
                if self.peek_token() == "}":
                    self.set(FSTRING_BARCKET_TOKENTYPE) # close
            else: # Default
                self.set("string")

    def _check_format(self) -> Location|None:
        """
        Reads the formating part of f-strings. If there is a ":" part, it
          should be in `self.peek_token()`.

        format := (whitespaces + "=" + whitespaces)? +
                  ("!" + conversion)? +
                  (":" + format_spec)?
        conversion := "s" | "r" | "a"
        whitespaces := whitespace*
        whitespace := " " | "\t" | "\n" | "\f" | "\v"

        Technically `format_spec` should be recursive but I've never
          seen anyone use it and implementing it will be a pain

        https://docs.python.org/3/reference/lexical_analysis.html#f-strings
        """
        start:Location = self.tell()
        if self.peek_token() == ":":
            self.skip() # ":"
            if self.read_wait_for({"}"} | CMD_KWS) != "}":
                return None # Command keyword in f-string => return
        # Exclam
        prev_start:Location = self.prev_start(start)
        prev_token:Token = self.token_at(prev_start)
        if prev_token in ("s", "r", "a"):
            prev_prev_start:Location = self.prev_start(prev_start)
            if self.token_at(prev_prev_start) == "!":
                start:Location = prev_prev_start
        elif prev_token == "!": # unfinished conversion: {!}
            start:Location = prev_start
        # Equals
        new_start:Location = start
        while True: # Spaces after =
            new_start:Location = self.prev_start(new_start)
            if self.token_at(new_start).strip(" \t\n"):
                break
        if self.token_at(new_start) == "=":
            while True: # Spaces before =
                start:Location = new_start
                new_start:Location = self.prev_start(new_start)
                if self.token_at(start).strip(" \t\n"):
                    break
        self.set_from("f-string-format", start)
        return start


class ColourManager(BaseColourManager):
    __slots__ = ()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig()
        self.aliases:dict[str:str] = {
                                       "class": "definition",
                                       "def": "definition",
                                       "identifier": "none",
                                       "setident": "none",
                                       "f-string-format": "string",
                                       "f-string-bracket": "string",
                                     }
        if True:
            self.text.parser:Parser = Parser()
            self.prog = Regex(self.text.parser)
        else:
            self.prog = make_pat()

    def attach(self) -> None:
        super().attach()
        # Re-order tag colouring so that the correct tags are at the top
        self.text.tag_raise("f-string-bracket", "string")
        self.text.tag_raise("f-string-format", "string")
        self.text.tag_raise("definition", "class")
        self.text.tag_raise("definition", "def")


FSTRINGS_COLOURED:bool = True
