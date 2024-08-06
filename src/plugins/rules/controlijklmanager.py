from __future__ import annotations
import tkinter as tk

from .baserule import Rule, SHIFT, ALT, CTRL


class ControlIJKLManager(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # New line shortcuts (top and bottom)
                           "<KeyPress-i>", "<KeyPress-k>",
                           "<KeyPress-j>", "<KeyPress-l>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if not (event.state&CTRL):
            return False
        on:str = on.removeprefix("keypress-")
        return on, True

    def do(self, _:str, on:str) -> Break:
        with self.plugin.see_end:
            return self.plugin.undo_wrapper(self._do, on)

    def _do(self, on:str) -> Break:
        self.plugin.remove_selection()
        if on == "i":
            return self.control_i()
        if on == "k":
            return self.control_k()
        if on == "j":
            return self.control_j()
        if on == "l":
            return self.control_l()
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # Control-i and Control-k
    def control_i(self) -> Break:
        if self.text.compare("insert linestart", "==", "1.0"):
            file_start:bool = True
            new_pos:str = "1.0"
        else:
            file_start:bool = False
            new_pos:str = "insert -1l lineend"
        self.text.event_generate("<<Move-Insert>>", data=(new_pos,))
        self.text.event_generate("<Return>")
        if file_start:
            self.text.event_generate("<Left>")
        return True

    def control_k(self) -> Break:
        new_pos:str = "insert lineend"
        self.text.event_generate("<<Move-Insert>>", data=(new_pos,))
        self.text.event_generate("<Return>")
        return True

    # Control-j and Control-l
    def control_j(self) -> Break:
        if self.text.compare("insert linestart", "==", "1.0"):
            return False
        insert:str = self.text.index("insert")
        line, char = insert.split(".")
        new_insert:str = f"{int(line)-1}.{char}"
        text:str = self.text.get(f"{insert} linestart", f"{insert} lineend")
        def do() -> None:
            self.text.delete(f"{insert} -1l lineend", f"{insert} lineend")
            self.text.insert(f"{insert} -1l linestart", text+"\n", "program")
        self.plugin.virual_event_wrapper(do)
        self.text.event_generate("<<Move-Insert>>", data=(new_insert,))
        return True

    def control_l(self) -> Break:
        if self.text.compare("insert lineend", "==", "end -1c"):
            return False
        insert:str = self.text.index("insert")
        line, char = insert.split(".")
        new_insert:str = f"{int(line)+1}.{char}"
        text:str = self.text.get(f"{insert} linestart", f"{insert} lineend")
        def do() -> None:
            self.text.delete(f"{insert} linestart", f"{insert} +1l linestart")
            self.text.insert(f"{insert} lineend", "\n"+text, "program")
        self.plugin.virual_event_wrapper(do)
        self.text.event_generate("<<Move-Insert>>", data=(new_insert,))
        return True