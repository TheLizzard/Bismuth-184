from __future__ import annotations
from os.path import dirname, join
import string
import json
import os

ALLOWED_CHARS:str = string.ascii_letters + string.digits + "_-"
OS_NAME:str = "".join(char for char in os.name if char in ALLOWED_CHARS)
PATH:str = join(dirname(dirname(__file__)), f"state.{OS_NAME}.json")

DEFAULTS:str = """
{
    "window":   {
                  "height":850,
                  "x":760,
                  "y":196
                },
    "explorer": {
                  "width": 250,
                  "hide_h_scroll": true,
                  "hide_v_scroll": true,
                  "expanded": [],
                  "added": []
                },
    "notebook": {
                  "width": 900,
                  "open": []
                },
    "editor":   {
                  "selectmanager": {
                                     "bg": "#ff4500"
                                   }
                }
}
"""

class Settings:
    __slots__ = "settings"

    def __init__(self, settings:dict) -> Settings:
        self.settings:dict = settings

    def __contains__(self, key:str) -> bool:
        return key in self.settings

    def __getattr__(self, key:str) -> object:
        return self._getattr(key)

    def _getattr(self, key:str) -> object:
        if key == "settings":
            return super().__getattr__(key)
        value = self.settings[key]
        if isinstance(value, dict):
            return Settings(value)
        else:
            return value

    def __setattr__(self, key:str, value:object) -> None:
        if key == "settings":
            super().__setattr__(key, value)
            return None
        if isinstance(self.settings.get(key, None), dict):
            raise ValueError("Can't replace a settings tree")
        self.settings[key] = value

    def __repr__(self) -> str:
        return "Settings(" + ", ".join(map(str, self.settings)) + ")"

    def save(self) -> Error:
        if os.path.exists(PATH):
            permissions:bool = os.access(PATH, os.W_OK)
        else:
            permissions:bool = os.access(dirname(PATH), os.W_OK)
        if not permissions:
            return True
        with open(PATH, "w") as file:
            file.write(json.dumps(self.settings, indent=4))
        return False

    def update(self, **kwargs) -> None:
        self.settings.update(kwargs)

    def get(self, key:str, *default:tuple[object]) -> object:
        assert len(default) < 2, "Too many arguments"
        if key in self.settings:
            return self._getattr(key)
        if len(default) == 1:
            return default[0]
        raise KeyError(f"Unknown {key=!r}")


if os.access(PATH, os.R_OK):
    with open(PATH, "r") as file:
        curr:Settings = Settings(json.loads(file.read()))
else:
    curr:Settings = Settings(json.loads(DEFAULTS))


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


if "font" not in curr.window:
    _default_font:str = get_actual_font_name(DEFAULT_FONT)
    curr.window.font = (_default_font, 10, "normal", "roman")
if "font" not in curr.explorer:
    _default_font:str = get_actual_font_name(DEFAULT_FONT)
    curr.explorer.font = (_default_font, 10, "normal", "roman")
if "monofont" not in curr.explorer:
    # Only for the + or - for expanding/collapsing folders
    # Why the hell did I choose size=9 when first making the explorer widget?
    _default_font:str = get_actual_font_name(DEFAULT_FONT_MONO)
    curr.explorer.monofont = (_default_font, 9, "normal", "roman")
if "font" not in curr.editor:
    _fixed_font:str = get_actual_font_name(DEFAULT_FONT_MONO)
    curr.editor.font = (_fixed_font, 10, "normal", "roman")