from __future__ import annotations
import tkinter as tk

from ..baserule import Rule, SHIFT, ALT, CTRL


class StdInsertManager(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        super().__init__(plugin, text, ("<Control-E>", "<Control-e>"))
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        shift:bool = event.state&SHIFT
        if shift:
            return False
        return shift, True

    def do(self, on:str, shift:bool) -> Break:
        with self.plugin.undo_wrapper():
            return self._do(on, shift)

    def _do(self, on:str, shift:bool) -> Break:
        if on == "control-e":
            start, end = self.plugin.get_selection()
            if start != end:
                with self.plugin.see_end_wrapper():
                    self.text.delete(start, end)
                    self.text.insert("insert", copied)
            self.text.insert("insert", "std::")
            return True
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")