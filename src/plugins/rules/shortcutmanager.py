from __future__ import annotations
import tkinter as tk

from .baserule import Rule

SIMPLE_TEXT:str = "SimpleText"
DEBUG:bool = False


class RemoveShortcuts(Rule):
    __slots__ = "text"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        super().__init__(plugin, text, ())
        self.text:tk.Text = self.widget

    def attach(self) -> None:
        super().attach()
        if not getattr(tk, "simpletag", False):
            self.create_simple_tag()
            tk.simpletag:bool = True

        text_tags:tuple[str] = self.text.bindtags()
        text_tags:tuple[str] = tuple(SIMPLE_TEXT if t == "Text" else t \
                                     for t in text_tags)
        self.text.bindtags(text_tags)

    def detach(self) -> None:
        super().detach()
        text_tags:tuple[str] = self.text.bindtags()
        text_tags:tuple[str] = tuple("Text" if t == SIMPLE_TEXT else t \
                                     for t in text_tags)
        self.text.bindtags(text_tags)

    def create_simple_tag(self) -> None:
        bindings:tuple[str] = self.text._bind(("bind", "Text"), None, None, None)
        to_remove:set[str] = set()
        for binding in bindings:
            if binding in ("<B2-Motion>", "<Button-2>"):
                to_remove.add(binding)
            if binding.startswith("<Control-"):
                b:str = binding.removeprefix("<Control-").replace("Shift-", "")
                b:str = b.replace("Key-", "").removesuffix(">")
                if (b in "htokdi") or ("Tab" in b) or ("Home" in b):
                    to_remove.add(binding)
                if "space" in b:
                    to_remove.add(binding)
                if ("Next" in b) or ("Prior" in b) or ("End" in b):
                    to_remove.add(binding)
            if "Meta-Key" in binding:
                to_remove.add(binding)
            if ("B1" in binding) or ("Button-1" in binding):
                to_remove.add(binding)
            if "Release-1" in binding:
                to_remove.add(binding)
            if ("Select" in binding) or ("Tab" in binding):
                to_remove.add(binding)
            if ("Key-Prior" in binding) or ("Key-Next" in binding):
                to_remove.add(binding)
            if ("Prev" in binding) or ("Next" in binding):
                to_remove.add(binding)
            if ("LineEnd" in binding) or ("LineStart" in binding):
                to_remove.add(binding)
            if binding in ("<<Cut>>", "<<Copy>>", "<<Paste>>"):
                to_remove.add(binding)
            if binding in ("<<Undo>>", "<<Redo>>", "<<Clear>>"):
                to_remove.add(binding)

        if DEBUG: print(f"[DEBUG]: {to_remove=}")
        for binding in set(bindings) - to_remove:
            cmd:str = self.text._bind(("bind", "Text"), binding, None, None)
            self.text._bind(("bind", SIMPLE_TEXT), binding, cmd, None)
            if DEBUG: print(f"[DEBUG]: {binding}: {cmd!r}")
        # Insert tab and break
        tab_cmd:str = "\n\t" + r"tk::TextInsert %W \t" + "\n\t" + "break" + "\n"
        self.text._bind(("bind", SIMPLE_TEXT), "<Tab>", tab_cmd, None)