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


class SaveLoadRunManager(Rule):
    __slots__ = "text", "args", "term", "cwd"
    REQUESTED_LIBRARIES:tuple[str] = "bind_all"
    REQUESTED_LIBRARIES_STRICT:bool = False

    FILE_TYPES:tuple[(str, str)] = (("Python file", "*.py"),
                                    ("All types", "*"))
    COMPILE:list[str] = ["python3", "-m", "py_compile", "{file}"]
    RUN:list[str] = ["python3", "{file}"]
    CD:list[str] = ["cd", "{folder}"]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:tuple[str] = (
                           # User interactions
                           "<Control-S>", "<Control-s>",
                           "<Control-O>", "<Control-o>",
                           # Other rules giving us commands
                           "<<Trigger-Save-As>>", "<<Trigger-Save>>",
                           "<<Trigger-Open>>",
                           # Run the code
                           "<F5>",
                           # Set/Remove cwd
                           "a<<Explorer-Set-CWD>>", "a<<Explorer-Unset-CWD>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.text:tk.Text = self.widget
        self.text.filepath:str = None
        self.term:TerminalTk = None
        self.args:list[str] = []
        self.cwd:str = None

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        data:str = None
        if on in ("<explorer-set-cwd>", "<trigger-open>"):
            data:str = event.data[0]
        return event.state&SHIFT, data, True

    def do(self, on:str, shift:bool, data:str) -> Break:
        if on == "f5":
            if shift:
                self.run_with_args()
            else:
                self.run(args=[])
            return False

        non:str = on.removeprefix("<trigger-").removesuffix(">") \
                    .removeprefix("control-")
        if non.startswith("s"):
            if shift or (non == "save-as"):
                self.save_as()
            else:
                self.save()
            return True
        if non.startswith("o"):
            if data is None:
                self.open()
            else:
                self.text.filepath:str = data
                self._open()
            return True

        if on == "<explorer-set-cwd>":
            self.cwd:str = data
            return None
        if on == "<explorer-unset-cwd>":
            self.cwd:str = None
            return None

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # Run
    def run_with_args(self) -> None:
        print("Implement: saverunmanager@run_with_args")
        self.run(args=[])

    def run(self, args:Iterable[str]) -> None:
        if self.text.edit_modified():
            print("Save first")
            return None

        if (self.term is None) or (not self.term.running):
            self.term = TerminalTk(self.widget)
            self.term.iqueue(0, ["echo", " Starting ".center(80, "=")], None)
        else:
            self.term.cancel_all()
            self.term.send_signal(b"KILL")
            self.term.send_ping(wait=True)
            self.term.iqueue(0, ["echo", " Restarting ".center(80, "=")], None)

        self.cd()
        self.compile()
        self.execute(args)

    def cd(self) -> None:
        cwd:str = self.cwd or os.path.expanduser("~")
        command:tuple[str] = self.format(self.CD, {"folder":cwd})
        self.term.iqueue(1, command, None)

    def compile(self) -> None:
        command = self.format(self.COMPILE, {"file":self.text.filepath})
        self.term.iqueue(2, command, None, condition=(0).__eq__)

    def execute(self, args:Iterable[str]) -> None:
        command = self.format(self.RUN, {"file":self.text.filepath}) + \
                  list(args)
        self.term.iqueue(3, command, None, condition=(0).__eq__)

    @staticmethod
    def format(text:list[str], kwargs:dict[str,str]) -> list[str]:
        text:list[str] = text.copy()
        for key, value in kwargs.items():
            for i in range(len(text)):
                if "{"+key+"}" in text[i]:
                    text[i] = text[i].replace("{"+key+"}", value)
        return text

    # Save/Load
    def save(self) -> None:
        if self.text.filepath is None:
            self.save_as()
        else:
            self._save()

    def save_as(self) -> None:
        file:str = asksaveasfilename(defaultextension=self.FILE_TYPES[0][1],
                                     filetypes=self.FILE_TYPES,
                                     master=self.text)
        if not file:
            return None
        self.text.filepath:str = file
        self._save()

    def open(self) -> None:
        # Stop if we have unsaved changes:
        if self.text.edit_modified():
            if self.text.event_generate("<<Unsaved-Open>>") == "break":
                print("breaking")
                return None
        # Ask the user for the filepath
        file:str = askopenfilename(filetypes=self.FILE_TYPES, master=self.text)
        if not file:
            return None
        self.text.filepath:str = file
        self._open()

    def _open(self) -> None:
        with open(self.text.filepath, "br") as file:
            data:bytes = file.read()
        try:
            data:str = data.decode("utf-8")
        except UnicodeError:
            title:str = "Unknown encoding"
            msg:str = "Error couldn't decode file."
            telluser(self.text, title=title, message=msg, icon="error",
                     center=True, center_widget=self.text)
            return None
        if self.text.compare("1.0", "!=", "end -1c"):
            self.text.delete("1.0", "end")
        self.text.saved:str = data
        self.text.insert("end", data, "program")
        self.text.event_generate("<<Open-File>>")

    def _save(self) -> None:
        data:str = self.text.get("1.0", "end").removesuffix("\n")
        if NO_SAVE:
            print("Stopping save")
        else:
            with open(self.text.filepath, "w") as file:
                file.write(data)
        self.text.saved:str = data
        self.text.event_generate("<<Save-File>>")
