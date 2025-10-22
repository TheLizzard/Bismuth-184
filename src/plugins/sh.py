from __future__ import annotations
import tkinter as tk
import stat
import os

from .baseplugin import BasePlugin
from .common_rules import COMMON_RULES
from .rules.sh.runmanager import RunManager
from .rules.sh.colourmanager import ColourManager
from .rules.sh.commentmanager import CommentManager
from .rules.sh.saveloadmanager import SaveLoadManager
from .rules.sh.whitespacemanager import WhiteSpaceManager


# Used to check if the file is executable by (owner, group, or other)
EXECUTABLE:int = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


class ShPlugin(BasePlugin):
    __slots__ = ()
    DEFAULT_CODE:str = '#!/bin/bash\nset -e\n\necho "Hello world"'

    def __init__(self, *args:tuple) -> PythonPlugin:
        rules:list[Rule] = [
                             RunManager,
                             ColourManager,
                             CommentManager,
                             SaveLoadManager,
                             WhiteSpaceManager,
                           ]
        super().__init__(*args, rules+COMMON_RULES)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        if filepath is None:
            return False
        # Check file extension
        if filepath.endswith(".sh") or filepath.endswith(".run"):
            return True
        # Check shebang/mode line
        try:
            with open(filepath, "r") as file:
                line:str = file.readline().removesuffix("\n")
                if line[:2] == "#!": # Shebang
                    return "sh" in line
                elif "-*- shell-script -*-" in line: # Mode line
                    return True
        except (OSError, UnicodeDecodeError):
            pass
        # BUG: All text files on NTFS/FAT/FAT32 partitions will be assumed
        #        to be executable since they don't support linux-like
        #        permissions. I tried using `fstatfs(···).f_fsid` but the
        #        documentation says that "nobody knows what `f_fsid` is
        #        supposed to contain"
        """
        # If no shebang and executable, assume shell script
        try:
            if os.stat(filepath).st_mode & EXECUTABLE:
                return True
        except OSError:
            pass
        """
        return False
