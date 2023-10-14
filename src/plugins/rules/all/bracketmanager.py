from __future__ import annotations

from ..bracketmanager import BracketManager as BaseBracketManager


class BracketManager(BaseBracketManager):
    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if on == "'":
            return False
        return super().applies(event, on)