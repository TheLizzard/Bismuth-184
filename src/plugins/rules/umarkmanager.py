from __future__ import annotations
import tkinter as tk

from .baserule import Rule


class UMarkManager(Rule):
    __slots__ = "text", "marks"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        ons:tuple[str] = (
                           # Toggle umarks
                           "<Control-m>", "<Control-M>"
                           # Goto umark
                           "<Control-8>", "<Control-KP_8>",
                           "<Control-2>", "<Control-KP_2>",
                           # Clear umarks
                           "<<Opened-File>>",
                           # Re-mark
                           "<<Reloaded-File>>",
                         )
        super().__init__(plugin, text, ons=ons)
        self.text:tk.Text = self.widget
        self.marks:set[int] = set()

    def attach(self) -> None:
        self.marks.clear()
        super().attach()

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        if on == "control-m":
            line:str = int(self.text.index("insert").split(".")[0])
            if line in self.marks:
                self.marks.remove(line)
                self.text.event_generate("<<Remove-UMark>>", data=line)
            else:
                self.marks.add(line)
                self.text.event_generate("<<Set-UMark>>", data=line)
            return False
        if on.endswith("2"):
            line:str = int(self.text.index("insert").split(".")[0])
            endline:str = int(self.text.index("end").split(".")[0])
            for i in range(line+1, endline+1):
                if i in self.marks:
                    self.plugin.move_insert(f"{i}.0 lineend")
                    break
            return False
        if on.endswith("8"):
            line:str = int(self.text.index("insert").split(".")[0])
            for i in range(line-1, -1, -1):
                if i in self.marks:
                    self.plugin.move_insert(f"{i}.0 lineend")
                    break
            return False
        if on == "<opened-file>":
            for mark in self.marks.copy():
                self.text.event_generate("<<Remove-UMark>>", data=mark)
                self.marks.remove(mark)
            return False
        if on == "<reloaded-file>":
            for mark in self.marks:
                self.text.event_generate("<<Set-UMark>>", data=mark)
            return False
        raise RuntimeError(f"Unhandled {on!r} in {self.__class__.__name__}")

    def get_state(self) -> object:
        return list(self.marks)

    def set_state(self, state:object) -> None:
        if not isinstance(state, list): return None
        for line in state:
            if not isinstance(line, int): return None
        for line in state:
            self.text.event_generate("<<Set-UMark>>", data=line)