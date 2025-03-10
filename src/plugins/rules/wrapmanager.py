from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class WrapManager(Rule):
    __slots__ = "text", "old_wrap", "chking_wrap", "after_id"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> WrapManager:
        ons = ("<<Opened-File>>", "<<Reloaded-File>>")
        super().__init__(plugin, text, ons=ons)
        self.text:tk.Text = self.widget
        self.chking_wrap:bool = False
        self.after_id:str = None

    # Attach/Detach
    def attach(self) -> None:
        super().attach()
        self.old_wrap:str = self.text.cget("wrap")
        self.chking_wrap:bool = True
        self._no_wrap_chk()

    def detach(self) -> None:
        super().detach()
        self.chking_wrap:bool = False
        self.text.config(wrap=self.old_wrap)

    # handle events
    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        if on in ("<opened-file>", "reloaded-file"):
            self._config_wrap()
            return False
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # Helpers
    def _no_wrap_chk(self) -> None:
        if self.after_id is not None:
            self.text.after_cancel(self.after_id)
        if self.chking_wrap:
            self._config_wrap()
        self.after_id:str = self.text.after(5000, self._no_wrap_chk)

    def _config_wrap(self) -> None:
        if self.text.get("1.0", "2.0") == "# no-wrap\n":
            if hasattr(self.text, "disable"):
                self.text.disable()
            self.text.config(wrap="word")
        else:
            self.text.config(wrap="none")
            if hasattr(self.text, "enable"):
                self.text.enable()