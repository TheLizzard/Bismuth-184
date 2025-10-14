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


def isfloat(data:str) -> bool:
    try:
        float(data)
        return True
    except ValueError:
        return False


class ColourConfig(BaseColourConfig):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "comment":           dict(foreground="red"),
                           "keyword":           dict(foreground="orange"),
                           "builtin":           dict(foreground="#ff75ff"),
                           "string":            dict(foreground="lime"),
                           "definition":        dict(foreground="cyan"),
                           "f-string-format":   dict(foreground="#c0c0c0"),
                           # "identifier":        dict(foreground="#b0ffff"),
                           # "number":            dict(foreground="#c0c0c0"),
                           "decorator":        dict(foreground="#ff75ff"),
                           "type-annotation":  dict(foreground="#c0c0c0"),
                           **kwargs
                        })


# To speed up parsing, only check for these if we need to
config:dict[str:dict[str:str]] = ColourConfig()
CHECK_TYPE_ANNOTATIONS:bool = "type-annotation" in config
CHECK_IDENTIFIERS:bool = "identifier" in config
CHECK_DECORATORS:bool = "decorator" in config
CHECK_NUMBERS:bool = "number" in config
CHECK_COLONS:bool = True


class Parser(BaseParser):
    __slots__ = "keywords", "builtins", "string_prefixes"

    def __init__(self) -> Parser:
        super().__init__(str.isidentifier)
        self.keywords:set[str] = set(keyword.kwlist)
        self.builtins:set[str] = set()
        for name in dir(builtins):
            if name.startswith("_"): continue
            if name in self.keywords: continue
            self.builtins.add(name)
        self.string_prefixes:set[str] = {"r","u","f","t","b",
                                         "fr","rf","tr","rt","br","rb"}

    def read(self) -> Iterable[TokenTypePair]:
        while True:
            token:Token = self.peek_token()
            # print("in:", (token,))
            if not token: break
            # Keywords
            if token in self.keywords:
                yield self.read_token(), "keyword"
                if token in ("def", "class"): # def ···
                    yield self.read_join_spaces(" \t"), "" # Eat spaces
                    if self.isidentifier(self.peek_token()):
                        yield self.read_token(), "definition"
                elif token == "lambda": # lambda···: (needed for f-strings)
                    for token, tokentype in self.read():
                        if (token == ":") and (tokentype != "keyword"):
                            yield ":", "keyword"
                            break
                        yield token, tokentype
                        # lambda's colon must be on the same line
                        if token == "\n": break
            # Builtins
            elif (self.seen_text[-1:] not in set(".'\"\\#")) and \
                                                  (token in self.builtins):
                yield self.read_token(), "builtin"
            # Decorators
            elif CHECK_DECORATORS and (token == "@"):
                yield from self.read_decorator()
            # Colon as keyword
            elif CHECK_COLONS and (token == "{"):
                yield self.read_token(), ""
                brackets:int = 1
                for token, tokentype in self.read():
                    if (token == ":") and (tokentype != "type-annotation"):
                        tokentype:TokenType = "dict-colon"
                    yield token, tokentype
                    if token == "{":
                        brackets += 1
                    elif token == "}":
                        brackets -= 1
                        if brackets == 0: break
            elif CHECK_COLONS and (token == ":"):
                yield self.read_token(), "keyword"
            # Types annotations
            elif CHECK_TYPE_ANNOTATIONS and (token == "\n"):
                yield self.read_token(), ""
                # TODO
            # Comment
            elif token == "#":
                token:Token = self.read_token() # Read the "#"
                while True:
                    new_token:Token = self.read_token()
                    # Newline is not part of the comment
                    if new_token == "\n":
                        yield token, "comment"
                        yield "\n", ""
                        break
                    token += new_token
            # Prefix (might be with string/just an identifier)
            elif token.lower() in self.string_prefixes:
                token:Token = self.read_token() # Read the string prefix
                new_token:Token = self.peek_token()
                if new_token and (new_token in "'\""):
                    yield from self.read_string(token)
                else:
                    yield token, "identifier"
            # Strings without a prefix
            elif token in "'\"":
                yield from self.read_string() # Read the string
            # Match soft-keyword (MATCH_SOFTKW)
            elif token == "match":
                if not self.seen_text.rstrip(" \t").endswith("\n"):
                    yield self.read_token(), "identifier"
                else:
                    token:Token = self.read_token() # `match`
                    spaces:Token = self.read_join_spaces(" \t")
                    new_token:Token = self.peek_token()
                    if new_token in ":,;=^&|@~)]}":
                        yield token, "identifier"
                        yield spaces, ""
                    elif new_token in self.keywords: # `match def`
                        yield token, "identifier"
                        yield spaces, ""
                    else:
                        yield token, "keyword"
                        yield spaces, ""
            # Case soft keyword
            elif token == "case":
                if not self.seen_text.rstrip(" \t").endswith("\n"):
                    yield self.read_token(), "identifier"
                else:
                    token:Token = self.read_token() # `case`
                    spaces:Token = self.read_join_spaces(" \t")
                    new_token:Token = self.peek_token()
                    if new_token in ":,;=^&|@~)]}":
                        yield token, "identifier"
                        yield spaces, ""
                    elif new_token in self.keywords: # `case def`
                        yield token, "identifier"
                        yield spaces, ""
                    elif new_token == "_": # `case _`
                        new_token:Token = self.read_token()
                        yield token, "keyword"
                        yield spaces, ""
                        yield new_token, "keyword"
                    else:
                        yield token, "keyword"
                        yield spaces, ""
            # Identifiers
            elif CHECK_IDENTIFIERS and self.isidentifier(token):
                yield self.read_token(), "identifier"
            # Numbers
            elif CHECK_NUMBERS and isfloat(token):
                yield self.read_token(), "number"
            # Default
            else:
                yield self.read_token(), ""

    def read_string(self, prefix:Token="") -> Iterable[TokenTypePair]:
        fstring:bool = "f" in prefix
        single:Token = self.read_token()
        output:Token = prefix + single
        triple:bool = False
        # Check for ""/"""···
        if self.peek_token() == single:
            output += self.read_token()
            if self.peek_token() != single:
                yield output, "string"
                return
            output += self.read_token()
            triple:bool = True
        # Actual string reading loop
        while True:
            token:Token = self.read_token()
            output += token
            # No data left => return
            if not token:
                yield output, "string"
                return
            # Newlines aren't special if triple quotes
            elif (token == "\n") and (not triple):
                yield output[:-1], "string" # Newline not part of string
                yield "\n", ""
                return
            # Slash-Character (the character might be a newline)
            elif token == "\\":
                output += self.read_token() # Read the token after the \
            # On string-closing
            elif token == single:
                if not triple:
                    yield output, "string"
                    return
                if self.peek_token() == single:
                    output += self.read_token()
                    if self.peek_token() == single:
                        output += self.read_token()
                        yield output, "string"
                        return
            # F-string code
            elif (token == "{") and fstring:
                if self.peek_token() == "{":
                    output += self.read_token()
                    continue
                # Flush the string so far and reset it
                yield output[:-1], "string"
                yield output[-1:], "string" # f-string-open
                output:Token = ""
                # Actual f-string recursive call
                override_tokentype:TokenType = ""
                if not FSTRINGS_COLOURED:
                    override_tokentype:TokenType = "string"
                depth:int = 1
                for token, tokentype in self.read():
                    # Open/close bracket
                    if (token == "}") and (tokentype != "string"):
                        depth -= 1
                        if depth == 0:
                            yield token, "string" # f-string-close
                            break
                    if (token == "{") and (tokentype != "string"):
                        depth += 1
                    # Lambdas and ":" f-string formatting
                    elif (token == ":") and (tokentype != "keyword"):
                        override_tokentype:TokenType = "f-string-format"
                    if override_tokentype:
                        tokentype:TokenType = override_tokentype
                    # Change the token back to a string
                    yield token, tokentype

    def read_decorator(self) -> Iterable[TokenTypePair]:
        yield self.read_token(), "decorator" # "@"
        for token, tokentype in self.read():
            if token == "\n":
                yield "\n", ""
                break
            if (not tokentype) or (tokentype == "identifier"):
                tokentype:TokenType = "decorator"
            yield token, tokentype


class ColourManager(BaseColourManager):
    __slots__ = ()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig()
        self.idprog = re.compile(r"\s+(\w+)")
        self.prog = Regex(Parser())
        # self.prog = make_pat()


FSTRINGS_COLOURED:bool = False