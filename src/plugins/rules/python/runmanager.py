from __future__ import annotations
import os

from ..runmanager import RunManager as BaseRunManager


class RunManager(BaseRunManager):
    __slots__ = ()

    # COMPILE:list[str] = ["python3", "-m", "py_compile", "{file}"]
    COMPILE:list[str] = []
    RUN:list[str] = ["python3", "-i", "{file}"]
    # RUN:list[str] = ["bash", "-c", "source env/bin/activate && python3 -i {file}"]

    def cd(self, *, print_str:str="") -> None:
        super().cd(os.path.dirname(self.text.filepath), print_str=print_str)