from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class SeeEndManager(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # Key press
                           "<<After-Insert>>", "<<After-Delete>>",
                           # Undo/Redo/Arrows
                           "<<Move-Insert>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str, *data) -> Break:
        self.text.see("insert")
        return False

