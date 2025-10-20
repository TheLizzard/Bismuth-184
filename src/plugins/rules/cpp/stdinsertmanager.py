from __future__ import annotations
import tkinter as tk

from ..baserule import Rule, SHIFT, ALT, CTRL


class StdInsertManager(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        super().__init__(plugin, text, (
                                         # Insert "std::"
                                         "<Control-E>", "<Control-e>",
                                         # Insert "std::cout << | << str::endl;"
                                         "<Control-Q>", "<Control-q>",
                                       ))
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
            # Insert "std::" at the cursor
            start, end = self.plugin.get_selection()
            if start != end:
                with self.plugin.see_end_wrapper():
                    self.text.delete(start, end)
            self.text.insert("insert", "std::")
            return True

        elif on == "control-q":
            # Insert "std::cout << | << endl;" at the cursor line
            #   only if there is nothing already on that line. The
            #   "|" is where the cursor will be at the end
            idx:str = self.text.index("insert")
            line:str = self.text.get(f"{idx} linestart", f"{idx} lineend")
            if line.strip(" \t"):
                return False
            if not self.text.compare(idx, "==", f"{idx} lineend"):
                return False
            self.text.insert("insert", "std::cout << ")
            new_idx:str = self.text.index("insert")
            self.text.insert("insert", " << std::endl;")
            self.plugin.move_insert(new_idx)
            return True
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")
