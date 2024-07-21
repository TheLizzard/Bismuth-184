from __future__ import annotations
from idlelib.colorizer import matched_named_groups, idprog
import os.path

from ..runmanager import RunManager as BaseRunManager
from .colourmanager import make_pat


WARNINGS:tuple[str] = ("-Wall", "-Wextra", "-Wshadow", "-Warray-bounds",
                       "-Wdangling-else", "-Wnull-dereference",
                       "-Wswitch-enum", "-Wformat-security", "-Wuninitialized",
                       "-Wconversion", "-Wpointer-arith")
DEBUG_MODE:bool = True

class RunManager(BaseRunManager):
    __slots__ = ()

    RUN:list[str] = ["{tmp}/executable"]

    def compile(self, *, print_str:str="") -> bool:
        file:str = self.text.filepath
        if file.endswith(".h"):
            return False
        assert file.endswith(".c"), f"{self.text.filepath!r} must be .h or .c file"
        files:set[str] = set()
        RunManager.get_c_files(file, files)
        files:list[str] = list(filter(os.path.exists, files))
        command:list[str] = ["gcc", *WARNINGS, "-o", "{tmp}/executable", "-O3",
                             *files, "-lm", "-funroll-all-loops"]
        if DEBUG_MODE:
            command += ["-g", "-rdynamic"]
        return super().compile(print_str=print_str, command=command)

    @staticmethod
    def get_c_files(filepath:str, results:set) -> None:
        if filepath.endswith(".c"):
            header, c = filepath.removesuffix(".c")+".h", filepath
        else:
            header, c = filepath, filepath.removesuffix(".h")+".c"
        if c in results:
            return None
        results.add(c)
        RunManager.get_headers(c, results)
        RunManager.get_headers(header, results)

    @staticmethod
    def get_headers(filepath:str, results:set[str]) -> None:
        folder:str = os.path.dirname(filepath)
        for header in RunManager._get_headers(filepath):
            if header in results:
                continue
            RunManager.get_c_files(os.path.join(folder, header), results)

    @staticmethod
    def _get_headers(filepath:str) -> set[str]:
        if not os.path.exists(filepath):
            return set()
        with open(filepath, "r") as file:
            code:str = file.read()
        includes:set[str] = set()
        last_include_start:int = None
        for m in PROG.finditer(code):
            for name, matched_text in matched_named_groups(m):
                a, b = m.span(name)
                if name == "include":
                    last_include_start:int = b
                if name == "string":
                    if last_include_start == a:
                        include:str = code[a:b]
                        if include.startswith('"') or include.endswith('"'):
                            include:str = include.removeprefix('"') \
                                                 .removesuffix('"')
                        elif include.startswith("<") or include.endswith(">"):
                            include:str = include.removeprefix("<") \
                                                 .removesuffix(">")
                        includes.add(include)
        return includes


PROG = make_pat()