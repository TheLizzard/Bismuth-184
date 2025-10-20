from __future__ import annotations
import tkinter as tk

from .xrawidgets import SingletonMeta
from .baserule import Rule


class WrapManager(Rule, metaclass=SingletonMeta):
    __slots__ = "text", "old_wrap"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("settingsmanager",True)]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> WrapManager:
        super().__init__(plugin, text, ons=("<<Settings-Changed>>",))
        self.text:tk.Text = self.widget

    # Attach/Detach
    def attach(self) -> None:
        super().attach()
        self.old_wrap:str = self.text.cget("wrap")
        self.text.add_setting("wrap", type="bool", default=False)
        self._config_wrap()

    def detach(self) -> None:
        super().detach()
        self.text.config(wrap=self.old_wrap)

    # handle events
    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        if on == "<settings-changed>":
            self._config_wrap()
            return False
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def _config_wrap(self) -> None:
        if self.text.get_setting("wrap"):
            if hasattr(self.text, "disable"):
                self.text.disable()
            self.text.config(wrap="word")
        else:
            self.text.config(wrap="none")
            if hasattr(self.text, "enable"):
                self.text.enable()
