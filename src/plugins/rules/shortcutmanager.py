from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class RemoveShortcuts(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:set[str] = set()
        characters:set[str] = set("poiytewkhfdazxcvbn")
        others:set[str] = {"at", "slash", "Tab"}
        for char in characters|set(map(str.upper, characters))|others:
            evs.add(f"<Control-{char}>")
        super().__init__(plugin, text, tuple(evs))
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        return True
