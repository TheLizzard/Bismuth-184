from __future__ import annotations
from sys import executable
import os

from ..runmanager import RunManager as BaseRunManager

# We need a better way of getting the default bashrc file
DEFAULT_BASHRC:list[str] = [
    "/etc/bash.bashrc",
    os.path.join(os.path.expanduser("~"),".bashrc"),
]
DEFAULT_BASHRC:list[str] = list(filter(os.path.exists,
                                       map(os.path.abspath, DEFAULT_BASHRC)))

PREAMBLE:str = """\
failed_bashrc() {
    echo -e "\\x1b[91m[ERROR]: bashrc file failed: \\x1b[92m$1\\x1b[0m"
    exit 1
}

_shell_set_opts="$(set -o)"
_shell_shopt_opts="$(shopt -p)"

restore_set_opt() {
    while IFS= read -r line; do
        line="$(echo "$line" | tr "\t" " " | tr " " "\\n")"
        name="$(echo "$line" | head -1)"
        status="$(echo "$line" | tail -1)"
        case "$status" in
            on)  set -o "$name" ;;
            off) set +o "$name" ;;
            *) \
                echo -e "\\x1b[91m[ERROR]: \
Unknown \\x1b[92m$name\\x1b[91m status: \\x1b[92m$status\\x1b[0m"
        esac
    done <<< "$_shell_set_opts"
}
"""

POSTAMBLE:str = """
# Reset `set -X`
restore_set_opt || true
# Reset `shopt -X`
eval "$_shell_shopt_opts" || true
# Reset traps
for _sig in {1..31}; do trap - $_sig; done
trap - ERR EXIT DEBUG
"""


class AutoNewlines:
    def __init__(self, file:File) -> AutoNewlines:
        self.file:File = file

    def write(self, data:str) -> None:
        self.file.write(data + "\n")

    def __enter__(self) -> AutoNewlines:
        self.file.__enter__()
        return self

    def __exit__(self, *args:tuple[object]) -> bool:
        return self.file.__exit__(*args)

    def __getattr__(self, attr:str) -> object:
        return getattr(self.file, attr)


class RunManager(BaseRunManager):
    __slots__ = ()

    COMPILE:list[str] = []
    RUN:list[str] = ["bash", "--rcfile", "{tmp}/bashrc", "-i"]

    def cd(self, *, print_str:str="") -> None:
        super().cd(os.path.dirname(self.text.filepath), print_str=print_str)

    def execute(self, args:Iterable[str]) -> None:
        tmp:str = self.tmp.name
        with open(self.text.filepath, "rb") as src:
            with open(tmp+"/program", "wb") as des:
                des.write(b"trap 'return 1' ERR\n")
                des.write(src.read())
        with AutoNewlines(open(f"{tmp}/bashrc", "w")) as file:
            file.write(PREAMBLE)
            for bashrc in DEFAULT_BASHRC:
                file.write(f"source {bashrc!r} || failed_bashrc {bashrc!r}")
            file.write(f"source {tmp+'/program'!r} || true")
            file.write(POSTAMBLE)
        super().execute(args)
