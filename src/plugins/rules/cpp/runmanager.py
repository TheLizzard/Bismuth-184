from __future__ import annotations
# from idlelib.colorizer import matched_named_groups, idprog
from subprocess import Popen, PIPE, DEVNULL, TimeoutExpired
from os import path, readlink, listdir
from collections import defaultdict
from shutil import which
from os import environ
from re import findall
import shlex

from ..runmanager import RunManager as BaseRunManager, PRINTF
from .colourmanager import make_pat


GPP_EXE:str = which("g++")
WARNINGS:tuple[str] = ("-Wall", "-Wextra", "-Wshadow", "-Warray-bounds",
                       "-Wdangling-else", "-Wnull-dereference",
                       "-Wswitch-enum", "-Wformat-security", "-Wuninitialized",
                       "-Wconversion", "-Wpointer-arith")
DEFAULT_FLAGS:list[str] = [
                       "-flto=5", # Link Time Optimisation
                       "-O3",
                       "-std=c++20",
                       "-funroll-all-loops",
                       "-lmpfr", # GNU Multiple Precision Float Library
                       "-lgmp", # GNU Multiple Precision Arithmetic Library
                       "-lm", # C++ Maths Library (not too sure?)
                          ] + list(WARNINGS)
DEBUG_MODE:bool = True
if DEBUG_MODE:
    DEFAULT_FLAGS += ["-g", "-rdynamic"]


GET_INCLUDES_CMD:list[str] = [GPP_EXE, "-MT", "", "-MM", "-MG"]


# TODO: this needs majour reworking
class RunManager(BaseRunManager):
    __slots__ = "libs"

    RUN:list[str] = ["{tmp}/executable"]

    def compile(self, *, print_str:str="") -> bool:
        if not self.text.filepath.endswith(".cpp"):
            return False
        compiler:Compiler = Compiler(self.effective_cwd)
        compiler.add_root(self.text.filepath)
        command:list[str] = compiler.get_cmd()
        if compiler.links:
            super().set_env_var("LIBRARY_PATH", set(compiler.links))
            super().set_env_var("LD_LIBRARY_PATH", set(compiler.links))
        cmd:str = " ".join(command) + "\n\n"
        self.term.queue([*PRINTF, cmd], condition=(0).__eq__)
        if compiler.error:
            self.term.queue([*PRINTF, compiler.error], condition=(0).__eq__)
            return False
        return super().compile(print_str=print_str, command=command)


class Compiler:
    __slots__ = "includes", "files", "links", "_visited", "_symlinks", \
                "flags", "error", "effective_cwd"

    def __init__(self, effective_cwd:str) -> Compiler:
        self.effective_cwd:str = effective_cwd
        self.error:str = ""
        self._visited:set[str] = set()
        self.files:set[str] = set()
        self.includes:set[str] = set()
        self.links:dict[str:set[str]] = defaultdict(set)
        self._symlinks:dict[str:str] = {}
        self.flags:set[str] = set()

    def get_cmd(self) -> list[str]:
        command:list[str] = [GPP_EXE, "-o", "{tmp}/executable"]

        # Includes before files
        for include in self.includes:
            command += [f"-I{include}"]
        # Files + flags
        command += sorted(self.files, key=len, reverse=True)
        command += self._get_flags()
        # Linked libraries
        for folder, libs in sorted(self.links.items()):
            if folder:
                command += [f"-L{folder}"]
            for lib in libs:
                command += [f"-l{lib}"]

        return command

    def add_root(self, filepath:str) -> Compiler:
        filepath:str = path.abspath(filepath)
        if (not path.exists(filepath)) or (filepath in self.files):
            return self
        flags_folderpath:str = path.join(path.dirname(filepath), "cpp-flags")
        if path.exists(flags_folderpath):
            if path.isdir(flags_folderpath):
                self.change_flags(flags_folderpath)
        self._add(filepath)
        return self

    def _add(self, filepath:str) -> None:
        filepath:str = path.abspath(filepath)
        if (not path.exists(filepath)) or (filepath in self.files):
            return None
        if not (filepath.endswith(".cpp") or filepath.endswith(".c")):
            return None
        self.files.add(filepath)
        # print(f"[DEBUG]: Adding {filepath!r}")

        proc:Popen = Popen(GET_INCLUDES_CMD+[filepath], shell=False,
                           stdout=PIPE, stderr=PIPE, stdin=DEVNULL,
                           env=environ, cwd=self.effective_cwd)
        try:
            proc.wait(3)
        except TimeoutExpired:
            proc.kill()
            self.error:str = "g++ -MM took too long"
            return None
        includes:str = proc.stdout.read().decode("utf-8", errors="ignore")
        if not includes.startswith(":"):
            self.error:str = f"g++ -MM unexpected output: {includes!r}"
            return None
        parsed_includes:str = includes.removeprefix(":") \
                                      .replace("\\\n", "") \
                                      .replace("\n", " ") \
                                      .strip(" ")

        base:str = path.dirname(path.abspath(filepath))
        # for include in findall(r"(?:[^ \\]|\\.)+", parsed_includes):
        for include in shlex.split(parsed_includes):
            if not include: continue
            full_include:str = path.join(base, include)
            for inc_ext in (".h", ".hpp", ".h++"):
                if full_include.endswith(inc_ext):
                    pure_full_include:str = full_include.removesuffix(inc_ext)
                    for c_ext in (".c", ".cpp", ".c++"):
                        full_c:str = pure_full_include + c_ext
                        if path.exists(full_c):
                            self._add(full_c)
            self._add_superlib_folder(path.dirname(full_include))

        """
        self.files.add(filepath)
        self._add_superlib_folder(path.dirname(filepath))
        self._add(filepath)
        return self

    def _add(self, filepath:str) -> None:
        if not path.exists(filepath):
            return None
        self._visited.add(filepath)
        folder:str = path.dirname(filepath)
        for include in self._get_includes(filepath):
            include_fullpath:str = path.join(folder, include)
            if include in self._visited:
                continue
            if not path.exists(include_fullpath):
                continue

            self._visited.add(include_fullpath)
            self._add(include_fullpath)
            if include_fullpath.endswith(".c"):
                self.add(include_fullpath)
            elif include_fullpath.endswith(".cpp"):
                self.add(include_fullpath)
            elif include_fullpath.endswith(".h"):
                pure:str = include_fullpath.removesuffix(".h")
                self.add(pure + ".c")
                self.add(pure + ".cpp")
            elif include_fullpath.endswith(".hpp"):
                pure:str = include_fullpath.removesuffix(".hpp")
                self.add(pure + ".c")
                self.add(pure + ".cpp")

    def _get_includes(self, filepath:str) -> set[str]:
        print("[LOG-C++-RUN]: Checking:", filepath.split("/")[-1])
        if not path.exists(filepath):
            return set()
        # print("[LOG-C++-RUN]: Reading:", filepath.split("/")[-1])
        with open(filepath, "r") as file:
            code:str = file.read()
        includes:set[str] = set()
        last_include_start:int = None
        for m in PROG.finditer(code):
            for name, matched_text in matched_named_groups(m):
                a, b = m.span(name)
                if name == "preprocessor":
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
        """

    def _get_flags(self) -> list[str]:
        flags:set[str] = set(DEFAULT_FLAGS)
        for flag in self.flags:
            if flag.startswith("+"):
                flags.discard("-" + flag.removeprefix("+"))
            elif flag.startswith("-"):
                flags.add(flag)
        return sorted(flags)

    def change_flags(self, folder:str) -> None:
        """
        - cpp-flags
            # +std=c++20     To remove the default -std=c++20
            # -std=c++14     To add -std=c++14
        # file.cpp
        """
        for file in listdir(folder):
            filepath:str = path.join(folder, file)
            if not path.isfile(filepath):
                continue
            self.flags.add(file)

    def _add_superlib_folder(self, folder:str) -> None:
        """
        - src-cpp
            - supername
               - include-sysliba => /usr/include/syslib1
               - include-syslibb => /usr/include/syslib2
               - libtorch => /usr/lib/   libtorch.so
               - libgmp1 => /usr/lib/    libgmp1.so
               - lib!gmp2 => /usr/lib64
            - curses
               # libncurses              -lncurses
        # file.cpp
        """
        root:str = path.join(folder, "cpp-libs")
        if not path.exists(root):
            return
        if not path.isdir(root):
            return None
        for super_libname in listdir(root):
            super_libfolder:str = path.join(root, super_libname)
            if not path.isdir(super_libfolder):
                continue
            self._add_lib_folder(super_libfolder)

    def _add_lib_folder(self, super_libfolder:str) -> None:
        for folder in listdir(super_libfolder):
            fullfolder:str = path.join(super_libfolder, folder)

            try:
                target:str = readlink(fullfolder)
                if target in self._symlinks:
                    fullfolder:str = self._symlinks[target]
                else:
                    self._symlinks[target] = fullfolder
            except OSError:
                pass

            if folder.startswith("include") and fullfolder:
                self.includes.add(fullfolder)

            elif folder.startswith("lib!"):
                if fullfolder not in self.links:
                    self.links[fullfolder] = set()

            elif folder.startswith("lib"):
                lib:str = folder.removeprefix("lib")
                if path.isfile(fullfolder):
                    fullfolder:str = ""
                self.links[fullfolder].add(lib)


PROG = make_pat()