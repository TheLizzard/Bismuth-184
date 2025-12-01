from __future__ import annotations
from shutil import which

from ..runmanager import RunManager as BaseRunManager
from ..helpers.compiler import Compiler


EXE:str = which("gcc")
WARNINGS:tuple[str] = ("-Wall", "-Wextra", "-Wshadow", "-Warray-bounds",
                       "-Wdangling-else", "-Wnull-dereference",
                       "-Wswitch-enum", "-Wformat-security", "-Wuninitialized",
                       "-Wconversion", "-Wpointer-arith")
DEFAULT_FLAGS:list[str] = [
                       "-flto=5", # Link Time Optimisation
                       "-O3",
                       "-std=c17",
                       "-funroll-all-loops",
                          ] + list(WARNINGS)
DEBUG_MODE:bool = True
if DEBUG_MODE:
    # https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html
    DEFAULT_FLAGS += [
                       # Retain source code debugging/symbol info
                       "-g",
                       # Exports source code symbols
                       "-rdynamic",
                       # Detect memoty leaks
                       "-fsanitize=leak",
                       # Detect user-after-frees
                       "-fsanitize=address",
                       # Detect undefined behavior
                       "-fsanitize=undefined",
                       # Detect use-after-scope
                       "-fsanitize-address-use-after-scope",
                     ]


GET_INCLUDES_CMD:list[str] = [EXE, "-MT", "", "-MM", "-MG"]

HEADER_EXTS:set[str] = {".h"}
SRC_EXTS:set[str] = {".c"}


class RunManager(BaseRunManager):
    __slots__ = "libs"

    RUN:list[str] = ["{tmp}/executable"]

    def compile(self) -> bool:
        for ext in SRC_EXTS:
            if self.text.filepath.endswith(ext): break
        else:
            return False
        self.term.queue(["print!", self.center("Pre-Compiling", "-")],
                        condition=(0).__eq__)
        compiler:Compiler = Compiler(self.effective_cwd, DEFAULT_FLAGS, EXE,
                                     GET_INCLUDES_CMD, HEADER_EXTS, SRC_EXTS)
        compiler.add_root(self.text.filepath)
        command:list[str] = compiler.get_cmd()
        if compiler.links:
            super().set_env_var("LIBRARY_PATH", set(compiler.links))
            super().set_env_var("LD_LIBRARY_PATH", set(compiler.links))
        cmd:str = " ".join(command) + "\n"
        self.term.queue(["print!", cmd], condition=(0).__eq__)
        if compiler.error:
            msg:str = compiler.error + "\n"
            self.term.queue(["print!", msg], condition=(0).__eq__)
            return False
        return super().compile(command=command,
                               print_str=self.center("Compiling", "-"))

    def execute(self, args:Iterable[str]) -> None:
        super().execute(args, print_str=self.center("Running", "-"))
