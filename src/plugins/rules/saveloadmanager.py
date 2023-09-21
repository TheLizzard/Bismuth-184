from __future__ import annotations
from tkinter.filedialog import askopenfilename, asksaveasfilename
import tkinter as tk
import os

from bettertk.terminaltk.terminaltk import TerminalTk
from bettertk.messagebox import tell as telluser
from .baserule import Rule

# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4

NO_SAVE:bool = False # for debug purposes


class SaveLoadManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:tuple[str] = "save_module"
    REQUESTED_LIBRARIES_STRICT:bool = False

    FILE_TYPES:tuple[(str, str)] = (("All types", "*"))

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
        self.text:tk.Text = self.widget
        self.text.filesystem_data:str = ""
        self.text.filepath:str = None

    # Helpers
    def can_read(self) -> bool:
        assert self.text.filepath is not None, "InternalError"
        if os.access(self.text.filepath, os.R_OK):
            return True
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
        return event.state&SHIFT, True

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
                    self.ask_saveas_filepath()
                self.text.event_generate("<<Request-Save>>")
                return True
            if on == "control-o":
                self.ask_open_filepath()
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
    def ask_saveas_filepath(self) -> None:
        file:str = asksaveasfilename(defaultextension=self.FILE_TYPES[0][1],
                                     filetypes=self.FILE_TYPES,
                                     master=self.text)
        if not file:
            return None
        self.text.filepath:str = file

    def ask_open_filepath(self) -> None:
        file:str = askopenfilename(filetypes=self.FILE_TYPES, master=self.text)
        if not file:
            return None
        self.text.filepath:str = file

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
            with open(self.text.filepath, "w") as file:
                file.write(data)
        self.text.filesystem_data:str = data
        self.text.event_generate("<<Saved-File>>")

    def _open(self) -> None:
        self._internal_open()
        self.text.event_generate("<<Opened-File>>")

    # reload
    def _reload(self) -> None:
        self._internal_open()
        self.text.event_generate("<<Reloaded-File>>")

    def _internal_open(self) -> None:
        if not self.can_read():
            return None
        with open(self.text.filepath, "br") as file:
            data:bytes = file.read()
        try:
            data:str = data.decode("utf-8").replace("\r\n", "\n")
        except UnicodeError:
            title:str = "Unknown encoding"
            msg:str = "Error couldn't decode file."
            telluser(self.text, title=title, message=msg, icon="error",
                     center=True, center_widget=self.text)
            return None
        if self.text.compare("1.0", "!=", "end -1c"):
            self.text.delete("1.0", "end")
        self.text.filesystem_data:str = data
        self.text.insert("end", data, "program")