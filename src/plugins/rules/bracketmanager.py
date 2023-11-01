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
        # if (event.state&ALT) and (not on.startswith("alt-")):
        #     return False
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
            is_comment:bool = self.plugin.is_inside("comment", "insert")
            is_string:bool = self.plugin.is_inside("string", "insert")
            if is_comment or is_string:
                # For people (like me) who double press '"':
                if self.plugin.is_inside(self.BACKET_HIGHLIGHT_TAG, "insert +1c"):
                    self.text.event_generate("<<Move-Insert>>",
                                             data=("insert +1c",))
                    return True
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
        start:str = self.plugin.find_bracket_match(open, close, "insert")
        if DEBUG: print(f"[DEBUG]: find_bracket_match took {perf_counter()-start_t:.3f} seconds")
        self.text.insert("insert", close)
        if start is not None:
            self.highlight(start, "insert")
        return True

    def backspace(self) -> Break:
        self.text.delete("insert -1c", "insert +1c")
        return True

    def highlight(self, start:str, end:str) -> None:
        self.text.tag_add(self.BACKET_HIGHLIGHT_TAG, start, end)
        self.text.after(TIME_HIGHLIGHT_BRACKETS, self.remove_highlight)

    def remove_highlight(self) -> None:
        self.text.tag_remove(self.BACKET_HIGHLIGHT_TAG, "1.0", "end")