from __future__ import annotations
import tkinter as tk

from .baserule import Rule

# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4


class FindReplaceManager(Rule):
    __slots__ = "text", "findreplace_window"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> None:
        evs:tuple[str] = (
                           # Find
                           "<Control-F>", "<Control-f>",
                           # Replace
                           "<Control-R>", "<Control-r>",
                           "<Control-H>", "<Control-h>",
                         )
        super().__init__(plugin, text, evs)
        self.text:tk.Text = self.widget

    def __new__(Cls, plugin:BasePlugin, text:tk.Text, *args, **kwargs):
        self:FindReplaceManager = getattr(text, "findreplacemanager", None)
        if self is None:
            self:FindReplaceManager = super().__new__(Cls, *args, **kwargs)
            text.findreplacemanager:FindReplaceManager = self
        return self

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if event.state&SHIFT:
            return False
        return True

    def do(self, on:str) -> Break:
        print(f"Implement: {on}")
        return True