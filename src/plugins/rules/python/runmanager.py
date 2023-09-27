from __future__ import annotations

from ..runmanager import RunManager as BaseRunManager


class RunManager(BaseRunManager):
    __slots__ = ()

    # COMPILE:list[str] = ["python3", "-m", "py_compile", "{file}"]
    RUN:list[str] = ["python3", "-i", "{file}"]