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

    def __getattr__(self, key:str):
        if key == "settings":
            return super().__getattr__(key)
        value = self.settings[key]
        if isinstance(value, dict):
            return Settings(value)
        else:
            return value

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


if os.access(PATH, os.R_OK):
    with open(PATH, "r") as file:
        curr:Settings = Settings(json.loads(file.read()))
else:
    curr:Settings = Settings(json.loads(DEFAULTS))