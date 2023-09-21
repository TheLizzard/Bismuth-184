from __future__ import annotations
import tkinter as tk
import string

from .baserule import Rule

DEBUG:bool = False
# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4
ALPHANUMERIC_ = string.ascii_letters + string.digits + "_"


class UndoManager(Rule):
    __slots__ = "text", "old_undo", "old_separators", "old_maxundo", \
                "paused", "sep_unnecessary", "after_id", "last_char_space"
    REQUESTED_LIBRARIES:tuple[str] = "event_generate", "bind", "unbind"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> UndoManager:
        self.sep_unnecessary:bool = False
        self.last_char_space:bool = False
        self.after_id:str = None
        self.paused:int = 0
        evs:tuple[str] = (
                           # Undo/Redo
                           "<Control-Z>", "<Control-z>",
                           # Insert separator
                           "<<Saved-File>>",
                           "<<Before-Insert>>", "<<After-Insert>>",
                           "<<Before-Delete>>", "<<After-Delete>>",
                           # Reset undo stack
                           "<<Opened-File>>", "<<Reloaded-File>>",
                           # Communication with other rules:
                           "<<Unpause-Separator>>", "<<Pause-Separator>>",
                           "<<Add-Separator>>", "<<Clear-Separators>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget

    def attach(self) -> None:
        super().attach()
        self.old_undo:str = self.text.cget("undo")
        self.old_maxundo:int = self.text.cget("maxundo")
        self.old_separators:str = self.text.cget("autoseparators")
        self.text.config(undo=True, autoseparators=False, maxundo=-1)

    def detach(self) -> None:
        super().detach()
        self.text.config(auto_separators=self.old_separators,
                         undo=self.old_undo, maxundo=self.old_maxundo)

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if on == "<before-delete>":
            self.sep_unnecessary:bool = False
            return False
        if on == "<before-insert>":
            self.sep_unnecessary:bool = False

        if (on == "<add-separator>") and self.sep_unnecessary:
            if (len(event.data) == 0) or (not event.data[0]):
                return False
            elif not self.paused:
                self.sep_unnecessary:bool = False
        if self.paused and (on != "<unpause-separator>"):
            return False
        data:str = None
        if on.endswith("-insert>"):
            data:str = event.data[1]
        return event.state&SHIFT, data, True

    def do(self, on:str, shift:bool, data:str|None) -> Break:
        if on == "control-z":
            if shift:
                self.plugin.double_wrapper(self.text.edit_redo)
                self.text.event_generate("<<Undo-Triggered>>")
            else:
                self.plugin.double_wrapper(self.text.edit_undo)
                self.text.event_generate("<<Redo-Triggered>>")
            self.sep_unnecessary:bool = True
            _, end = self.plugin.get_selection()
            self.text.event_generate("<<Move-Insert>>", data=(end,))
            self.text.event_generate("<<Modified-Change>>")
            return True

        if on in ("<opened-file>", "<reloaded-file>"):
            self.text.edit_reset()
            self.sep_unnecessary:bool = False
            self.text.edit_modified(False)
            self.add_sep(wait=False)
            self.text.event_generate("<<Modified-Change>>")
            return False
        if on == "<saved-file>":
            #self.add_sep()
            self.text.edit_modified(False)
            self.add_sep(wait=False)
            self.text.event_generate("<<Modified-Change>>")
            return False

        if on == "<before-insert>":
            if self.last_char_space:
                if data == " ":
                    return False
                else:
                    self.last_char_space:bool = False
                    self.sep_unnecessary:bool = False
                    self.add_sep(False)
            self.last_char_space:bool = (data == " ")
            self.sep_unnecessary &= (data in ALPHANUMERIC_)
            self.add_sep(wait=(data in ALPHANUMERIC_))
            # self.sep_unnecessary &= (data not in ALPHANUMERIC_)
            return False
        if on == "<after-insert>":
            if (data == " ") and self.last_char_space:
                return False
            self.sep_unnecessary &= (data in ALPHANUMERIC_)
            self.add_sep(wait=(data in ALPHANUMERIC_))
            self.text.event_generate("<<Modified-Change>>")
            return False
        if on == "<after-delete>":
            self.add_sep()
            self.text.event_generate("<<Modified-Change>>")
            return False

        if on == "<add-separator>":
            self.add_sep()
            return False

        if on == "<pause-separator>":
            self.paused += 1
            return False
        if on == "<unpause-separator>":
            self.paused -= 1
            return False
        if on == "<clear-separators>":
            self.text.edit_reset()
            self.add_sep()
            return False

    def add_sep(self, wait:bool=False) -> None:
        if self.after_id is not None:
            self.text.after_cancel(self.after_id)
        if not wait:
            self._add_sep()
        if not self.last_char_space:
            self.after_id:str = self.text.after(1000, self.add_sep)

    def _add_sep(self) -> None:
        if self.paused or self.sep_unnecessary:
            return None
        if DEBUG: print("[DEBUG]: add-sep")
        self.sep_unnecessary:bool = True
        self.text.edit_separator()
