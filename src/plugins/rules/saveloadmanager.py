from __future__ import annotations
from tkinter.filedialog import askopenfilename as askopen, \
                               asksaveasfilename as asksave
from sys import getdefaultencoding
import tkinter as tk
import os

from bettertk.messagebox import tell as telluser, askyesno
from bettertk.terminaltk.terminaltk import TerminalTk
from .baserule import Rule, SHIFT, ALT, CTRL

# DEFAULT_ENCODING:str = getdefaultencoding() # Unused
NO_SAVE:bool = False # For debug only


class SaveLoadManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = []

    FILE_TYPES:tuple[(str, str)] = (("Text files", ".txt"),
                                    ("All types", "*"))

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:tuple[str] = (
                           # User interactions
                           "<Control-S>", "<Control-s>",
                           "<Control-O>", "<Control-o>",
                           "<Control-R>", "<Control-r>",
                           # Forced to save/open
                           "<<Force-Open>>", "<<Force-Set-Data>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = text
        self.text.filesystem_data:str = getattr(text, "filesystem_data", "")
        self.text.filepath:str = getattr(text, "filepath", "")

    def attach(self) -> None:
        self.text.filepath:str = getattr(self.text, "filepath", "")
        self.text.filesystem_data:str = getattr(self.text, "filesystem_data",
                                                "")
        super().attach()

    # Helpers
    def _can_read(self) -> bool:
        assert self.text.filepath, "InternalError"
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

    def _can_write(self) -> bool:
        assert self.text.filepath, "InternalError"
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

    def _chk_fs_modified(self) -> bool:
        print(os.path.exists(self.text.filepath))
        if not self.text.filepath:
            return False
        if not os.path.exists(self.text.filepath):
            return False
        with open(self.text.filepath, "rb") as file:
            filesystem_data:bytes = file.read() \
                                        .replace(b"\r\n", b"\n") \
                                        .rstrip(b"\n")
        print(repr(filesystem_data),
              repr(self.text.filesystem_data.encode("utf-8")), sep="\n")
        if not filesystem_data:
            return False
        return filesystem_data != self.text.filesystem_data.encode("utf-8")

    def _edit_modified(self, value:bool) -> None:
        self.text.edit_modified(value)
        self.text.event_generate("<<Modified-Change>>")

    # handle events
    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        data:str = ""
        shift:bool = event.state&SHIFT
        if (on == "control-r") and (not shift):
            return False
        if on in ("<force-open>", "<force-set-data>"):
            data:str = event.data
        return shift, data, True

    def do(self, on:str, shift:bool, data:str) -> Break:
        if on == "<force-open>":
            self.text.filepath:str = data
            self._internal_open(reload=False)
            return False

        if on == "<force-set-data>":
            self.text.delete("1.0", "end -1c")
            self.text.insert("end", data)
            self.text.event_generate("<<Clear-Separators>>")
            self._edit_modified(False)
            return False

        if on == "control-s":
            if shift or (not self.text.filepath):
                file:str = asksave(defaultextension=self.FILE_TYPES[0][1],
                                   filetypes=self.FILE_TYPES,
                                   master=self.text)
                if not file: return True
                self.text.filepath:str = file
            self._save()
            return True

        if on == "control-o":
            file:str = askopen(filetypes=self.FILE_TYPES, master=self.text)
            if not file: return True
            self.text.filepath:str = file
            if self.text.edit_modified():
                title:str = "Discard changes to this file?"
                msg:str = "You haven't saved this file. Are you sure you\n" \
                          "want to continue and discard the changes?"
                ret:bool = askyesno(self.text, title=title, icon="warning",
                                    message=msg, center=True,
                                    center_widget=self.text)
                if not ret: return False
            self._internal_open(reload=False)
            return True

        if on == "control-r":
            if self.text.edit_modified():
                title:str = "Reload discarding changes?"
                msg:str = "Are you sure you want to reload discarding \n" \
                          "all changes to this file?"
                ret:bool = askyesno(self.text, title=title, message=msg,
                                    center=True, icon="warning",
                                    center_widget=self.text)
                if not ret: return True
            self._internal_open(reload=True)
            return True

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # Save/Open
    def _save(self) -> None:
        # Compare and ask if we can replace data
        if self._chk_fs_modified():
            self._edit_modified(True)
            title:str = "Merge conflict"
            msg:str = "The file has been modified on the filesystem.\n" \
                      "Are you sure you want to save it?"
            allow:bool = askyesno(self.text, title=title, icon="warning",
                                  message=msg, center=True,
                                  center_widget=self.text)
            if not allow:
                return None
        # Actual save
        if not self._can_write():
            return None
        self.text.filesystem_data:str = self.text.get("1.0", "end") \
                                                 .rstrip("\n")
        if NO_SAVE:
            print("Stopping save")
        else:
            with open(self.text.filepath, "wb") as file:
                file.write(self.text.filesystem_data.encode("utf-8"))
        self.text.event_generate("<<Saved-File>>")

    def _internal_open(self, *, reload:bool) -> None:
        # Check if the file can be read
        if not self._can_read():
            return None
        with open(self.text.filepath, "rb") as file:
            data:bytes = file.read()
        try:
            data:str = data.decode("utf-8") \
                           .replace("\r\n", "\n") \
                           .removesuffix("\n")
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
        # Delete old
        current_data:str = self.text.get("1.0", "end -1c")
        if current_data.rstrip("\n") != data:
            if self.text.compare("1.0", "!=", "end -1c"):
                self.text.delete("1.0", "end")
            self.text.filesystem_data:str = data
            self.text.insert("end", data, "program")
        # Trigger the correct event
        if reload:
            self.text.event_generate("<<Reloaded-File>>")
        else:
            self.text.event_generate("<<Opened-File>>")
            self.plugin.move_insert("1.0")

    # Save/Load state
    def get_state(self) -> object:
        # Get state
        filepath:str = self.text.filepath
        modified:bool = self.text.edit_modified()
        data:str = self.text.get("1.0", "end").rstrip("\n")
        saved_data:str = self.text.filesystem_data
        xview:str = str(self.text.xview()[0])
        yview:str = str(self.text.yview()[0])
        insert:str = self.text.index("insert")
        # Congregate state information:
        save_state:list[object] = (filepath, modified, data, saved_data)
        view_state:list[object] = (xview, yview, insert)
        return (save_state, view_state)

    def set_state(self, state:object) -> None:
        assert not self.text.filepath, "set_state called too late"
        if not isinstance(state, list|tuple): return None
        save_state, view_state = state
        self._set_state_save(*save_state)
        self._set_state_view(*view_state)

    def _set_state_view(self, xview:str, yview:str, insert:str) -> None:
        self.plugin.move_insert(insert)
        self.text.xview("moveto", xview)
        self.text.yview("moveto", yview)

    def _set_state_save(self, filepath:str, modified:bool, data:str,
                        saved_data:str) -> None:
        self.text.filepath:str = filepath
        self.text.filesystem_data:str = saved_data
        # Check for merge conflict
        if self.text.filepath:
            if not modified:
                self._internal_open(reload=False)
                return None
            problem:bool = True
            if self._can_read():
                with open(self.text.filepath, "rb") as fd:
                    filedata:bytes = fd.read() \
                                       .replace(b"\r\n", b"\n") \
                                       .rstrip(b"\n")
                    problem:bool = saved_data.encode("utf-8") != filedata
            if problem:
                title:str = "Merge Conflict"
                msg:str = f"The file {self.text.filepath} has been\n" \
                          f"modified on your system and there are " \
                          f"changes in this editor.\nThis means that " \
                          f"you have a merge conflict."
                telluser(self.text, title=title, message=msg,
                         center=True, icon="warning",
                         center_widget=self.text, block=False)
        # Set the data
        self.text.delete("1.0", "end")
        self.text.insert("end", data)
        self.text.event_generate("<<Clear-Separators>>")
        self.text.event_generate("<<Opened-File>>")
        self._edit_modified(modified)