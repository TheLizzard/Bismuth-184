from __future__ import annotations
from idlelib.colorizer import ColorDelegator
from time import perf_counter
from io import StringIO
import tkinter as tk
import bisect
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
REPLACE_LINE_CONTINUATIONS:re.Pattern = re.compile(
    r"[ \t]*" +      # Any white spaces, followed by
    r"(?<!\\)" +     # Not followed by a slash, followed by
    r"((?:\\\\)*)" + # An even number of slashes, followed by
    r"\\\n" +        # A slash and a newline, followed by
    r"[ \t]*"        # Any indentation
)

DEBUG:bool = False


class ColourManager(Rule, ColorDelegator):
    __slots__ = "old_bg", "old_fg", "old_insertbg", "colorizer", "text", \
                "coloriser"
    REQUESTED_LIBRARIES:tuple[str] = [("insertdeletemanager",True)]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ColourManager:
        evs:tuple[str] = (
                           "<<Raw-After-Insert>>", "<<Raw-After-Delete>>",
                         )
        super().__init__(plugin, text, ons=evs)
        # Note cpython issues: #84564 and #135052
        self.idprog = re.compile(r"[ \t]+(?:(?:\\\n)?[ \t]*)*([^\W\d]\w+)")
        self.delegate:tk.Text = text
        self.coloriser:bool = False
        self.text:tk.Text = text
        ColorDelegator.init_state(self)
        ColorDelegator.close(self)
        self.init()

    def init(self) -> None:
        self.prog = re.compile(r"\b(?P<word>\w+)\b|(?P<SYNC>\n)", re.M|re.S)
        self.tagdefs:dict[str,str] = ColourConfig({"word":{}})

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
        super().config_colors()
        if not self.coloriser:
            self.coloriser:bool = True
            super().toggle_colorize_event()
        if self.text.compare("1.0", "!=", "end -1c"):
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
        super().removecolors()
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

    def notify_range(self, start:str, end:str|None=None) -> None:
        end:str = end or "end"
        if (start == "1.0") and self.text.compare(end, "==", "end"):
            # Shortcut for colouring in the whole textbox
            self.text.update_idletasks()
            super().removecolors()
            self._add_tags_in_section(self.text.get("1.0","end"), "1.0")
        else:
            super().notify_range(start, end)

    def _add_tag(self, start:int, end:int, head:str, tag:str) -> None:
        start_idx:str = self.text.index(f"{head}+{start:d}c")
        self.text.tag_add(tag, start_idx, f"{start_idx}+{end-start:d}c")

    def _add_tags_in_section(self, chars:str, head:str) -> None:
        if DEBUG:
            s = perf_counter()
            self.lines = getattr(self, "lines", 0) + chars.count('\n')
            print(f"+{chars.count(chr(10))} more lines (total={self.lines}):")

        if isinstance(self.prog, Regex):
            head_start:int = 0
            for start, end, name in self.prog.finditer(chars):
                if name not in self.tagdefs: continue
                assert head_start <= start < end, "OrderingError"
                head:str = self.text.index(f"{head} +{start-head_start:d}c")
                head_start:int = start
                self._add_tag(start-head_start, end-head_start, head, name)
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

        if DEBUG:
            self.time = getattr(self, "time", 0) + perf_counter() - s
            print(f"\tTotal time: {self.time:.3f} sec")


# New method for colorising:
class Regex:
    __slots__ = "parser"

    def __init__(self, parser:Parser) -> Regex:
        assert isinstance(parser, Parser), "TypeError"
        self.parser:Parser = parser

    def finditer(self, text:str) -> Iterable[tuple[int,int,str]]:
        yield from self.parser._master_read(text)


Token:type = str
Location:type = int
TokenType:type = str
SeekLocation:type = int
TokenInfo:type = tuple[Location,Token,TokenType]


class Buffer(StringIO):
    __slots__ = "total_data", "_newlines"

    def __init__(self, data:str) -> Buffer:
        super().__init__(data)
        self.total_data:str = data
        self._newlines:list[int] = [0] + \
                              [i for i,c in enumerate(data) if c == "\n"] + \
                                   [len(data)]

    def peek(self, size:Location) -> str:
        location:Location = super().tell()
        return self.total_data[location:location+size]

    def closest_newlines(self, index:Location, *,
                         respect_slashes:bool) -> tuple[Location,Location]:
        """
        Return the location of the closest newlines around `index`
        """
        # Edge cases
        if index == 0:
            return 0, self._newlines[1]
        # Get the index of the index of the closest newline to the right
        idx:int = bisect.bisect_left(self._newlines, index)
        low_idx:int = idx - 1
        if respect_slashes:
            while low_idx > 0:
                start_text_idx:int = self._newlines[low_idx-1]
                end_text_idx:int = self._newlines[low_idx]
                line:str = self.total_data[start_text_idx:end_text_idx]
                slashes:int = len(line) - len(line.rstrip("\\"))
                if not (slashes&1): break
                low_idx -= 1
        # Get the index of the closest newlines
        return self._newlines[low_idx], self._newlines[idx]

    def __bool__(self) -> bool:
        return super().tell() != len(self.total_data)


not_alpha:Callable[str,bool] = lambda s: not s.isalpha()
not_digit:Callable[str,bool] = lambda s: not s.isdigit()

def alpha_or_nonascii(text:str) -> bool:
    """
    Alpha or (¬Ascii) = ¬((¬Alpha) and Ascii)
    """
    return not any(filter(not_alpha, filter(str.isascii, text)))

not_alpha_or_nonascii:Callable[str,bool] = lambda s: not alpha_or_nonascii(s)

def isidentifier(token:Token) -> bool:
    """
    First character must be Alpha or (¬Ascii)
    The rest of the characters must be Alpha or (¬Ascii) or Digit
    """
    if not token: return False
    if token[0].isdigit(): return False
    return not any(filter(not_digit, filter(not_alpha_or_nonascii, token)))


class Tokeniser:
    __slots__ = "isidentifier", "isnumber", "_under"

    def __init__(self, *, isidentifier:Callable[str,bool],
                 isnumber:Callable[str,bool]) -> Tokeniser:
        """
        `isidentifier` function is used to recognise/test for identifiers
        `isnumber` function is used to recognise/test for numbers
        This module provides an `isidentifier` that is more relaxed than
          Python's `str.isidentifier` (allowing non-ascii-non-alpha
          characters)
        """
        self.isidentifier:Callable[str,bool] = isidentifier
        self.isnumber:Callable[str,bool] = isnumber

    def __bool__(self) -> bool:
        """
        Returns if there are any tokens left in the buffer
        """
        return bool(self._peeked_token or self._under)

    def curr_line_seen(self, respect_slashes:bool=False) -> str:
        """
        Returns the text on the current line that has been read already.
        If `respect_slashes` it also concatenate previous lines that end
          in an odd number of slashes
        """
        curr:Location = self.tell()
        return self._get_line_until(curr, curr,
                                    respect_slashes=respect_slashes)

    def line_around(self, index:Location, respect_slashes:bool=False) -> str:
        """
        Returns all of the text on the current line even if it hasn't been
          read yet.
        """
        return self._get_line_until(index, respect_slashes=respect_slashes)

    def _get_line_until(self, _from:Location, to:Location=None, *,
                        respect_slashes:bool=False) -> str:
        """
        Internal Helper for `line_around` and `curr_line_seen`
        """
        start, end = self._under.closest_newlines(_from,
                                               respect_slashes=respect_slashes)
        end:Location = end if to is None else to
        text:str = self._under.total_data[start:end].removeprefix("\n")
        if "\n" in text:
            text = REPLACE_LINE_CONTINUATIONS.sub(r"\1", text)
        return text

    def text_between(self, start:Location, end:Location) -> str:
        """
        Returns the text between `start` and `end`. It acts like string
          indexing for indices that are out of bounds
        """
        return self._under.total_data[start:end]

    def tell(self) -> Location:
        """
        Returns the current read location. Don't do arithmetic
          operations on the returned location
        """
        # Subtract the peeked token because it was actually read not peeked
        return self._under.tell() - len(self._peeked_token or "")

    def peek_token(self) -> Token:
        """
        Peeks a token (indentation/identifier/number/any other character).
        This actually reads a token and caches it. We must remember
          to account for that in self.tell()
        """
        if self._peeked_token is None:
            start:str = self._under.tell()
            self._peeked_token:str|None = self._pure_read_token()
            if not self._peeked_token: return ""
            # Update self._start_size_map/self._overrides
            self._start_size_map.append((start,len(self._peeked_token)))
            self._overrides[start] = "SYNC"*(self._peeked_token == "\n")
        return self._peeked_token

    def skip_whitespaces(self, whitespaces:str, *,
                         slash_newline:bool=True) -> Token:
        """
        Skips whitespaces. Skips over slash newlines if `slash_newline`
        """
        while True:
            while self and (not self.peek_token().strip(whitespaces)):
                self.skip()
            start:Location = self.tell()
            if self.text_between(start, start+2) != "\\\n": break
            self.skip() # Skip the "\"
            self.set("no-sync-slash-newline") # Skip the "\n"

    def _pure_read_token(self) -> Token:
        output:Token = self._under.read(1)
        if output:
            # Indentation
            if output in " \t":
                while True:
                    if self._under.peek(1) not in " \t": break
                    output += self._under.read(1)
                return output
            # Identifier
            elif self.isidentifier(output):
                while self.isidentifier(output + self._under.peek(1)):
                    output += self._under.read(1)
                return output
            # Numbers
            elif self.isnumber(output):
                # Note that leading -/+ signs aren't part of the token
                while self.isnumber(output + self._under.peek(1)):
                    output += self._under.read(1)
                return output
        # Default:
        return output


class Parser(Tokeniser):
    __slots__ = "_overrides", "_start_size_map", "_peeked_token"

    # Override this
    def read(self) -> None:
        """
        Override this method using:
            * __bool__() -> bool
            * curr_line_seen(respect_slashes:bool=False) -> str
            * line_around(index:Location, respect_slashes:bool=False) -> str
            * text_between(start:Location, end:Location) -> str
            * tell() -> Location
            * peek_token() -> Token
            * skip_tokens(tokens:Iterable[str]) -> Token
            * set(tokentype:Tokentype, index:Optional[Location]) -> None
            * set_from(replace_tokentype:TokenType, start:Location,
                       end:Optional[Location], *
                       ignoretypes:set[TokenType]) -> None
            * skip() -> None
            * token_at(start:Location) -> Token
            * tokentype_at(start:Location) -> TokenType
            * next_start(start:Location) -> Optional[Location]
            * prev_start(start:Location) -> Optional[Location]
            * add_extra_pass(func:Callable[None]) -> None
            * tokens_after(start:Location) -> Iterable[TokenInfo]
            * read_tokens() -> Iterable[TokenInfo]
            * read_wait_for(tokens:Iterable[str], settype:Optional[TokenType],
                            *, ignoretypes:Iterable[str]=()) -> Token
            * add_extra_pass(func:Callable[None]) -> None

        Tokens returned from `peek_token` are:
            * Indentation (spaces/tabs concatenated)
            * Identifiers (see `isidentifier` arg in `__init__`)
            * Numbers (see `isnumber` arg in `__init__`)
            * All other characters are returned as separate tokens
        Note:
            If you peek a newline and don't `self.set(···)` with it
              with a non-empty tokentype, it will be used for SYNC
              which means that next time the line (before the "\n")
              is changed, only that line will be parsed. If you
              change the newline's tokentype to a non-empty string
              that isn't SYNC, it will join the 2 lines when picking
              which lines to parse.
        """
        raise NotImplementedError("Implement this method")

    # Use these functions
    def set(self, tokentype:TokenType, index:Location=None) -> None:
        """
        Set the token at `index`'s type as `tokentype`. If index is `None`,
          `index` is assumed to be `self.tell()`.
        If `index` is `None` or at `self.tell()`, it sets the tokentype and
          moves the buffer forward
        """
        assert isinstance(tokentype, TokenType), "TypeError"
        curr:Location = self.tell()
        if index is None:
            index:Location = curr
        else:
            assert isinstance(index, Location), "TypeError"
        self._overrides[index] = tokentype
        if index == curr:
            self.skip() # Advance buffer

    def set_from(self, replace_tokentype:TokenType, start:Location,
                 end:Location=None, *, ignoretypes:Iterable[str]=()) -> None:
        """
        Replace all tokentypes from `start` until `end` (or `self.tell()`
          if not specified) with `replace_tokentype` if the tokentype
          is not in `ignoretypes`
        """
        assert isinstance(replace_tokentype, TokenType), "TypeError"
        assert isinstance(start, Location), "TypeError"
        if end is None:
            end:Location = self.tell()
        else:
            assert isinstance(end, Location), "TypeError"
        while start < end:
            if not (ignoretypes and (self._overrides[start] in ignoretypes)):
                self.set(replace_tokentype, start)
            start:Location = self.next_start(start)

    def skip(self) -> None:
        """
        Advance buffer over `self.peek_token()` without setting a tokentype
        """
        # This actually reads a token instead of peeking it
        self._peeked_token:str|None = None
        self.peek_token()

    def token_at(self, start:Location) -> Token:
        """
        Return a token at the location. The buffer is not consumed. Location
          must be before or at `self.tell()`
        """
        if start < 0: return ""
        return self.text_between(start, self.next_start(start))

    def tokentype_at(self, start:Location) -> TokenType:
        """
        Return the tokentype at the given location. The buffer is not
          consumed. Location must be before or at `self.tell()`
        Deprecated:
            Unneeded since `self.set_from` takes in `ignoretypes` parameter
        """
        return self._overrides[start]

    def prev_token(self) -> Token:
        """
        Return the previous token that ends at `self.tell()`
        """
        start:Location = self.tell()
        if start == 0: return ""
        return self.token_at(self.prev_start(start))

    def next_start(self, start:Location) -> Location|None:
        """
        Returns the location where the next token starts. The token must
          have been read by `self.read()` first otherwise it returns `None`
        """
        if self._start_size_map[-1][0] < start: return None
        idx:int = bisect.bisect_left(self._start_size_map, (start,))
        if self._start_size_map[idx][0] != start:
            raise IndexError("Invalid token start location")
        # Since we store (start,size) tuples, we can just sum them to
        #   figure out the end which is the start for the next token
        return sum(self._start_size_map[idx])

    def prev_start(self, start:Location) -> Location|None:
        """
        Returns the location where the last token started. Returns `None`
          if `start` is already at the start of the data
        """
        if start == 0: return None
        idx:int = bisect.bisect_left(self._start_size_map, (start,))
        if self._start_size_map[idx][0] != start:
            raise IndexError("Invalid token start location")
        return self._start_size_map[idx-1][0]

    def tokens_after(self, start:Location=0) -> Iterable[TokenInfo]:
        """
        Yields all tokens after location that have been read/peeked.
        Deprecated: unused
        """
        idx:int = bisect.bisect_left(self._start_size_map, (start,))
        for i in range(idx, len(self._start_size_map)):
            start, size = self._start_size_map[i]
            # We can use `self.token_at` or `self.text_between`
            #   but this will be much faster
            token:Token = self._under.total_data[start:start+size]
            yield start, token, self._overrides[start]

    def read_tokens(self) -> Iterable[TokenInfo]:
        """
        Start peeking at tokens after they have been read by `self.read`.
        This yields tuples of (start,token,tokentype). This is useful for
          implementing recursive parsing (like nested f-strings in python
          or nested command-substitutions in bash).
        Note that while iterating over this, you shouldn't call `self.set`
          without passing in a location. It's discouraged to call
          `self.peek_token` since the recursive `self.read` call can read
          an arbitraty number of tokens before yielding them.

        Deprecated:
            * This function is deprecated. Use `self.read_wait_for` and
               `self.set_from` instead.
        """
        text:str = self._under.total_data
        max_index:int = len(text)
        index:Location = self.tell()
        while index < max_index:
            # Make sure we have called `self.read()` until at least
            #   the next token has been parsed
            while self.tell() <= index:
                self.read()
            end:Location = self.next_start(index)
            yield index, text[index:end], self._overrides[index]
            index:Location = end

    def read_wait_for(self, tokens:Iterable[str], settype:TokenType=None, *,
                      ignoretypes:Iterable[str]=(),
                      read_func:Callable[None]=None) -> Token:
        """
        Calls `self.read()` until the next token is in the `tokens` iterable
          passed in. If `settype` is passed in, this function behaves like
          `set_from` for all of the tokens read (excluding the returned one)
        Returns the next token (guaranteed to be empty or one of `tokens`)
        """
        assert isinstance(settype, TokenType|None), "TypeError"
        if read_func is None:
            read_func:Callable[None] = self.read
        while True:
            token:Token = self.peek_token()
            if (token in tokens) or (not token):
                return token
            elif token == "\n":
                self.set(f"no-sync-{settype}")
            else:
                if settype is None:
                    read_func()
                else:
                    start:Location = self.tell()
                    read_func()
                    self.set_from(settype, start, ignoretypes=ignoretypes)

    # Used by ColourManager
    def _master_read(self, text:str) -> Iterable[tuple[int,int,str]]:
        assert text.endswith("\n"), "self._pure_read_token might loop forever"
        # Reset
        self._overrides:dict[Location:TokenType] = {}
        self._start_size_map:list[tuple[Location,int]] = []
        self._peeked_token:str|None = None
        self._under:Buffer = Buffer(text)
        # Read tokens
        while self.peek_token(): self.read()
        assert self.tell() == len(text), "InternalError"
        # Merge and yield overrides
        max_idx:int = len(self._start_size_map)
        idx:int = 0
        while idx < max_idx:
            # Get info
            start, size = self._start_size_map[idx]
            tokentype:TokenType = self._overrides[start]
            end:Location = start + size
            idx += 1
            # If tokentype is empty, just skip it
            if not tokentype: continue
            # Merge
            while tokentype == self._overrides.get(end, None):
                end += self._start_size_map[idx][1]
                idx += 1
            # Yield the merged token
            yield start, end, tokentype
        assert end == len(self._under.total_data), "InternalError"


NUMBER_LITERAL_TYPES:dict[str,str] = {
                                       "x": set("0123456789abcdef"), # hex
                                       "o": set("0123456"), # oct
                                       "b": set("01"), # bin
                                     }
DIGITS:set[str] = set("0123456789")
