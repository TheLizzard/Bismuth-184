from __future__ import annotations
from time import perf_counter
import tkinter as tk
import os

from .baserule import Rule, SHIFT, ALT, CTRL

DEBUG:bool = False


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
    raise NotImplementedError(f"OS {os.name=!r} not recognised.")

TIME_HIGHLIGHT_BRACKETS:int = 1000


class BracketManager(Rule):
    __slots__ = "text"

    BACKET_HIGHLIGHT_TAG:str = "bracket_highlight"
    BRACKETS:tuple[tuple[str,str,str]] = BRACKETS
    BRACKETS_DICT:dict[str] = {open:close for open, close, _ in BRACKETS}
    RBRACKETS_DICT:dict[str] = {close:open for open, close, _ in BRACKETS}

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:list[str] = ["<BackSpace>"]
        for open, close, tcl_name in self.BRACKETS:
            evs.append(open)
            evs.extend((close, f"<Alt-{tcl_name}>"))
        super().__init__(plugin, text, tuple(evs))
        self.text:tk.Text = self.widget
        self.text.tag_config(self.BACKET_HIGHLIGHT_TAG, background="grey")

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if event.state&CTRL:
            return False
        if on in ("alt-'", 'alt-"'):
            return False
        # if (event.state&ALT) and (not on.startswith("alt-")):
        #     return False
        if on == "backspace":
            start, end = self.plugin.get_selection()
            if start != end:
                return False
            around:str = self.text.get("insert -1c", "insert +1c")
            if len(around) < 2:
                return False
            before, after = around
            if before not in self.BRACKETS_DICT:
                return False
            if after != self.BRACKETS_DICT[before]:
                return False
        return True

    def do(self, on:str) -> Break:
        with self.plugin.undo_wrapper():
            if on.startswith("alt-"):
                return self.alt_bracket(on)
            if on in self.BRACKETS_DICT.keys():
                return self.open_bracket(on, self.BRACKETS_DICT[on])
            if on in self.RBRACKETS_DICT.keys():
                return self.close_bracket(self.RBRACKETS_DICT[on], on)
            if on == "backspace":
                return self.backspace()
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def alt_bracket(self, on:str) -> Break:
        on:str = on.removeprefix("alt-")
        for open, close, tcl_name in self.BRACKETS:
            if on == tcl_name:
                self.text.insert("insert", open)
                return True
        return False

    def _check_closing_after_open(self, close:str) -> bool:
        # For people (like me) who type ")" right after "(":
        double_press:bool = self.plugin.left_has_tag(self.BACKET_HIGHLIGHT_TAG,
                                                     "insert")
        if not double_press:
            return False
        if self.text.get("insert", "insert +1c") != close:
            return False
        self.plugin.move_insert("insert +1c")
        return True

    def open_bracket(self, open:str, close:str) -> Break:
        if open == close:
            is_comment:bool = self.plugin.left_has_tag("comment", "insert")
            left_is_string:bool = self.plugin.left_has_tag("string", "insert")
            right_is_string:bool = self.plugin.right_has_tag("string", "insert")
            BHT:str = self.BACKET_HIGHLIGHT_TAG
            double_press:bool = self.plugin.left_has_tag(BHT, "insert")
            if left_is_string or right_is_string:
                if self._check_closing_after_open(close):
                    return True
                return False
            if is_comment and (open == "'"):
                return False
            if self._check_closing_after_open(close):
                return True
        start, end = self.plugin.get_selection()
        self.plugin.remove_selection()
        self.text.mark_set("bracket_end", end)
        self.text.insert(end, close, "program")
        self.text.insert(start, open, "program")
        self.plugin.move_insert("bracket_end -1c")
        self.highlight(start, "bracket_end")
        return True

    def close_bracket(self, open:str, close:str) -> Break:
        if self._check_closing_after_open(close):
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
