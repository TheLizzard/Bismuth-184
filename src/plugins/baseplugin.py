from __future__ import annotations
import tkinter as tk

WARNINGS:bool = True


class BasePlugin:
    __slots__ = "rules", "widget"

    def __init__(self, widget:tk.Misc) -> BasePlugin:
        self.widget:tk.Misc = widget
        self.rules:list[Rule] = []

    def attach(self) -> None:
        for rule in self.rules:
            Rule:type[rule] = rule.__class__
            libraries:tuple[str]|str = rule.__class__.REQUESTED_LIBRARIES
            if isinstance(libraries, str):
                libraries:tuple[str] = (libraries,)
            for lib in libraries:
                self.request_library(lib, Rule.__name__,
                                     strict=Rule.REQUESTED_LIBRARIES_STRICT)
            rule.attach()

    def detach(self) -> None:
        for rule in self.rules:
            rule.detach()

    def add(self, Rule:type[Rule]) -> None:
        self.rules.append(Rule(self, self.widget))

    def add_rules(self, rules:Iterable[type[Rule]]) -> None:
        for Rule in rules:
            self.add(Rule)

    def is_library_loaded(self, method_name:str) -> bool:
        """
        Returns a boolean that describes if a `tk.<widget>` attribute has been
          changed by something. If instead the attribute is a boolean instead
          of a Function, the boolean will be returned instead.
        """
        method = getattr(self.widget, method_name, None)
        if isinstance(method, bool):
            return method
        function = getattr(self.widget.__class__, method_name, None)
        return getattr(method, "__func__", function) is not function

    def request_library(self, method:str, requester:str, strict:bool=False):
        if not self.is_library_loaded(method):
            msg:str = f"{requester} requested the library {method!r} " \
                      f"but it's not loaded."
            if strict:
                raise RuntimeError(msg)
            elif WARNINGS:
                print(f"[WARNING] {msg} {requester} might malfunction.")
