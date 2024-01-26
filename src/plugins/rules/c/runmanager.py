from __future__ import annotations

from ..runmanager import RunManager as BaseRunManager


class RunManager(BaseRunManager):
    __slots__ = ()

    COMPILE:list[str] = ["gcc", "{file}", "-o", "{tmp}/executable"]
    RUN:list[str] = ["{tmp}/executable"]