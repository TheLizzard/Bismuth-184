from __future__ import annotations
import tkinter as tk

from .baserule import Rule, SHIFT, ALT, CTRL


class ControlIJKLManager(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # New line shortcuts
                           "<Control-i>", "<Control-k>",
                           "<Control-I>", "<Control-K>",
                           # Swap lines
                           "<Control-j>", "<Control-l>",
                           "<Control-J>", "<Control-L>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if not (event.state&CTRL):
            return False
        on:str = on.removeprefix("keypress-").removeprefix("control-").lower()
        return on, event.state&SHIFT, True

    def do(self, _:str, on:str, shift:bool) -> Break:
        with self.plugin.see_end_wrapper():
            with self.plugin.undo_wrapper():
                self.plugin.remove_selection()
                if on == "i":
                    return self.control_i(shift)
                if on == "k":
                    return self.control_k(shift)
                if on == "j":
                    if shift: return False
                    return self.control_j()
                if on == "l":
                    if shift: return False
                    return self.control_l()
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # Control-i and Control-k
    def control_i(self, shift:bool) -> Break:
        if self.text.compare("insert linestart", "==", "1.0"):
            file_start:bool = True
            new_pos:str = "1.0"
        else:
            file_start:bool = False
            new_pos:str = "insert -1l lineend"
        self.plugin.move_insert(new_pos)
        self.text.event_generate("<" + ("Shift-"*shift) + "Return>")
        if file_start:
            self.text.event_generate("<Left>")
        return True

    def control_k(self, shift:bool) -> Break:
        new_pos:str = "insert lineend"
        self.plugin.move_insert(new_pos)
        self.text.event_generate("<" + ("Shift-"*shift) + "Return>")
        return True

    # Control-j and Control-l
    def control_j(self) -> Break:
        if self.text.compare("insert linestart", "==", "1.0"):
            return False
        insert:str = self.text.index("insert")
        line, char = insert.split(".")
        new_insert:str = f"{int(line)-1}.{char}"
        text:str = self.text.get(f"{insert} linestart", f"{insert} lineend")
        with self.plugin.virtual_event_wrapper():
            self.text.delete(f"{insert} -1l lineend", f"{insert} lineend")
            self.text.insert(f"{insert} -1l linestart", text+"\n", "program")
        self.plugin.move_insert(new_insert)
        return True

    def control_l(self) -> Break:
        if self.text.compare("insert lineend", "==", "end -1c"):
            return False
        insert:str = self.text.index("insert")
        line, char = insert.split(".")
        new_insert:str = f"{int(line)+1}.{char}"
        text:str = self.text.get(f"{insert} linestart", f"{insert} lineend")
        with self.plugin.virtual_event_wrapper():
            self.text.delete(f"{insert} linestart", f"{insert} +1l linestart")
            self.text.insert(f"{insert} lineend", "\n"+text, "program")
        self.plugin.move_insert(new_insert)
        return True
