from __future__ import annotations
from os.path import dirname, join
from getpass import getuser
import string
import json
import os

ALLOWED_CHARS:str = string.ascii_letters + string.digits + "_-"
USERNAME:str = "".join(char for char in getuser() if char in ALLOWED_CHARS)
OS_NAME:str = "".join(char for char in os.name if char in ALLOWED_CHARS)
PATH:str = join(dirname(__file__), f"state.{OS_NAME}.{USERNAME}.json")


class Settings:
    __slots__ = "_settings"

    def __init__(self, settings:dict[str,object]) -> Settings:
        self._settings:dict[str,object] = settings

    def __contains__(self, key:str) -> bool:
        return key in self._settings

    def __getattr__(self, key:str) -> object:
        return self._getattr(key)

    def _getattr(self, key:str) -> object:
        if key == "_settings":
            return super().__getattr__(key)
        value = self._settings[key]
        if isinstance(value, dict):
            return Settings(value)
        else:
            return value

    def __setattr__(self, key:str, value:object) -> None:
        if key == "_settings":
            super().__setattr__(key, value)
            return None
        if isinstance(self._settings.get(key, None), dict):
            raise ValueError("Can't replace a settings tree")
        self._settings[key] = value

    def __repr__(self) -> str:
        return "Settings(" + ", ".join(map(str, self._settings)) + ")"

    def save(self) -> Error:
        try:
            with open(PATH, "w") as file:
                file.write(json.dumps(self._settings, indent=4))
            return False
        except (OSError, IOError):
            return True

    def update(self, **kwargs) -> None:
        self._settings.update(kwargs)

    def get(self, key:str, *default:tuple[object]) -> object:
        assert len(default) < 2, "Too many arguments"
        if key in self._settings:
            return self._getattr(key)
        if len(default) == 1:
            return default[0]
        raise KeyError(f"Unknown {key=!r}")

    def set_default(self, setting:str, value:object) -> None:
        if setting == "_settings":
            raise ValueError('"_settings" setting is reserved.')
        if setting not in self:
            setattr(self, setting, value)


try:
    with open(PATH, "r") as file:
        curr:Settings = Settings(json.loads(file.read()))
except (PermissionError,FileNotFoundError,json.decoder.JSONDecodeError):
    curr:Settings = Settings({})


# Set-up fonts:
def get_actual_font_name(fontname:str) -> str:
    from tkinter import font
    import tkinter as tk
    root:tk.Tk = tk.Tk()
    real_fontname:str = font.nametofont(fontname).actual()["family"]
    root.destroy()
    return real_fontname

def font_exists(fontname:str) -> bool:
    raise NotImplementedError("This doesn't work for some reason")
    try:
        font.nametofont(fontname)
        return True
    except tk.TclError:
        return False


DEFAULT_FONT:str = "TkDefaultFont"
DEFAULT_FONT_MONO:str = "TkFixedFont"
_default_font:str = get_actual_font_name(DEFAULT_FONT)
_default_font_mono:str = get_actual_font_name(DEFAULT_FONT_MONO)


curr.set_default("window", {})
curr.window.set_default("height", 815)
curr.window.set_default("x", 998)
curr.window.set_default("y", 228)
curr.window.set_default("focused_text", None)
curr.window.set_default("font", (_default_font,10,"normal","roman"))

curr.set_default("explorer", {})
curr.explorer.set_default("width", 222)
curr.explorer.set_default("hide_h_scroll", True)
curr.explorer.set_default("hide_v_scroll", True)
curr.explorer.set_default("expanded", [])
curr.explorer.set_default("added", [])
curr.explorer.set_default("font", (_default_font,10,"normal","roman"))
curr.explorer.set_default("monofont", (_default_font_mono,9,"normal","roman"))

curr.set_default("notebook", {})
curr.notebook.set_default("width", 690)
curr.notebook.set_default("open", [])

curr.set_default("editor", {})
curr.editor.set_default("selectmanager", {})
curr.editor.selectmanager.set_default("bg", "#ff4500")
curr.editor.set_default("font", (_default_font_mono,10,"normal","roman"))
