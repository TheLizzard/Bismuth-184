from __future__ import annotations
from idlelib.colorizer import ColorDelegator, make_pat
import tkinter as tk
import re

from .baserule import Rule


class ColourConfig(dict):
    __slots__ = ()

    def __init__(self, kwargs:dict[str:dict[str:str]]={}) -> ColourConfig:
        super().__init__({
                           "SYNC":  dict(),
                           "TODO":  dict(),
                           "error": dict(),
                           "hit":   dict(background="blue", foreground="white"),
                           **kwargs
                        })


class ColourManager(Rule, ColorDelegator):
    __slots__ = "old_bg", "old_fg", "old_insertbg", "colorizer", "text", \
                "coloriser"
    REQUESTED_LIBRARIES:tuple[str] = "insertdeletemanager"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ColourManager:
        evs:tuple[str] = (
                           "<<Raw-After-Insert>>", "<<Raw-After-Delete>>",
                         )
        super().__init__(plugin, text, ons=evs)
        self.delegate:tk.Text = text
        self.coloriser:bool = False
        self.text:tk.Text = text
        ColorDelegator.init_state(self)
        ColorDelegator.close(self)
        self.init()

    def init(self) -> None:
        self.tagdefs:dict[str,str] = ColourConfig()
        self.idprog = re.compile(r"\s+(\w+)")
        self.prog = re.compile("(?:.*)", re.M|re.S) # Kind of matches nothing

    def __getattr__(self, key:str) -> object:
        return getattr(self.text, key)

    def setdelegate(self, delegate:object) -> None:
        raise RuntimeError("Unreachable")

    def attach(self) -> None:
        super().attach()
        self.old_bg:str = self.text.cget("bg")
        self.old_fg:str = self.text.cget("fg")
        self.old_insertbg:str = self.text.cget("insertbackground")
        self.text.config(bg="black", fg="white", insertbackground="white",
                         takefocus=True)
        # Start recolorising
        self.config_colors()
        if not self.coloriser:
            self.coloriser:bool = True
            self.toggle_colorize_event(self)
        self.notify_range("1.0", "end")
        # Bring forward hit tag
        try:
            self.text.tag_raise("hit")
        except tk.TclError:
            pass

    def detach(self) -> None:
        super().detach()
        self.coloriser:bool = False
        ColorDelegator.close(self)
        self.removecolors()
        self.text.config(bg=self.old_bg, fg=self.old_fg,
                         insertbackground=self.old_insertbg)

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if on == "<raw-after-insert>":
            start, data, _ = event.data["abs"]
            end:str = self.text.index(f"{start} +{len(data)}c")
        elif on == "<raw-after-delete>":
            start, _ = event.data["abs"]
            end:str = None
        return start, end, True

    def do(self, _:str, start:str, end:str|None) -> Break:
        self.notify_range(start, end)
        return False

    # def notify_range(self, start:str, end:str|None=None) -> None:
    #     print((start, end))
    #     super().notify_range(start, end)

    def _add_tag(self, start, end, head, tag):
        tag:str = "SYNC" if tag == "SYNC" else tag.lower()
        kw_groups = ("match_softkw", "case_softkw", "case_softkw2",
                     "case_default_underscore")
        self.tag_add("keyword" if tag in kw_groups else tag,
                     f"{head}+{start:d}c", f"{head}+{end:d}c")