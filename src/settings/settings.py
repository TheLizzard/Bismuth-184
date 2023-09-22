from __future__ import annotations
import json
import os

PATH:str = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "state.json")

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
                  "open": []
                },
    "notebook": {
                  "width": 900,
                  "open": []
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

    def save(self) -> None:
        with open(PATH, "w") as file:
            file.write(json.dumps(self.settings))

    def update(self, **kwargs) -> None:
        self.settings.update(kwargs)


if os.path.exists(PATH):
    with open(PATH, "r") as file:
        curr:Settings = Settings(json.loads(file.read()))
else:
    curr:Settings = Settings(json.loads(DEFAULTS))
