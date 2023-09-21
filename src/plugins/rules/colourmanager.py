from __future__ import annotations
from idlelib.colorizer import ColorDelegator, make_pat
from idlelib.percolator import Percolator
import tkinter as tk
import re

from .baserule import Rule


class ColourConfig(dict):
    __slots__ = ()

    def __init__(self) -> ColourConfig:
        super().__init__({
                           "SYNC":       dict(),
                           "TODO":       dict(),
                           "error":      dict(),
                           "hit":        dict(),
                         })


# /usr/lib/python3.10/idlelib/colorizer.py
class Colorizer(ColorDelegator):
    def __init__(self) -> Colorizer:
        super().__init__()
        self.tagdefs:dict[str,str] = ColourConfig()
        self.idprog = re.compile(r"\s+(\w+)")
        self.text:tk.Text = None
        self.prog = re.compile("(?:.*)", re.M|re.S) # Kind of matches nothing
        self.close()

    def close(self) -> None:
        self.colorizer_on:bool = False
        return super().close()

    def apply_colorizer(self, text:tk.Text) -> None:
        self.percolator:Percolator = Percolator(text)
        self.percolator.insertfilter(self)
        self.text:tk.Text = text

    def _add_tag(self, start, end, head, tag):
        tag:str = "SYNC" if tag == "SYNC" else tag.lower()
        kw_groups = ("match_softkw", "case_softkw", "case_softkw2",
                     "case_default_underscore")
        self.tag_add("keyword" if tag in kw_groups else tag,
                     f"{head}+{start:d}c", f"{head}+{end:d}c")

    def toggle_colorize_event(self, event:tk.Event=None) -> str:
        self.colorizer_on:bool = not self.colorizer_on
        return super().toggle_colorize_event(event)

    def insert(self, index:str, chars:str, tags=None) -> None:
        data:tuple = (index, chars, tags)
        self.text.event_generate("<<Before-Insert>>", data=data)
        super().insert(index, chars, tags)
        self.text.event_generate("<<After-Insert>>", data=data)

    def delete(self, index1:str, index2:str=None) -> None:
        data:tuple = (index1, index2)
        self.text.event_generate("<<Before-Delete>>", data=data)
        super().delete(index1, index2)
        self.text.event_generate("<<After-Delete>>", data=data)


class ColourManager(Rule):
    __slots__ = "old_bg", "old_fg", "old_insertbg", "colorizer", "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ColourManager:
        super().__init__(plugin, text, ons=())
        self.text:tk.Text = self.widget
        self.colorizer:Colorizer = Colorizer()
        self.apply_colorizer()

    def apply_colorizer(self) -> None:
        self.colorizer.apply_colorizer(self.text)

    def attach(self) -> None:
        super().attach()
        self.old_bg:str = self.text.cget("bg")
        self.old_fg:str = self.text.cget("fg")
        self.old_insertbg:str = self.text.cget("insertbackground")
        self.text.config(bg="black", fg="white", insertbackground="white",
                         takefocus=True)

    def detach(self) -> None:
        super().detach()
        self.text.config(bg=self.old_bg, fg=self.old_fg,
                         insertbackground=self.old_insertbg)
