from __future__ import annotations
import tkinter as tk

from bettertk import BetterTk, SpriteCache
from .xrawidgets import SingletonMeta
from .baserule import Rule


class SettingsManager(Rule, metaclass=SingletonMeta):
    __slots__ = "text", "settings", "settings_open", "root"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = []

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> BarManager:
        super().__init__(plugin, text, ons=("<<Open-Settings>>",))
        self.settings:dict[str:dict] = dict()
        self.settings_open:bool = False
        self.text:tk.Text = text

    # Normal manager methods
    def attach(self) -> None:
        super().attach()
        self.text.add_setting = self.add_setting
        self.text.get_setting = self.get_setting

    def destroy(self) -> None:
        if self.settings_open:
            self.root.destroy()

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        if on == "<open-settings>":
            self.open_settings()
            return False
        raise RuntimeError(f"Unhandled {on!r} in {self.__class__.__name__}")

    # Add/Get setting value (used by other managers)
    def add_setting(self, name:str, *, type:str, default:object) -> None:
        if name not in self.settings:
            self.settings[name] = dict()
        self.settings[name]["type"] = type
        self.settings[name]["default"] = default

    def get_setting(self, name:str, /) -> object|None:
        setting:dict|None = self.settings.get(name, None)
        if setting is None: return None
        return setting.get("value", setting["default"])

    # Generate update event
    def _updated(self) -> None:
        self.text.event_generate("<<Settings-Changed>>")

    # Get/Set state
    def set_state(self, data:dict) -> None:
        if data is None: return None
        for name, value in data.items():
            if name in self.settings:
                self.settings[name]["value"] = value
        self._updated()

    def get_state(self) -> dict:
        output:dict[str:object] = dict()
        for name, setting in self.settings.items():
            if "value" in setting:
                output[name] = setting["value"]
        return output

    # Open settings UI
    def open_settings(self) -> None:
        if self.settings_open:
            self.root.deiconify()
            self.root.move_to_current_workspace()
            self.root.attributes("-topmost", True)
            self.root.attributes("-topmost", False)
            return None
        self.settings_open:bool = True
        self.root:BetterTk = BetterTk(self.text)
        self.root.protocol("WM_DELETE_WINDOW", self.root.withdraw)
        self.root.iconphoto(False, SpriteCache(size=128)["gear-grey"])
        self.root.resizable(False, False)
        self.root.title("Settings")
        self.root.grid_columnconfigure(2, weight=1)

        for idx, name in enumerate(sorted(self.settings.keys()), start=1):
            setting:dict = self.settings[name] | {"name":name, "idx":idx}
            self._add_setting(**setting, value_exists="value" in setting)

    def _add_setting(self, *, type:str, default:object, value:object=None,
                     value_exists:bool, name:str, idx:int) -> None:
        text:str = name.title()
        root:tk.Tk = self.root

        if type == "bool":
            def updated() -> None:
                nonlocal value
                value = not value
                self.settings[name]["value"] = value
                self._updated()
            label:tk.Label = tk.Label(root, text=text, bg="black", fg="white")
            label.grid(row=idx+1, column=1)
            check:tk.Checkbutton = tk.Checkbutton(root, bg="black", fg="white",
                                                  bd=0, highlightthickness=0,
                                                  activebackground="black",
                                                  activeforeground="white",
                                                  selectcolor="black",
                                                  command=updated)
            if value: check.select()
            check.grid(row=idx+1, column=2)

        else:
            raise NotImplementedError("Setting of {type=!r} not implemented " \
                                      "by SettingsManager")