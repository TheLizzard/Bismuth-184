from __future__ import annotations
from time import perf_counter
import tkinter as tk
import os

from .baserule import Rule

DEBUG:bool = False
# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4


if os.name == "posix":
    BRACKETS = (("[", "]", "bracketleft"),
                ("(", ")", "parenleft"),
                ("{", "}", "braceleft"),
                ("'", "'", "apostrophe"),
                ('"', '"', "quotedbl"))
elif os.name == "nt":
    BRACKETS = (("[", "]", "bracketleft"),
                ("(", ")", "parenleft"),
                ("{", "}", "braceleft"),
                ("'", "'", "'"),
                ('"', '"', '"'))
else:
    raise NotImplementedError(f"OS {os.name!r} not recognised.")

TIME_HIGHLIGHT_BRACKETS:int = 1000


class BracketManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:tuple[str] = "event_generate", "bind", "unbind"
    REQUESTED_LIBRARIES_STRICT:bool = False

    BACKET_HIGHLIGHT_TAG:str = "bracket_highlight"
    BRACKETS:tuple[tuple[str,str,str]] = BRACKETS
    BRACKETS_DICT:dict[str] = {open:close for open, close, _ in BRACKETS}
    RBRACKETS_DICT:dict[str] = {close:open for open, close, _ in BRACKETS}

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:list[str] = ["<BackSpace>"]
        for open, close, tcl_name in self.BRACKETS:
            evs.append(open)
            if open != close:
                evs.extend((close, f"<Alt-{tcl_name}>"))
        super().__init__(plugin, text, tuple(evs))
        self.text:tk.Text = self.widget
        self.text.tag_config(self.BACKET_HIGHLIGHT_TAG, background="grey")

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if event.state&CTRL:
            return False
        if (event.state&ALT) and (not on.startswith("alt-")):
            return False
        if on == "backspace":
            before, after = self.text.get("insert -1c", "insert +1c")
            if before not in self.BRACKETS_DICT:
                return False
            if after != self.BRACKETS_DICT[before]:
                return False
        return True

    def do(self, on:str) -> Break:
        if on.startswith("alt-"):
            return self.plugin.undo_wrapper(self.alt_bracket, on)
        if on in self.BRACKETS_DICT.keys():
            return self.plugin.undo_wrapper(self.open_bracket, on,
                                            self.BRACKETS_DICT[on])
        if on in self.RBRACKETS_DICT.keys():
            return self.plugin.undo_wrapper(self.close_bracket, on,
                                            self.RBRACKETS_DICT[on])
        if on == "backspace":
            return self.plugin.undo_wrapper(self.backspace)
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def alt_bracket(self, on:str) -> Break:
        on:str = on.removeprefix("alt-")
        for open, close, tcl_name in self.BRACKETS:
            if on == tcl_name:
                self.text.insert("insert", open)
                return True
        return False

    def open_bracket(self, open:str, close:str) -> Break:
        if open == close:
            is_comment:str = self.plugin.is_inside("comment", "insert")
            is_string:str = self.plugin.is_inside("string", "insert")
            if is_comment or is_string:
                return False
        start, end = self.plugin.get_selection()
        self.plugin.remove_selection()
        self.text.mark_set("bracket_end", end)
        self.text.insert(end, close, "program")
        self.text.insert(start, open, "program")
        self.text.event_generate("<<Move-Insert>>", data=("bracket_end -1c",))
        self.highlight(start, "bracket_end")
        return True

    def close_bracket(self, close:str, open:str) -> Break:
        # For people (like me) who type ")" right after "(":
        if self.plugin.is_inside(self.BACKET_HIGHLIGHT_TAG, "insert +1c") and \
           not self.plugin.is_inside(self.BACKET_HIGHLIGHT_TAG, "insert +2c"):
            if self.text.get("insert", "insert +1c") == close:
                self.text.event_generate("<<Move-Insert>>", data=("insert +1c",))
                return True
        # Find the closest match, insert the ")" and highlight the brackets
        start_t:float = perf_counter()
        start:str = self.find_bracket_match(open, close, "insert")
        if DEBUG: print(f"[DEBUG]: find_bracket_match took {perf_counter()-start_t:.3f} seconds")
        self.text.insert("insert", close)
        if start is not None:
            self.highlight(start, "insert")
        return True

    def backspace(self) -> Break:
        self.text.delete("insert -1c", "insert +1c")
        return True

    def find_bracket_match(self, open:str, close:str, end:str="insert"):
        # If we are in a comment or a string, stay in the comment/string
        is_comment:bool = self.plugin.is_inside("comment", end)
        is_string:bool = self.plugin.is_inside("string", f"{end} +1c")
        if is_string or is_comment:
            if is_string:
                tag:str = "string"
            elif is_comment:
                tag:str = "comment"
            start, _ = self.text.tag_prevrange(tag, end)
            text:list[str] = self.text.get(start, end).split("\n")
            add_line, add_char = start.split(".")
            add_line, add_char = int(add_line)-1, int(add_char)
        else:
            add_line = add_char = 0
            # Remove the strings/comments/both from text
            #   according to is_comment/is_string
            text:list[str] = self.text.get("1.0", end).split("\n")
            """
            while True:
                taga = self.text.tag_prevrange("comment", cur, "1.0")
                tagb = self.text.tag_prevrange("string", cur, "1.0")
                if not taga:
                    if not tagb:
                        break
                    _range = tagb
                elif not tagb:
                    _range = taga
                else:
                    _range = self._max_tag_range(taga, tagb)
                self._remove_range(text, _range)
                cur:str = _range[0]
            """
            self._remove_tag(text, "comment", end)
            self._remove_tag(text, "string", end)
        stack:int = 1
        for line_number, line in enumerate(reversed(text)):
            for char_number, char in enumerate(reversed(line)):
                if char == open:
                    stack -= 1
                elif char == close:
                    stack += 1
                if stack == 0:
                    l:int = len(text) - line_number + add_line
                    c:int = len(line) - char_number + add_char - 1
                    return f"{l}.{c}"
        return None

    def _remove_tag(self, text:list[str], tag:str, end:str) -> None:
        cur:str = end
        while True:
            tag_range = self.text.tag_prevrange(tag, cur, "1.0")
            if not tag_range:
                return None
            self._remove_range(text, tag_range)
            cur:str = tag_range[0]

    """
    def _max_tag_range(self, taga:tuple[str,str], tagb:tuple[str,str]):
        linea, chara = taga[0].split(".")
        lineb, charb = tagb[0].split(".")
        if int(linea) > int(lineb):
            taga_greater:bool = True
        elif linea == lineb:
            taga_greater:bool = int(chara) > int(charb)
        else:
            taga_greater:bool = False
        return taga if taga_greater else tagb
    """

    def _remove_range(self, text:list[str], _range:tuple[tuple[str,str]]):
        start, end = _range
        start_line, start_char = start.split(".")
        start_line, start_char = int(start_line), int(start_char)
        end_line, end_char = end.split(".")
        end_line, end_char = int(end_line), int(end_char)

        in_between:list[str] = text[start_line-1:end_line]
        if start_line == end_line:
            in_between[0] = in_between[0][:start_char] + \
                            "-"*(end_char-start_char) + \
                            in_between[0][end_char:]
        else:
            in_between[0] = in_between[0][:start_char] + \
                            "-"*(len(in_between[0])-start_char)
            in_between[-1] = "-"*end_char + in_between[-1][end_char:]
            for i in range(1, len(in_between)-1):
                in_between[i] = "-"*len(in_between[i])
        text[start_line-1:end_line] = in_between

    """ Too slow
    def find_bracket_match(self, open:str, close:str, start:str="insert"):
        cur:str = start
        bracket_stack:int = 1
        start_in_comment:bool = self.plugin.is_inside("comment", start)
        start_in_string:bool = self.plugin.is_inside("string", start)
        while self.text.compare(cur, "!=", "0.0"):
            in_comment:bool = self.plugin.is_inside("comment", cur)
            in_string:str = self.plugin.is_inside("string", cur)
            cur:str = self.text.index(f"{cur} -1c")
            if in_comment == start_in_comment and in_string == start_in_string:
                char:str = self.text.get(cur, f"{cur} +1c")
                if char == open:
                    bracket_stack -= 1
                elif char == close:
                    bracket_stack += 1
                if bracket_stack == 0:
                    return cur
        return None
    """

    def highlight(self, start:str, end:str) -> None:
        self.text.tag_add(self.BACKET_HIGHLIGHT_TAG, start, end)
        self.text.after(TIME_HIGHLIGHT_BRACKETS, self.remove_highlight)

    def remove_highlight(self) -> None:
        self.text.tag_remove(self.BACKET_HIGHLIGHT_TAG, "1.0", "end")
