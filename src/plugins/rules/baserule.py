from __future__ import annotations
from time import perf_counter
import tkinter as tk


Break = Applies = bool
DEBUG:bool = False

# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4


class Rule:
    __slots__ = "ons", "widget", "ids", "plugin", "attached"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = []

    def __init__(self, plugin:BasePlugin, widget:tk.Misc, ons:tuple[str]):
        assert isinstance(ons, tuple), "TypeError"
        self.plugin:BasePlugin = plugin
        self.widget:tk.Misc = widget
        self.attached:bool = False
        self.ons:tuple[str] = ons
        self.ids:list[str] = []

    def attach(self) -> None:
        assert not self.attached, "Already attached"
        self.attached:bool = True
        self.ids:list[str] = []
        for on in self.ons:
            add:bool = True
            bind_all:bool = False
            if on.startswith("a") and (on != "a"):
                on:str = on.removeprefix("a")
                bind_all:bool = True
            if on.startswith("-") and (on != "-"):
                on:str = on.removeprefix("-")
                add:bool = False
            better_on:str = on.removeprefix("<").removesuffix(">").lower()
            func = lambda event, on=better_on: self(event, on)
            if bind_all:
                id:str = self.widget.bind_all(on, func, add=add)
            else:
                id:str = self.widget.bind(on, func, add=add)
            self.ids.append(id)

    def detach(self) -> None:
        assert self.attached, "Not attached"
        self.attached:bool = False
        for on, id in zip(self.ons, self.ids):
            bind_all:bool = False
            if on.startswith("a") and (on != "a"):
                on:str = on.removeprefix("a")
                bind_all:bool = True
            on:str = on.removeprefix("-")
            if bind_all:
                self.widget.unbind_all(on, id)
            else:
                self.widget.unbind(on, id)
        self.ids.clear()

    def destroy(self) -> None:
        self.widget = None
        self.plugin = None

    def __call__(self, event:tk.Event, on:str) -> str:
        if not self.attached:
            return None
        start:float = perf_counter()
        data = self.applies(event, on)
        if DEBUG: print(f"[DEBUG {perf_counter()-start:.2f}]: Checking if {on} applies to {self.__class__.__name__}")
        if not isinstance(data, tuple|list):
            data = (data,)
        *data, applies = data
        if applies:
            start:float = perf_counter()
            block:bool = self.do(on, *data)
            if DEBUG: print(f"[DEBUG {perf_counter()-start:.2f}]: {self.__class__.__name__}.do({on}) => {block}")
            return "break" if block else None

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return False

    def do(self, on:str, *data) -> Break:
        return False

    def get_state(self) -> object:
        return None

    def set_state(self, state:object) -> None:
        if state is not None:
            raise RuntimeError("State was saved but not loaded")
