from __future__ import annotations

from ..runmanager import RunManager as BaseRunManager


class RunManager(BaseRunManager):
    __slots__ = ()

    COMPILE:list[str] = ["g++", "{file}", "-o", "{tmp}/executable.o"]
    RUN:list[str] = ["{tmp}/executable.o"]