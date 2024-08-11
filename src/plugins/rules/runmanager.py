from __future__ import annotations
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tempfile import TemporaryDirectory
import tkinter as tk
import os

from bettertk.terminaltk.terminaltk import TerminalTk
from bettertk.messagebox import tell as telluser
from bettertk import BetterTkSettings
from .baserule import Rule, SHIFT, ALT, CTRL


class RunManager(Rule):
    __slots__ = "text", "args", "term", "cwd", "tmp"
    REQUESTED_LIBRARIES:tuple[str] = "bind_all"
    REQUESTED_LIBRARIES_STRICT:bool = False

    CD:list[str] = ["cd", "{folder}"]
    COMPILE:list[str] = None
    RUN:list[str] = None
    TEST:list[str] = None # No key binding yet
    AFTER:list[str] = None

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs:tuple[str] = (
                           # Run the code
                           "<F5>",
                           # Set/Remove cwd
                           "a<<Explorer-Set-CWD>>", "a<<Explorer-Unset-CWD>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.tmp:TemporaryDirectory = None
        self.text:tk.Text = self.widget
        self.term:TerminalTk = None
        self.args:list[str] = []
        self.cwd:str = None

    def attach(self) -> None:
        super().attach()
        self.text.event_generate("<<Explorer-Report-CWD>>")

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        data:str = None
        if on == "<explorer-set-cwd>":
            if len(event.data) == 0:
                print("[WARNING]: <explorer-set-cwd> had no data!")
                return False
            data:str = event.data[0]
        return event.state&SHIFT, data, True

    def destroy(self) -> None:
        if (self.term is not None) and (self.term.running()):
            self.term.queue_clear(stop_cur_proc=True)
            self.term.close()
        if self.tmp is not None:
            self.tmp.cleanup()
        super().destroy()

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
            title:str = "Save first"
            msg:str = "You need to save before you can run the file."
            telluser(self.text, title=title, message=msg, center=True,
                     icon="error", center_widget=self.text)
            return None

        if (self.term is None) or (not self.term.running()):
            window_settings:BetterTkSettings = BetterTkSettings()
            window_settings.config(use_border=False)
            self.term = TerminalTk(self.widget, settings=window_settings)
            print_str:str = " Starting ".center(80, "=") + "\n"
        else:
            self.term.queue_clear(stop_cur_proc=True)
            # self.term.check_alive()
            self.term.clear()
            print_str:str = " Restarting ".center(80, "=") + "\n"

        if self.tmp is not None:
            self.tmp.cleanup()
        self.tmp:TemporaryDirectory = TemporaryDirectory()
        self.term.topmost(True)
        self.term.topmost(False)
        self.term.focus_set()
        self.cd(print_str=print_str)
        if self.compile():
            self.execute(args)
        self.after()

    def cd(self, req_cwd:str=None, *, print_str:str="") -> None:
        if self.CD is None:
            return None
        cwd:str = self.cwd or req_cwd or os.path.expanduser("~")
        command:tuple[str] = self.format(self.CD, {"folder":cwd})
        self.term.queue(["printf", print_str])
        self.term.queue(command)

    def compile(self, *, print_str:str="", command:list[str]=None) -> bool:
        if (self.COMPILE is None) and (command is None):
            return False
        if self.COMPILE == []:
            return True
        command:list[str] = command or self.COMPILE
        command:list[str] = self.format(command, {"file":self.text.filepath,
                                                  "tmp":self.tmp.name})
        self.term.queue(["printf", print_str], condition=(0).__eq__)
        self.term.queue(command)
        return True

    def execute(self, args:Iterable[str], *, print_str:str="") -> None:
        if self.RUN is None:
            return None
        command = self.format(self.RUN, {"file":self.text.filepath,
                                         "tmp":self.tmp.name}) + list(args)
        self.term.queue(["printf", print_str], condition=(0).__eq__)
        self.term.queue(command)

    def after(self, *, print_str:str="", command:list[str]=None) -> None:
        if (self.AFTER is None) and (command is None):
            return None
        command:list[str] = command or self.AFTER
        command:list[str] = self.format(command, {"file":self.text.filepath})
        self.term.queue(["printf", print_str], condition=(0).__eq__)
        self.term.queue(command)

    def test(self, args:Iterable[str], *, print_str:str="") -> None:
        if self.RUN is None:
            return None
        command = self.format(self.TEST, {"file":self.text.filepath,
                                          "tmp":self.tmp.name}) + list(args)
        self.term.queue(command, condition=(0).__eq__)

    @staticmethod
    def format(text:list[str], kwargs:dict[str,str]) -> list[str]:
        text:list[str] = text.copy()
        for key, value in kwargs.items():
            for i in range(len(text)):
                if "{"+key+"}" in text[i]:
                    text[i] = text[i].replace("{"+key+"}", value)
        return text