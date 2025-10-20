from __future__ import annotations
from time import perf_counter
import tkinter as tk
import os

from .baserule import Rule


class CommentManager(Rule):
    __slots__ = "text"
    COMMENT_STR:str = ""

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        super().__init__(plugin, text, ("<Control-slash>",))
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        if self.COMMENT_STR == "":
            return True
        with self.plugin.select_wrapper():
            with self.plugin.double_wrapper():
                # Get the selection
                start, end = self.plugin.get_selection()
                getline = lambda idx: int(idx.split(".")[0])
                # For each line in the selection
                lines:list[int] = list(range(getline(start), getline(end)+1))
                spaces = min(map(self.get_whites, lines))
                for line in lines:
                    self.toggle_comment(line, spaces)
                return True

    def toggle_comment(self, linenumber:int, minwhites:int) -> None:
        line:str = self.text.get(f"{linenumber}.0", f"{linenumber}.0 lineend")
        whites:int = self.count(line, " \t")
        if line == "":
            return None
        if line[whites:].startswith(self.COMMENT_STR):
            end:int = whites + len(self.COMMENT_STR)
            if line[end:end+1] == " ":
                end += 1
            self.text.delete(f"{linenumber}.{whites}", f"{linenumber}.{end}")
            if (line[end:end+1] == " ") and (line[end+1:end+2] != " "):
                self.text.delete(f"{linenumber}.{whites}")
        else:
            idx:str = f"{linenumber}.{min(whites, minwhites)}"
            self.text.insert(idx, self.COMMENT_STR+" ", "program")

    def get_whites(self, linenumber:int) -> int:
        line:str = self.text.get(f"{linenumber}.0", f"{linenumber}.0 lineend")
        whites:int = self.count(line, " \t")
        return whites if line != "" else float("inf")

    def count(self, string:str, ins:tuple[str]) -> int:
        return len(string) - len(string.lstrip(ins))
