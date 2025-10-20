from __future__ import annotations
import tkinter as tk

from .baserule import Rule

DEBUG:bool = False


class ReparentManager(Rule):
    __slots__ = "target", "manager_type", "manager_state", "frame"
    SPACE_SIZE:int = 5

    def __init__(self, plugin:BasePlugin, widget:tk.Misc):
        super().__init__(plugin, widget, ons=())
        # Target is the widget that will get reparented:
        #   the tk.Text if widget is tk.Text and
        #   the tk.Canvas if widget is BetterText
        self.target:tk.Misc = widget
        self.frame:tk.Frame = tk.Frame(plugin.master, highlightthickness=0,
                                       bd=0)
        self.frame.grid_columnconfigure(self.SPACE_SIZE, weight=1)
        self.frame.grid_rowconfigure(self.SPACE_SIZE, weight=1)

    def __new__(Cls:type, plugin:BasePlugin, widget:tk.Misc, *args, **kwargs):
        reparenter = getattr(widget, "reparenter", None)
        if reparenter is not None:
            return reparenter
        else:
            self = super().__new__(Cls, *args, **kwargs)
            widget.reparenter = self
            return self

    def attach(self) -> None:
        super().attach()
        self.frame.config(bg=self.target.cget("bg"))
        self.manager_type:str = self.target.winfo_manager()
        if self.manager_type == "pack":
            self.manager_state:dict = self.target.pack_info()
            self.target.pack_forget()
            self.frame.pack(**self.manager_state)
        elif self.manager_type == "grid":
            self.manager_state:dict = self.target.grid_info()
            self.target.grid_forget()
            self.frame.grid(**self.manager_state)
        elif self.manager_type == "place":
            self.manager_state:dict = self.target.place_info()
            self.target.place_forget()
            self.frame.place(**self.manager_state)
        elif self.manager_type == "wm":
            raise NotImplementedError("Can't work with toplevel widgets.")
        else:
            raise NotImplementedError("Unreachable code")
            raise NotImplementedError(f"Can't work with the " \
                                      f"{self.manager_type} manager")
        self.target.grid(in_=self.frame, sticky="news", row=self.SPACE_SIZE,
                         column=self.SPACE_SIZE)
        tk.Misc.lift(self.target)
        self.widget.add_widget = self.add_widget

    def detach(self) -> None:
        super().detach()
        if self.manager_type == "pack":
            self.frame.pack_forget()
            self.target.pack(**self.manager_state)
        elif self.manager_type == "grid":
            self.frame.grid_forget()
            self.target.grid(**self.manager_state)
        elif self.manager_type == "place":
            self.frame.place_forget()
            self.target.place(**self.manager_state)
        else:
            raise NotImplementedError("Unreachable code")

    def add_widget(self, widget:tk.Misc, *, row:int=0, column:int=0,
                   sticky:str="news", **kwargs:dict) -> None:
        column += self.SPACE_SIZE
        row += self.SPACE_SIZE
        if (column < 0) or (row < 0):
            raise RuntimeError("row/column are too negative")
        if DEBUG:
            print(f"[DEBUG] adding {widget} to {row=}, {column=}")
        widget.grid(in_=self.frame, row=row, column=column, sticky=sticky,
                    **kwargs)
        # widget.tk.call("raise", widget._w)
        self.frame.lower()
