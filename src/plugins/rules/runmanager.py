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


class RunManager(Rule):
    __slots__ = "text", "args", "term", "cwd"
    REQUESTED_LIBRARIES:tuple[str] = "bind_all"
    REQUESTED_LIBRARIES_STRICT:bool = False

    COMPILE:list[str] = None
    RUN:list[str] = None
    CD:list[str] = None

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:tuple[str] = (
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
        if on == "<explorer-set-cwd>":
            data:str = event.data[0]
        return event.state&SHIFT, data, True

    def do(self, on:str, shift:bool, data:str) -> Break:
        if on == "f5":
            if shift:
                self.run_with_args()
            else:
                self.run(args=[])
            return False

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
            self.term.print(" Starting ".center(80, "="))
            #self.term.iqueue(0, ["echo", " Starting ".center(80, "=")], None)
        else:
            self.term.cancel_all()
            self.term.send_signal(b"KILL")
            self.term.send_ping(wait=True)
            self.term.print(" Restarting ".center(80, "="))
            #self.term.iqueue(0, ["echo", " Restarting ".center(80, "=")], None)

        self.term.topmost(True)
        self.term.topmost(False)
        self.term.focus_set()
        self.cd()
        self.compile()
        self.execute(args)

    def cd(self) -> None:
        if self.CD is None:
            return None
        cwd:str = self.cwd or os.path.expanduser("~")
        command:tuple[str] = self.format(self.CD, {"folder":cwd})
        self.term.iqueue(1, command, None)

    def compile(self) -> None:
        if self.COMPILE is None:
            return None
        command = self.format(self.COMPILE, {"file":self.text.filepath})
        self.term.iqueue(2, command, None, condition=(0).__eq__)

    def execute(self, args:Iterable[str]) -> None:
        if self.RUN is None:
            return None
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