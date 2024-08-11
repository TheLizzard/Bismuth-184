from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class WrapManager(Rule):
    __slots__ = "text", "old_wrap"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> WrapManager:
        super().__init__(plugin, text, ons=())
        self.text:tk.Text = self.widget

    def attach(self) -> None:
        super().attach()
        self.old_wrap:str = self.text.cget("wrap")
        self.text.config(wrap="none")

    def detach(self) -> None:
        super().detach()
        self.text.config(wrap=self.old_wrap)