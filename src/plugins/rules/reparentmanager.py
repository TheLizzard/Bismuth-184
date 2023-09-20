from __future__ import annotations
import tkinter as tk

from .baserule import Rule

DEBUG:bool = False


class WidgetReparenterManager(Rule):
    __slots__ = "widget", "manager_type", "manager_state", "frame"

    SPACE_SIZE:int = 5

    def __init__(self, plugin:BasePlugin, widget:tk.Misc):
        super().__init__(plugin, widget, ons=())
        self.frame:tk.Frame = tk.Frame(widget.master, highlightthickness=0,
                                       bd=0)
        self.frame.grid_columnconfigure(self.SPACE_SIZE, weight=1)
        self.frame.grid_rowconfigure(self.SPACE_SIZE, weight=1)

    def attach(self) -> None:
        super().attach()
        self.frame.config(bg=self.widget.cget("bg"))
        self.manager_type:str = self.widget.winfo_manager()
        if self.manager_type == "pack":
            self.manager_state:dict = self.widget.pack_info()
            self.widget.pack_forget()
            self.frame.pack(**self.manager_state)
        elif self.manager_type == "grid":
            self.manager_state:dict = self.widget.grid_info()
            self.widget.grid_forget()
            self.frame.grid(**self.manager_state)
        elif self.manager_type == "place":
            self.manager_state:dict = self.widget.place_info()
            self.widget.place_forget()
            self.frame.place(**self.manager_state)
        elif self.manager_type == "wm":
            raise NotImplementedError("Can't work with toplevel widgets.")
        else:
            raise NotImplementedError("Unreachable code")
            raise NotImplementedError("Can't work with the " \
                                      f"{self.manager_type} manager")
        self.widget.grid(in_=self.frame, sticky="news", row=self.SPACE_SIZE,
                         column=self.SPACE_SIZE)
        self.widget.lift()

        self.widget.add_widget = self.add_widget

    def detach(self) -> None:
        super().dettach()
        if self.manager_type == "pack":
            self.frame.pack_forget()
            self.widget.pack(**self.manager_state)
        elif self.manager_type == "grid":
            self.frame.grid_forget()
            self.widget.grid(**self.manager_state)
        elif self.manager_type == "place":
            self.frame.place_forget()
            self.widget.place(**self.manager_state)
        else:
            raise NotImplementedError("Unreachable code")

    def add_widget(self, widget:tk.Misc, row:int=0, column:int=0,
                   sticky:str="news", **kwargs:dict) -> None:
        column += self.SPACE_SIZE
        row += self.SPACE_SIZE
        if (column < 0) or (row < 0):
            raise RuntimeError("row/column are too negative")
        if DEBUG:
            print(f"[DEBUG] adding {widget} to {row=}, {column=}")
        widget.grid(in_=self.frame, row=row, column=column, sticky=sticky,
                    **kwargs)
