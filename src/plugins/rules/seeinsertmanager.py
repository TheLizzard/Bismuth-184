from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class SeeInsertManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:tuple[str] = "insertdel_events"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # Key press
                           "<<Before-Insert>>", "<<Before-Delete>>",
                           "<<After-Insert>>", "<<After-Delete>>",
                           # Insert being moved
                           "<<Move-Insert>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        idx:str = None
        if on == "<move-insert>":
            idx:str = event.data[0]
        return idx, True

    def do(self, on:str, idx:str) -> Break:
        if (on == "<move-insert>") and (idx != "insert"):
            self.text.mark_set("insert", idx)
        self.text.see("insert")
        return False