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


def realpath(path:str) -> str:
    if not path: return ""
    return os.path.realpath(path)


class SaveLoadManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = []

    FILE_TYPES:tuple[tuple[str,str]] = (
                                         ("All types", "*"),
                                         ("Text files", ".txt"),
                                       )

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
        if not self.text.filepath:
            return False
        if not os.path.exists(self.text.filepath):
            return False
        try:
            with open(self.text.filepath, "rb") as file:
                filesystem_data:bytes = file.read()
        except OSError:
            return False
        if not filesystem_data:
            return False
        filesystem_data:str = self._security(filesystem_data, decode=True)
        modified:bool = filesystem_data != self.text.filesystem_data
        self.text.filesystem_data:str = filesystem_data
        return modified

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
            self.text.filepath:str = realpath(data)
            self._internal_open(reload=False)
            return False

        if on == "<force-set-data>":
            if self.text.compare("1.0", "!=", "end -1c"):
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
                self.text.filepath:str = realpath(file)
            self._save()
            return True

        if on == "control-o":
            file:str = askopen(filetypes=self.FILE_TYPES, master=self.text)
            if not file: return True
            self.text.filepath:str = realpath(file)
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

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__qualname__}")

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
        filesystem_data:str = self._remove_newline(self.text.get("1.0", "end"))
        self.text.filesystem_data:str = filesystem_data
        if NO_SAVE:
            print("Stopping save")
        else:
            try:
                with open(self.text.filepath, "wb") as file:
                    if self.text.filesystem_data: # Empty text => empty file
                        file.write(self.text.filesystem_data.encode("utf-8"))
                        file.write(b"\n") # https://stackoverflow.com/q/72271
            except OSError as error:
                msg:str = "Failed to save because of:\n" + \
                          repr(error)
                telluser(self.text, title="Error", message=msg, icon="error",
                         center=True, center_widget=self.text)
                return None
        self.text.event_generate("<<Saved-File>>")

    def _internal_open(self, *, reload:bool) -> None:
        xview, yview = self.text.xview()[0], self.text.yview()[0]
        insert:str = self.text.index("insert")
        success:bool = self._try_internal_open(reload=reload)
        if success:
            self.plugin.move_insert(insert)
            self.text.xview("moveto", xview)
            self.text.yview("moveto", yview)
        elif reload:
            msg:str = "File was deleted"
            telluser(self.text, title="Error", icon="error", message=msg,
                     center=True, center_widget=self.text)
        else:
            self.text.after(10, self.text.event_generate, "<<Close-Tab>>")

    def _try_internal_open(self, *, reload:bool) -> Success:
        # Check if the file can be read
        if not self._can_read():
            return False
        # Check the file's size and refuse/ask the user if they really
        #   want to open it
        filesize:int = _filesize(self.text.filepath)
        filesize_str:str = _pretty_print_size(filesize)
        if filesize > 100*MB: # >100MB - refuse to open
            msg:str = f"This file is too big ({filesize_str})."
            telluser(self.text, title="Huge file", icon="error", message=msg,
                     center=True, center_widget=self.text)
            return False
        if filesize > 2*MB: # (2MB, 100MB] - ask to open
            msg:str = f"This file is {filesize_str}. Are you\n" \
                      f"sure you want to open it?"
            allow:bool = askyesno(self.text, title="Huge file", icon="warning",
                                  message=msg, center=True,
                                  center_widget=self.text)
            if not allow: return False
        # Read the file
        with open(self.text.filepath, "rb") as file:
            data:bytes = file.read()
        # Make sure there are no illegal characters
        data:str|None = self._security(data, decode=True)
        if data is None: return False
        # Delete old
        current_data:str = self._remove_newline(self.text.get("1.0", "end"))
        if current_data != data:
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
        return True

    # Save/Load state
    def get_state(self) -> object:
        # Get state
        filepath:str = self.text.filepath
        modified:bool = self.text.edit_modified()
        data:str = self._remove_newline(self.text.get("1.0", "end"))
        saved_data:str = self.text.filesystem_data
        xview:str = str(self.text.xview()[0])
        yview:str = str(self.text.yview()[0])
        insert:str = self.text.index("insert")
        # Congregate state information:
        state:dict = dict(filepath=filepath, modified=modified, data=data,
                          saved_data=saved_data, xview=xview, yview=yview,
                          insert=insert)
        return state

    def set_state(self, state:object) -> None:
        assert not self.text.filepath, "set_state called too late"
        if not isinstance(state, dict): return None
        filepath:str = state.pop("filepath", "")
        modified:str = state.pop("modified", True)
        data:str = state.pop("data", "")
        saved_data:str = state.pop("saved_data", "")
        xview:str = state.pop("xview", "0.0")
        yview:str = state.pop("yview", "0.0")
        insert:str = state.pop("insert", "1.0")
        self._set_state_save(filepath, modified, data, saved_data)
        self._set_state_view(xview, yview, insert)

    def _set_state_view(self, xview:str, yview:str, insert:str) -> None:
        self.plugin.move_insert(insert)
        self.text.after(1, self.text.xview, "moveto", xview)
        self.text.after(1, self.text.yview, "moveto", yview)

    def _set_state_save(self, filepath:str, modified:bool, data:str,
                        saved_data:str) -> None:
        self.text.filepath:str = realpath(filepath)
        self.text.filesystem_data:str = saved_data
        opened:bool = False
        # Check for merge conflict
        if self.text.filepath:
            if not self._can_read():
                msg:str = f"The file {self.text.filepath}\n"
                if not os.path.exists(self.text.filepath):
                    msg += "no longer exists"
                elif os.path.isfile(self.text.filepath):
                    msg += "can't be read"
                else:
                    msg += "is a folder or a broken link"
                telluser(self.text, title="Can't read file", message=msg,
                         center=True, icon="warning", center_widget=self.text)
                return None
            elif modified:
                with open(self.text.filepath, "rb") as fd:
                    filedata:bytes = self._remove_newline(fd.read(),
                                                          binary=True)
                if saved_data.encode("utf-8") != filedata:
                    title:str = "Merge Conflict"
                    msg:str = f"The file {self.text.filepath} has been\n" \
                              f"modified on your system and there are " \
                              f"changes in this editor.\nThis means that " \
                              f"you have a merge conflict."
                    telluser(self.text, title=title, message=msg,
                             center=True, icon="warning",
                             center_widget=self.text)
            else:
                opened:bool = True
                self._internal_open(reload=False)
        # Set the data
        data:str|None = self._security(data, decode=False)
        if data is None: return None
        self.text.event_generate("<<Clear-Separators>>")
        if not opened:
            if self.text.compare("1.0", "!=", "end -1c"):
                self.text.delete("1.0", "end")
            self.text.insert("end", data, "program")
            self.text.event_generate("<<Opened-File>>")
        self._edit_modified(modified)

    def _security(self, data:bytes|str, *, decode:bool) -> str|None:
        try:
            if decode:
                assert isinstance(data, bytes), "if decode, data must be bytes"
                data:str = data.decode("utf-8")
            assert isinstance(data, str), "Pass in decode=True"
            data:str = self._remove_newline(data)
            char:str = _get_first_non_printable(data)
            if char:
                raise UnicodeError(f"{char=!r} isn't accepted by the security")
            return data
        except UnicodeError as error:
            err_str:str = str(error)
            if len(err_str) > 45:
                err_str:str = err_str.replace("in position", "in\nposition")
            title:str = "UnicodeError"
            msg:str = "Error couldn't open file."
            filepath:str = getattr(self.text, "filepath", "")
            if filepath:
                msg += f"\n{filepath}"
            msg += f"\n{err_str}"
            telluser(self.text, title=title, message=msg, icon="error",
                     center=True, center_widget=self.text)
            self.text.after(10, self.text.event_generate, "<<Close-Tab>>")
            return None

    @staticmethod
    def _remove_newline(text:str|bytes, *, binary:bool=False) -> str|bytes:
        if binary:
            return text.replace(b"\r\n", b"\n").removesuffix(b"\n")
        else:
            return text.replace("\r\n", "\n").removesuffix("\n")


# Security
# https://stackoverflow.com/q/71879883/11106801
# Not fixed by: https://github.com/python/cpython/issues/64567
def _string_is_non_printable(string:str) -> bool:
    # https://stackoverflow.com/a/6875607/11106801
    return len(string)+2 != len(repr(string))

def _find_satisfying_char_binary_search(predicate:Callable[str,bool],
                                        input_str:str) -> str:
    assert predicate(input_str), "predicate(input_str) must be true"
    while True:
        assert len(input_str) > 0, "Impossible"
        if len(input_str) == 1:
            assert predicate(input_str), "Impossible"
            return input_str
        # Binary search
        lower_string:str = input_str[:len(input_str)//2]
        if predicate(lower_string): # If lower half matches
            input_str:str = lower_string
        else: # Else upper half must match
            input_str:str = input_str[len(input_str)//2:]

def _get_first_non_printable(string:str) -> str:
    for char in "\n\t\r\"'\\":
        string:str = string.replace(char, "")
    if not _string_is_non_printable(string):
        return ""
    return _find_satisfying_char_binary_search(_string_is_non_printable, string)


SIZE_FACTOR:int = 1000
B:int = 1
KB:int = SIZE_FACTOR*B
MB:int = SIZE_FACTOR*KB
GB:int = SIZE_FACTOR*MB
TB:int = SIZE_FACTOR*GB
PB:int = SIZE_FACTOR*TB
EB:int = SIZE_FACTOR*PB

def _pretty_print_size(size:int) -> str:
    """
    Convert the size (in bytes) passed in to a human readable string
      rounded to 3 significant figures
    """
    for name in ("B", "KB", "MB", "GB", "TB", "PB", "EB"):
        if size < SIZE_FACTOR: break
        size /= SIZE_FACTOR
    return f"{size:.3g}{name}"

def _filesize(path:str) -> int:
    """
    Return the size (in bytes) of the file
    """
    size:int = 0
    chunk_size:int = 100*MB
    with open(path, "rb") as file:
        while True:
            data:bytes = file.read(chunk_size)
            if not data: break
            size += len(data)
    return size
