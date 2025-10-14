from __future__ import annotations
from idlelib.colorizer import ColorDelegator
from io import StringIO
import tkinter as tk
import re

try:
    from .baserule import Rule
except ImportError:
    from baserule import Rule


class ColourConfig(dict):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "SYNC":  dict(),
                           "TODO":  dict(),
                           "error": dict(),
                           "hit":   dict(background="blue", foreground="white"),
                           **kwargs
                        })

KEYWORD_GROUPS:re.Pattern = re.compile(
    "|".join([
        r"match_softkw",
        r"case_softkw\d*",
        r"case_default_underscore",
        r"keyword\d*"]),
    re.IGNORECASE)


class ColourManager(Rule, ColorDelegator):
    __slots__ = "old_bg", "old_fg", "old_insertbg", "colorizer", "text", \
                "coloriser"
    REQUESTED_LIBRARIES:tuple[str] = [("insertdeletemanager",True)]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ColourManager:
        evs:tuple[str] = (
                           "<<Raw-After-Insert>>", "<<Raw-After-Delete>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.delegate:tk.Text = text
        self.coloriser:bool = False
        self.text:tk.Text = text
        ColorDelegator.init_state(self)
        ColorDelegator.close(self)
        self.init()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig({"word":{}})
        self.idprog = re.compile(r"\s+(\w+)")
        self.prog = re.compile(r"\b(?P<word>\w+)\b", re.M|re.S)

    def __getattr__(self, key:str) -> object:
        return getattr(self.text, key)

    def setdelegate(self, delegate:object) -> None:
        raise RuntimeError("Unreachable")

    def attach(self) -> None:
        super().attach()
        self.old_bg:str = self.text.cget("bg")
        self.old_fg:str = self.text.cget("fg")
        self.old_insertbg:str = self.text.cget("insertbackground")
        self.text.config(bg="black", fg="white", insertbackground="white",
                         takefocus=True)
        # Start recolorising
        self.config_colors()
        if not self.coloriser:
            self.coloriser:bool = True
            self.toggle_colorize_event(self)
        self.notify_range("1.0", "end")
        # Bring forward hit tag
        try:
            self.text.tag_raise("hit")
        except tk.TclError:
            pass

    def detach(self) -> None:
        super().detach()
        self.coloriser:bool = False
        ColorDelegator.close(self)
        self.removecolors()
        self.text.config(bg=self.old_bg, fg=self.old_fg,
                         insertbackground=self.old_insertbg)

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if on == "<raw-after-insert>":
            start, data, _ = event.data["abs"]
            end:str = self.text.index(f"{start} +{len(data)}c")
        elif on == "<raw-after-delete>":
            start, _ = event.data["abs"]
            end:str = None
        return start, end, True

    def do(self, _:str, start:str, end:str|None) -> Break:
        self.notify_range(start, end)
        return False

    # def notify_range(self, start:str, end:str|None=None) -> None:
    #     print((start, end))
    #     super().notify_range(start, end)

    def _add_tag(self, start:int, end:int, head:str, tag:str) -> None:
        start_idx:str = self.text.index(f"{head} +{start}c")
        self.tag_add(tag, start_idx, f"{start_idx} +{end-start}c")

    def _add_tags_in_section(self, chars:str, head:str) -> None:
        # from time import perf_counter
        # s = perf_counter()
        if isinstance(self.prog, Regex):
            for start, end, name in self.prog.finditer(chars):
                if name not in self.tagdefs: continue
                self._add_tag(start, end, head, name)
        else:
            for match in self.prog.finditer(chars):
                for name, matched_text in match.groupdict().items():
                    if not matched_text: continue
                    tag:str = "SYNC" if name.lower() == "sync" else name.lower()
                    start, end = match.span(name)
                    if KEYWORD_GROUPS.fullmatch(tag):
                        tag:str = "keyword"
                    self._add_tag(start, end, head, tag)
                    if matched_text in ("def", "class"):
                        if m1 := self.idprog.match(chars, end):
                            start, end = m1.span(1)
                            self._add_tag(start, end, head, "definition")
        # self.time = getattr(self, "time", 0) + perf_counter() - s
        # print(self.time)


# New method for colorising:
class Regex:
    __slots__ = "parser"

    def __init__(self, parser:Parser) -> Regex:
        assert isinstance(parser, Parser), "TypeError"
        self.parser:Parser = parser

    def finditer(self, text:str) -> Iterable[tuple[int,int,str]]:
        yield from self.parser.master_read(text)


Token:type = str
Location:type = int
TokenType:type = str
SeekLocation:type = int
TokenTypePair:type = tuple[Token,TokenType]


class Buffer(StringIO):
    __slots__ = ()

    def peek(self, size:int) -> str:
        location:int = super().tell()
        output:str = super().read(size)
        super().seek(location)
        return output


not_alpha:Callable[str,bool] = lambda s: not s.isalpha()
not_digit:Callable[str,bool] = lambda s: not s.isdigit()

def alpha_or_nonascii(text:str) -> bool:
    """
    Alpha or (¬Ascii) = ¬((¬Alpha) and Ascii)
    """
    for _ in filter(not_alpha, filter(str.isascii, text)):
        return False
    return True

not_alpha_or_nonascii:Callable[str,bool] = lambda s: not alpha_or_nonascii(s)

def isidentifier(token:Token) -> bool:
    """
    First character must be Alpha or (¬Ascii)
    The rest of the characters must be Alpha or (¬Ascii) or Digit
    """
    if not token: return False
    if not alpha_or_nonascii(token[0]):
        return False
    for _ in filter(not_digit, filter(not_alpha_or_nonascii, token)):
        return False
    return True


class Parser:
    __slots__ = "isidentifier", "negatives", \
                "under", "seen_text", "overrides"

    def __init__(self, isidentifier:Callable[str:bool]=isidentifier,
                 negatives:bool=True) -> Parser:
        """
        `isidentifier` function is used to recognise/test identifiers
        `negatives` tells us if we should treat `-453` as 1 or 2 tokens
        """
        self.isidentifier:Callable[str:bool] = isidentifier
        self.negatives:bool = negatives

    def tell(self) -> Location:
        """
        Returns the current read location. Only to be used
          in `self.override`
        """
        return self.under.tell()

    def override(self, start:Location, size:int, tokentype:TokenType) -> None:
        self.overrides.append((start,start+size,tokentype))

    def read(self) -> Iterable[TokenTypePair]:
        """
        Use `self.read_token` to override this method to yield tuples of
          token, token type pairs.
        If the token type is `""`, it is ignored.
        Note that all of the tokens from `self.read_token()` must be yielded
          sequentially (in-order) without dropping any of them
        It's fine if the parser joins up tokens into bigger tokens but
          they must stay in the same order
        Tokens returned from `read_token` are:
            * Identifiers (see `isidentifier` arg in `__init__`)
            * Numbers (with leading +/-) (int/hex/bin/float/exponential)
            * >>
            * <<
            * All other characters are returned individually
        Note:
            You must not join newlines with tokens on its left nor
              right. newlines are used for SYNC tags
        """
        raise NotImplementedError("Implement this method")

    def master_read(self, text:str) -> Iterable[tuple[int,int,str]]:
        """
        Note that text will always start from the begining of a line
          and will always end at the end of a line (including "\n" on
          the right side)
        """
        # Reset
        self.overrides:list[Location,Location,TokenType] = []
        self.under:Buffer = Buffer(text)
        self.seen_text:str = ""
        # Read tokens
        start = end = 0
        for token, tokentype in self.read():
            end += len(token)
            if text[start:end] != token:
                raise RuntimeError(f"Expected token={text[start:end]!r} got " \
                                   f"{token=!r} instead ({tokentype=!r})")
            print("out:", (token,tokentype))
            if token == "\n": # Try adding SYNC on newlines
                tokentype:str = tokentype or "SYNC"
            if tokentype:
                yield start, end, tokentype
            start:int = end
        # Check all data used up
        if end < len(text):
            raise RuntimeError("Not all data was used up by Parser")
        elif end > len(text):
            raise RuntimeError("Some data was duplicated by Parser")
        # Overrides
        for start, end, tokentype in self.overrides:
            yield start, end, tokentype

    def read_join_spaces(self, spaces:list[str]) -> Token:
        """
        Read and join space tokens (intended for indentation/whitespace
          clearing)
        """
        total_token:Token = ""
        while True:
            token:Token = self.peek_token()
            if not token: break
            if token.strip(spaces): break
            total_token += self.read_token()
        return total_token

    def peek_token(self) -> Token:
        """
        Same as `read_token` but the token isn't consumed
        """
        location:int = self.under.tell()
        token:Token = self._read_token()
        self.under.seek(location)
        return token

    def read_token(self) -> Token:
        """
        Read a token (identifier/number/<</>>/any other character)
        """
        token:Token = self._read_token()
        self.seen_text += token
        return token

    def _read_token(self) -> Token:
        char:Token = self.under.peek(1)
        # Empty
        if not char: return char
        # Identifier
        if self.isidentifier(char):
            output:Token = self.under.read(1)
            while True:
                if not self.isidentifier(output + self.under.peek(1)):
                    break
                output += self.under.read(1)
            return output
        # +/-
        if char in ("-", "+"):
            sign:str = self.under.read(1)
            if self.negatives and self.under.peek(1).isdigit():
                return self._try_read_number(sign)
            else:
                return sign
        # <</>>
        if char in ("<",">"):
            char:str = self.under.read(1)
            if self.under.peek(1) == char:
                return char + self.under.read(1)
            return char
        # Numbers (without leading +/-)
        if char.isdigit():
            return self._try_read_number()
        # Default:
        return self.under.read(1)

    def _try_read_number(self, sign:Token="") -> Token:
        """
        Reads a json like number without the +/- from the start
        """
        output:Token = sign
        char:str = self.under.peek(1)
        if char == "0":
            output += self.under.read(1)
            char:str = self.under.peek(1)
            # Read hex/oct/bin
            if char in NUMBER_LITERAL_TYPES:
                output += char
                possible:set[str] = NUMBER_LITERAL_TYPES[char]
                while True:
                    char:str = self.under.peek(1)
                    if not char: break
                    if char.lower() not in possible: break
                    output += self.under.read(1)
                return output
        # Normal numbers
        output += self._try_read_int()
        # Decimals
        if self.under.peek(1) == ".":
            output += self.under.read(1)
            output += self._try_read_int()
        # Exponentials
        if self.under.peek(1).lower() == "e":
            output += self.under.read(1)
            if self.under.peek(1) in "+-":
                output += self.under.read(1)
            output += self._try_read_int()
        return output

    def _try_read_int(self) -> Token:
        output:Token = ""
        while True:
            char:str = self.under.peek(1)
            if char not in DIGITS: break
            output += self.under.read(1)
        return output


NUMBER_LITERAL_TYPES:dict[str,str] = {
                                       "x": set("0123456789abcdef"), # hex
                                       "o": set("0123456"), # oct
                                       "b": set("01"), # bin
                                     }
DIGITS:set[str] = set("0123456789")