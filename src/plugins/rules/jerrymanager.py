from __future__ import annotations
import tkinter as tk

from bettertk.messagebox import tell as telluser
from .baserule import Rule


class JerryManager(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        super().__init__(plugin, text, ("<ButtonPress-1>", "<ButtonRelease-1>"))
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return False
        raw_on:str = "<<" + getattr(event.type,"name",event.type) + ">>"
        data:dict = dict(x=event.x, y=event.y, state=event.state)
        return True, raw_on, data

    def do(self, _:str, raw_on:str, data:dict) -> Break:
        print("jerry")
        self.text.event_generate(f"<{raw_on}>", *data)
        return True
        # raise RuntimeError(f"Unhandled {op} in {self.__class__.__name__}")