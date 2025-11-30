from __future__ import annotations
from sys import executable
import os

from ..runmanager import RunManager as BaseRunManager

# We need a better way of getting the default bashrc file
DEFAULT_BASHRC:list[str] = [os.path.join(os.path.expanduser("~"), ".bashrc")]
DEFAULT_BASHRC:list[str] = list(filter(os.path.exists,
                                       map(os.path.abspath, DEFAULT_BASHRC)))


class RunManager(BaseRunManager):
    __slots__ = ()

    COMPILE:list[str] = []
    RUN:list[str] = ["bash", "--rcfile", "{tmp}/bashrc", "-i"]

    def cd(self, *, print_str:str="") -> None:
        super().cd(os.path.dirname(self.text.filepath), print_str=print_str)

    def execute(self, args:Iterable[str]) -> None:
        tmp:str = self.tmp.name
        with open(f"{tmp}/bashrc", "w") as file:
            for bashrc in DEFAULT_BASHRC:
                file.write(f"source {bashrc!r}\n")
            file.write(f"source {self.text.filepath!r}\n")
        super().execute(args)
