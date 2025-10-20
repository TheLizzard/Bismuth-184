from __future__ import annotations
import tkinter as tk

from .baserule import Rule, SHIFT, ALT, CTRL

DEBUG_SEP:bool = False
DEBUG_NOSEP:bool = False
DEBUG_PAUSE:bool = False
DEBUG_INSERT:bool = False
DEBUG_UNDO_REDO:bool = False
TIME_DELAY_UNDO_SEP:int = 300
ORIG_LOC:tuple[str] = ("colorizer", "percolator", "redir", "orig")

class UndoManager(Rule):
    __slots__ = "text", "old_undo", "old_separators", "old_maxundo", \
                "paused", "after_id", "modified_since_last_sep", \
                "last_char_type", "undo", "redo"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("insertdeletemanager",True)]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> UndoManager:
        self.modified_since_last_sep:bool = True
        self.last_char_type:str = None
        self.after_id:str = None
        self.paused:int = 0
        evs:tuple[str] = (
                           # Undo/Redo
                           "<Control-Z>", "<Control-z>",
                           # Insert separator
                           "<<Saved-File>>",
                           "<<Raw-Before-Insert>>", "<<Raw-After-Insert>>",
                           "<<Raw-Before-Delete>>", "<<Raw-After-Delete>>",
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
        self.modified_since_last_sep:bool = True
        self.old_undo:str = self.text.cget("undo")
        self.old_maxundo:int = self.text.cget("maxundo")
        self.old_separators:str = self.text.cget("autoseparators")
        self.text.config(undo=True, autoseparators=False, maxundo=-1)
        orig:str|None = self._getattr(self.text, ORIG_LOC)
        if orig is None:
            self.undo = self.text.edit_undo
            self.redo = self.text.edit_redo
        else:
            self.undo = lambda: self.text.tk.call(orig, "edit", "undo")
            self.redo = lambda: self.text.tk.call(orig, "edit", "redo")
        self.text.after(100, self.text.event_generate, "<<Clear-Separators>>")

    def _getattr(self, obj:object, attrs:tuple[str]) -> object|None:
        for attr in attrs:
            obj:object = getattr(obj, attr, None)
        return obj

    def detach(self) -> None:
        super().detach()
        self.text.config(auto_separators=self.old_separators,
                         undo=self.old_undo, maxundo=self.old_maxundo)

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        # if self.paused and (on != "<unpause-separator>"):
        #     return None

        data:str = None
        if on.endswith("-insert>"):
            data:str = event.data["raw"][1]
            if not data:
                return False

        if on.endswith("-delete>"):
            data:str = event.data["raw"][1]

        return event.state&SHIFT, data, True

    def do(self, on:str, shift:bool, data:str|None) -> Break:
        if on == "control-z":
            if self.paused:
                return True
            if shift:
                if not self.text.edit("canredo"):
                    if DEBUG_UNDO_REDO: print("[DEBUG]: (canredo) no redo")
                    return True
                self.add_sep(force=True)
                with self.plugin.double_wrapper():
                    self.text.edit_redo()
                if DEBUG_UNDO_REDO: print("[DEBUG]: redone")
                self.text.event_generate("<<Redo-Triggered>>")
            else:
                if not self.text.edit("canundo"):
                    if DEBUG_UNDO_REDO: print("[DEBUG]: (canundo) no undo")
                    return True
                self.add_sep(force=True)
                with self.plugin.double_wrapper():
                    self.text.edit_undo()
                if DEBUG_UNDO_REDO: print("[DEBUG]: undone")
                self.text.event_generate("<<Undo-Triggered>>")

            _, end = self.plugin.get_selection()
            self.plugin.move_insert(end)
            self.text.event_generate("<<Modified-Change>>")
            # self.modified_since_last_sep:bool = True
            self.add_sep(force=True)
            return True

        if on in ("<opened-file>", "<reloaded-file>"):
            self.text.event_generate("<<Clear-Separators>>")
            self.text.edit_modified(False)
            self.text.event_generate("<<Modified-Change>>")
            return False
        if on == "<saved-file>":
            self.text.edit_modified(False)
            self.add_sep(force=True)
            self.text.event_generate("<<Modified-Change>>")
            return False

        if on == "<raw-before-insert>":
            if self.paused:
                return False
            new_char_type:str = self._get_type(data)
            if DEBUG_INSERT: print(f"[DEBUG]: before new {new_char_type=!r}")
            self.add_sep(force=((self.last_char_type != new_char_type) and \
                                (self.last_char_type is not None)))
            self.last_char_type:str = new_char_type
            return False
        if on == "<raw-after-insert>":
            self.modified_since_last_sep:bool = True
            if self.paused:
                return False
            if DEBUG_INSERT:
                if len(data) < 10: print(f"[DEBUG]: after new {data!r}")
                else: print(f"[DEBUG]: after new {len(data)=}")
            with self.plugin.virtual_event_wrapper(anti=True):
                self.text.event_generate("<<Modified-Change>>")
            return False
        if on == "<raw-before-delete>":
            if self.paused:
                return False
            self.add_sep(force=True)
            return False
        if on == "<raw-after-delete>":
            self.modified_since_last_sep:bool = True
            self.last_char_type:str = None
            if self.paused:
                return False
            with self.plugin.virtual_event_wrapper(anti=True):
                self.text.event_generate("<<Modified-Change>>")
            self.add_sep(force=True)
            return False

        if on == "<add-separator>":
            if self.paused:
                return False
            self.add_sep(force=True, reason="event")
            return False

        if on == "<pause-separator>":
            if DEBUG_PAUSE and (self.paused == 0): print(f"[DEBUG]: pause")
            self.paused += 1
            return False
        if on == "<unpause-separator>":
            self.paused -= 1
            if DEBUG_PAUSE and (self.paused == 0):
                print(f"[DEBUG]: unpause"+"!"*self.modified_since_last_sep)
            return False

        if on == "<clear-separators>":
            if self.paused:
                raise RuntimeError("Why call clear-separators when paused?")
            self.add_sep(cancel_only=True)
            self.modified_since_last_sep:bool = False
            self.text.event_generate("<<Cleared-Separators>>")
            self.text.edit_reset()
            return False

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def _get_type(self, string:str) -> str:
        if len(string) > 1:
            return "largee" if self.last_char_type == "large" else "large"
        if self.last_char_type == "0":
            if string.isdigit() or (string == "."):
                return "0"
        if string.isdigit():
            if self.last_char_type == "a":
                return "a"
            else:
                return "0"
        if string.isidentifier():
            return "a"
        return string

    def add_sep(self, *, force:bool=False, cancel_only:bool=False,
                reason:str=None) -> None:
        """
        This starts a timer to call `self._add_sep` after TIME_DELAY_UNDO_SEP
        milliseconds. If force=True then it skips the wait and immediately
        calls `self._add_sep`
        """
        if self.after_id is not None:
            self.text.after_cancel(self.after_id)
        if cancel_only:
            return None
        if force:
            self._add_sep(reason=reason)
        else:
            self.after_id = self.text.after(TIME_DELAY_UNDO_SEP, self._add_sep)

    def _add_sep(self, reason:str=None) -> None:
        """
        Adds an edit separator unless `self.paused` or it's unnecessary
        because `self.modified_since_last_sep=False`
        """
        if not self.modified_since_last_sep:
            if DEBUG_NOSEP: print("[DEBUG]: (modified_flag) no add-sep")
            return None
        if self.paused:
            if DEBUG_NOSEP: print("[DEBUG]: (paused) no add-sep")
            return None
        if DEBUG_SEP:
            if reason is None: print("[DEBUG]: add-sep")
            else: print(f"[DEBUG]: (because of {reason}) add-sep")
        self.text.event_generate("<<Added-Separator>>")
        self.modified_since_last_sep:bool = False
        self.last_char_type:str = None
        self.text.edit_separator()
