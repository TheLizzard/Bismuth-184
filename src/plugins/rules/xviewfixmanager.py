from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class XViewFixManager(Rule):
    __slots__ = "text", "old_xset"
    REQUESTED_LIBRARIES:tuple[str] = "colorizer", "scroll_bar"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # After any changes
                           "<<After-Insert>>", "<<After-Delete>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def attach(self) -> None:
        self.old_xset = self.text.cget("xscrollcommand")
        # self.text.config(xscrollcommand=self.xset)
        super().attach()

    def detach(self) -> None:
        self.text.config(xscrollcommand=self.old_xset)
        super().detach()

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return event.data, True

    def do(self, on:str, data:tuple[str,str,str]) -> Break:
        if on == "<after-insert>":
            # data = (idx, text, tag)
            return False
        if on == "<after-delete>":
            # data = ("insert -1c", None) # pressed backspace
            # data = ("2.5", "6.3") # Selected and deleted
            return False

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def xset(self, low:str, high:str) -> None:
        # modify (low, high)
        self.text.tk.call(self.old_xset, low, high)