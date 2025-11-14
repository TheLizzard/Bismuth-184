from __future__ import annotations
from subprocess import Popen, PIPE, DEVNULL, TimeoutExpired
from collections import defaultdict
from os import path, listdir
from os import environ
import shlex


class Compiler:
    """
    % Comment
    % Hashtag means a file (can be blank)
    % Dash means a folder
    % Arrow means a symbolic link

    - cpp-libs
        - library-bundle-name
           - include-sysliba => /usr/include/syslib1 % For the -I flag
           - include-syslibb => /usr/include/syslib2 % For the -I flag
           - libtorch => /usr/lib/   % libtorch.so
           - libgmp1 => /usr/lib/    % libgmp1.so
           - lib!gmp2 => /usr/lib64  % For lib64
        - curses
           # libncurses              % For "-lncurses" flag
    - cpp-flags
        # +std=c++20     % To remove the default -std=c++20
        # -std=c++14     % To add -std=c++14
    # file.c
    """

    __slots__ = "includes", "files", "links", "_visited", "_symlinks", \
                "flags", "error", "effective_cwd", "default_flags", \
                "compile_exe", "get_includes_cmd", "header_exts", "src_exts"

    def __init__(self, effective_cwd:str, default_flags:set[str],
                 compile_exe:list[str], get_includes_cmd:list[str],
                 header_exts:set[str], src_exts:set[str]) -> Compiler:

        self.get_includes_cmd:list[str] = get_includes_cmd.copy()
        self.default_flags:set[str] = set(default_flags)
        self.header_exts:set[str] = header_exts
        self.compile_exe:str = compile_exe
        self.src_exts:set[str] = src_exts

        self.effective_cwd:str = effective_cwd

        self.error:str = ""
        self._visited:set[str] = set()
        self.files:set[str] = set()
        self.includes:set[str] = set()
        self.links:dict[str:set[str]] = defaultdict(set)
        self._symlinks:dict[str:str] = {}
        self.flags:set[str] = set()

    def get_cmd(self) -> list[str]:
        command:list[str] = [self.compile_exe, "-o", "{tmp}/executable"]

        # Includes before files
        for include in self.includes:
            command += [f"-I{include}"]
        # Files + flags
        command += sorted(self.files, key=len, reverse=True)
        command += self._get_flags()
        # Linked libraries
        for folder, libs in sorted(self.links.items()):
            if folder:
                command += [f"-L{path.realpath(folder)}"]
            for lib in libs:
                command += [f"-l{lib}"]

        return command

    def add_root(self, filepath:str) -> Compiler:
        filepath:str = path.abspath(filepath)
        if (not path.exists(filepath)) or (filepath in self.files):
            return self
        for ext in self.src_exts:
            ext:str = ext.removeprefix(".")
            flags_path:str = path.join(path.dirname(filepath), ext+"-flags")
            if path.exists(flags_path) and path.isdir(flags_path):
                self.change_flags(flags_path)
        self._add(filepath)
        return self

    def _add(self, filepath:str) -> None:
        filepath:str = path.abspath(filepath)
        if (not path.exists(filepath)) or (filepath in self.files):
            return None
        for ext in self.src_exts:
            if filepath.endswith(ext): break
        else:
            return None
        self.files.add(filepath)
        # print(f"[DEBUG]: Adding {filepath!r}")

        proc:Popen = Popen(self.get_includes_cmd+[filepath], shell=False,
                           stdout=PIPE, stderr=PIPE, stdin=DEVNULL,
                           env=environ, cwd=self.effective_cwd)
        try:
            proc.wait(3)
        except TimeoutExpired:
            proc.kill()
            self.error:str = "gcc -MM took too long"
            return None
        includes:str = proc.stdout.read().decode("utf-8", errors="ignore")
        if not includes.startswith(":"):
            self.error:str = f"gcc -MM unexpected output: {includes!r}"
            return None
        parsed_includes:str = includes.removeprefix(":") \
                                      .replace("\\\n", "") \
                                      .replace("\n", " ") \
                                      .strip(" ")

        base:str = path.dirname(path.abspath(filepath))
        for include in shlex.split(parsed_includes):
            if not include: continue
            full_include:str = path.join(base, include)
            for inc_ext in self.header_exts:
                if full_include.endswith(inc_ext):
                    pure_full_include:str = full_include.removesuffix(inc_ext)
                    for c_ext in self.src_exts:
                        full_c:str = pure_full_include + c_ext
                        if path.exists(full_c):
                            self._add(full_c)
            self._add_superlib_folder(path.dirname(full_include))

    def _get_flags(self) -> list[str]:
        flags:set[str] = self.default_flags
        for flag in self.flags:
            if flag.startswith("+"):
                flags.discard("-" + flag.removeprefix("+"))
            elif flag.startswith("-"):
                flags.add(flag)
        return sorted(flags)

    def change_flags(self, folder:str) -> None:
        for file in listdir(folder):
            filepath:str = path.join(folder, file)
            if not path.isfile(filepath):
                continue
            self.flags.add(file)

    def _add_superlib_folder(self, folder:str) -> None:
        for ext in self.src_exts:
            root:str = path.join(folder, ext.removeprefix(".")+"-libs")
            if not (path.exists(root) and path.isdir(root)):
                continue
            for super_libname in listdir(root):
                super_libfolder:str = path.join(root, super_libname)
                if not path.isdir(super_libfolder):
                    continue
                self._add_lib_folder(super_libfolder)

    def _add_lib_folder(self, super_libfolder:str) -> None:
        for folder in listdir(super_libfolder):
            fullfolder:str = path.join(super_libfolder, folder)

            try:
                target:str = path.realpath(fullfolder)
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
