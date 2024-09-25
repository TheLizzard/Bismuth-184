from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class SeeInsertManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("insertdeletemanager",True)]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # Key press
                           "<<Raw-Before-Insert>>", "<<Raw-Before-Delete>>",
                           "<<Raw-After-Insert>>", "<<Raw-After-Delete>>",
                           # Insert moved
                           "<<Insert-Moved>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        self.text.see("insert")
        return False