from __future__ import annotations
from tkinter.filedialog import askopenfilename, asksaveasfilename
from sys import getdefaultencoding
import tkinter as tk
import os

from bettertk.messagebox import tell as telluser, askyesno
from bettertk.terminaltk.terminaltk import TerminalTk
from .baserule import Rule, SHIFT, ALT, CTRL

DEFAULT_ENCODING:str = getdefaultencoding()
NO_SAVE:bool = False # For debug only


class SaveLoadManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("save_module",True)]

    FILE_TYPES:tuple[(str, str)] = (("Text files", ".txt"),
                                    ("All types", "*"))

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:tuple[str] = (
                           # User interactions
                           "<Control-S>", "<Control-s>",
                           "<Control-O>", "<Control-o>",
                           "<Control-R>", "<Control-r>",
                           # Forced to save/open
                           "<<Trigger-Open>>", "<<Trigger-Save>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = text
        self.text.filesystem_data:str = getattr(text, "filesystem_data", "")
        self.text.filepath:str = getattr(text, "filepath", None)

    # Helpers
    def can_read(self) -> bool:
        assert self.text.filepath is not None, "InternalError"
        msg:str = "Unreachable in SaveLoadManager.can_read"
        if not os.path.exists(self.text.filepath):
            return False
        elif not os.path.isfile(self.text.filepath):
            msg:str = "File is now a folder on the filesystem."
        elif os.access(self.text.filepath, os.R_OK):
            return True
        else:
            msg:str = "You don't have the permissions to open this file."
        telluser(self.text, title="File permissions", message=msg, icon="error",
                 center=True, center_widget=self.text)
        return False

    def can_write(self) -> bool:
        assert self.text.filepath is not None, "InternalError"
        if os.path.exists(self.text.filepath):
            permissions:bool = os.access(self.text.filepath, os.W_OK)
        else:
            parent_folder:str = os.path.dirname(self.text.filepath)
            permissions:bool = os.access(parent_folder, os.W_OK)
        if permissions:
            return True
        title:str = "File permissions"
        msg:str = "You don't have the permissions to save this file."
        telluser(self.text, title=title, message=msg, icon="error",
                 center=True, center_widget=self.text)
        return False

    # handle events
    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        shift:bool = event.state&SHIFT
        if (on == "control-r") and (not shift):
            return False
        return shift, True

    def do(self, on:str, shift:bool) -> Break:
        if on.startswith("<trigger-"):
            on:str = on.removeprefix("<trigger-").removesuffix(">")
            if on == "open":
                self._open()
            elif on == "save":
                self._save()
            return False

        if on.startswith("control-"):
            if on == "control-s":
                if shift or (self.text.filepath is None):
                    error:bool = self.ask_saveas_filepath()
                    if error:
                        return True
                self.text.event_generate("<<Request-Save>>")
                return True
            if on == "control-o":
                error:bool = self.ask_open_filepath()
                if error:
                    return True
                self.text.event_generate("<<Request-Open>>")
                return True
            if on == "control-r":
                if self.text.edit_modified():
                    ret:bool = self.ask_reload()
                    if not ret:
                        return True
                self._reload()
                return True
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # User ask
    def ask_saveas_filepath(self) -> Error:
        file:str = asksaveasfilename(defaultextension=self.FILE_TYPES[0][1],
                                     filetypes=self.FILE_TYPES,
                                     master=self.text)
        if not file:
            return True
        self.text.filepath:str = file
        return False

    def ask_open_filepath(self) -> Error:
        file:str = askopenfilename(filetypes=self.FILE_TYPES, master=self.text)
        if not file:
            return True
        self.text.filepath:str = file
        return False

    def ask_reload(self) -> bool:
        title:str = "Reload discarding changes?"
        msg:str = "Are you sure you want to reload discarding \n" \
                  "all changes to this file?"
        return askyesno(self.text, title=title, message=msg, center=True,
                        icon="warning", center_widget=self.text)

    # Save/Open
    def _save(self) -> None:
        if not self.can_write():
            return None
        data:str = self.text.get("1.0", "end").removesuffix("\n")
        if NO_SAVE:
            print("Stopping save")
        else:
            with open(self.text.filepath, "wb") as file:
                file.write(data.encode(DEFAULT_ENCODING))
        self.text.filesystem_data:str = data
        self.text.event_generate("<<Saved-File>>")

    def _open(self) -> None:
        self._internal_open()
        # self.text.see("end -1c linestart")
        self.text.event_generate("<<Opened-File>>")
        self.plugin.move_insert("1.0")

    # reload
    def _reload(self) -> None:
        insert:str = self.text.index("insert")
        self._internal_open()
        self.text.event_generate("<<Reloaded-File>>")
        self.plugin.move_insert(insert)

    def _internal_open(self) -> None:
        if not self.can_read():
            return None
        with open(self.text.filepath, "br") as file:
            data:bytes = file.read()
        try:
            data:str = data.decode("utf-8").replace("\r\n", "\n")
            data:str = data.removesuffix("\n")
            for char in data:
                # https://stackoverflow.com/q/71879883/11106801
                # Not fixed by: https://github.com/python/cpython/issues/64567
                if (char == "\x00") or (128 <= ord(char) < 160):
                    raise UnicodeError(f"tkinter doesn't like {char=!r}")
        except UnicodeError as error:
            err_str:str = str(error)
            if len(err_str) > 45:
                err_str:str = err_str.replace("in position", "in\nposition")
            title:str = "UnicodeError"
            msg:str = f"Error couldn't open file.\n{err_str}"
            telluser(self.text, title=title, message=msg, icon="error",
                     center=True, center_widget=self.text)
            self.text.after(10, self.text.event_generate, "<<Close-Tab>>")
            return None
        if self.text.compare("1.0", "!=", "end -1c"):
            self.text.delete("1.0", "end")
        self.text.filesystem_data:str = data
        self.text.insert("end", data, "program")