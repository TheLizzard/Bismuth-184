from __future__ import annotations
import tkinter as tk

from .baserule import Rule, SHIFT, ALT, CTRL


class ControlIJKLManager(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # New line shortcuts (top and bottom)
                           "<KeyPress-i>", "<KeyPress-k>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        ctrl:bool = event.state & CTRL

        # Control-i and Control-k
        if on.startswith("keypress-"):
            if not ctrl:
                return False
            on:str = on.removeprefix("keypress-")

        return on, ctrl, True

    def do(self, _:str, on:str, ctrl:bool) -> Break:
        if on == "i":
            if self.text.compare("insert linestart", "==", "1.0"):
                return False
            new_pos:str = "insert -1l lineend"
            self.text.event_generate("<<Move-Insert>>", data=(new_pos,))
            self.text.event_generate("<Return>")
            return True
        if on == "k":
            if self.text.compare("insert lineend", "==", "end -1c"):
                return False
            new_pos:str = "insert lineend"
            self.text.event_generate("<<Move-Insert>>", data=(new_pos,))
            self.text.event_generate("<Return>")
            return True

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")