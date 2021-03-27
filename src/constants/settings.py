#https://stackoverflow.com/questions/1405913/how-do-i-determine-if-my-python-shell-is-executing-in-32bit-or-64bit-mode-on-os
from functools import partial
from tkinter import ttk
import tkinter as tk
import threading
import platform
import struct
import copy
import sys
import ast
import os
import re

class PyObject: pass

#BLOCK_REGEX = "([^:\n]+):( *#[^\n]*){0,1}(\n[ \t]+[^\n]*)+"
#LINE_REGEX = "(.*?) *= *(.+)"
TUPLE_REGEX = "\((([\w. \"]+),* *)+\)"

LINE_REGEX = " *([^\n \(\)]+)\(([^\n\(\)]+)\) *= *([^\n]+)"
BLOCK_REGEX = "([^\n \(\)]+)\(block\):\n( +("+LINE_REGEX+"\n)+)"

NAMED_COLOURS = ("alice blue", "AliceBlue", "antique white", "AntiqueWhite",
                 "AntiqueWhite1", "AntiqueWhite2", "AntiqueWhite3",
                 "AntiqueWhite4", "agua", "aquamarine", "aquamarine1",
                 "aquamarine2", "aquamarine3", "aquamarine4", "azure","azure1",
                 "azure2", "azure3", "azure4", "beige", "bisque", "bisque1",
                 "bisque2", "bisque3", "bisque4", "black", "blanched almond",
                 "BlanchedAlmond", "blue", "blue violet", "blue1", "blue2",
                 "blue3", "blue4", "BlueViolet", "brown", "brown1", "brown2",
                 "brown3", "brown4", "burlywood", "burlywood1", "burlywood2",
                 "burlywood3", "burlywood4", "cadet blue", "CadetBlue",
                 "CadetBlue1", "CadetBlue2", "CadetBlue3", "CadetBlue4",
                 "chartreuse", "chartreuse1", "chartreuse2", "chartreuse3",
                 "chartreuse4", "chocolate", "chocolate1", "chocolate2",
                 "chocolate3", "chocolate4", "coral", "coral1", "coral2",
                 "coral3", "coral4", "cornflower blue", "CornflowerBlue",
                 "cornsilk", "cornsilk1", "cornsilk2", "cornsilk3",
                 "cornsilk4", "crymson", "cyan", "cyan1", "cyan2", "cyan3",
                 "cyan4", "dark blue", "dark cyan", "dark goldenrod",
                 "dark gray", "dark green", "dark grey", "dark khaki",
                 "dark magenta", "dark olive green", "dark orange",
                 "dark orchid", "dark red", "dark salmon", "dark sea green",
                 "dark slate blue", "dark slate gray", "dark slate grey",
                 "dark turquoise", "dark violet", "DarkBlue", "DarkCyan",
                 "DarkGoldenrod", "DarkGoldenrod1", "DarkGoldenrod2",
                 "DarkGoldenrod3", "DarkGoldenrod4", "DarkGray", "DarkGreen",
                 "DarkGrey", "DarkKhaki", "DarkMagenta", "DarkOliveGreen",
                 "DarkOliveGreen1", "DarkOliveGreen2", "DarkOliveGreen3",
                 "DarkOliveGreen4", "DarkOrange", "DarkOrange1", "DarkOrange2",
                 "DarkOrange3", "DarkOrange4", "DarkOrchid", "DarkOrchid1",
                 "DarkOrchid2", "DarkOrchid3", "DarkOrchid4", "DarkRed",
                 "DarkSalmon", "DarkSeaGreen", "DarkSeaGreen1", "DarkSeaGreen2",
                 "DarkSeaGreen3", "DarkSeaGreen4", "DarkSlateBlue",
                 "DarkSlateGray", "DarkSlateGray1", "DarkSlateGray2",
                 "DarkSlateGray3", "DarkSlateGray4", "DarkSlateGrey",
                 "DarkTurquoise", "DarkViolet", "deep pink", "deep sky blue",
                 "DeepPink", "DeepPink1", "DeepPink2", "DeepPink3", "DeepPink4",
                 "DeepSkyBlue", "DeepSkyBlue1", "DeepSkyBlue2", "DeepSkyBlue3",
                 "DeepSkyBlue4", "dim gray", "dim grey", "DimGray", "DimGrey",
                 "dodger blue", "DodgerBlue", "DodgerBlue1", "DodgerBlue2",
                 "DodgerBlue3", "DodgerBlue4", "firebrick", "firebrick1",
                 "firebrick2", "firebrick3", "firebrick4", "floral white",
                 "FloralWhite", "forest green", "ForestGreen", "fuchsia",
                 "gainsboro", "ghost white", "GhostWhite", "gold", "gold1",
                 "gold2", "gold3", "gold4", "goldenrod", "goldenrod1",
                 "goldenrod2", "goldenrod3", "goldenrod4", "gray", "green",
                 "green yellow", "green1", "green2", "green3", "green4",
                 "GreenYellow", "grey", "honeydew", "honeydew1", "honeydew2",
                 "honeydew3", "honeydew4", "hot pink", "HotPink", "HotPink1",
                 "HotPink2", "HotPink3", "HotPink4", "indian red", "IndianRed",
                 "IndianRed1", "IndianRed2", "IndianRed3", "IndianRed4",
                 "indigo", "ivory", "ivory1", "ivory2", "ivory3", "ivory4",
                 "khaki", "khaki1", "khaki2", "khaki3", "khaki4", "lavender",
                 "lavender blush", "LavenderBlush", "LavenderBlush1",
                 "LavenderBlush2", "LavenderBlush3", "LavenderBlush4",
                 "lawn green", "LawnGreen", "lemon chiffon", "LemonChiffon",
                 "LemonChiffon1", "LemonChiffon2", "LemonChiffon3",
                 "LemonChiffon4", "light blue", "light coral", "light cyan",
                 "light goldenrod", "light goldenrod yellow", "light gray",
                 "light green", "light grey", "light pink", "light salmon",
                 "light sea green", "light sky blue", "light slate blue",
                 "light slate gray", "light slate grey", "light steel blue",
                 "light yellow", "LightBlue", "LightBlue1", "LightBlue2",
                 "LightBlue3", "LightBlue4", "LightCoral", "LightCyan",
                 "LightCyan1", "LightCyan2", "LightCyan3", "LightCyan4",
                 "LightGoldenrod", "LightGoldenrod1", "LightGoldenrod2",
                 "LightGoldenrod3", "LightGoldenrod4", "LightGoldenrodYellow",
                 "LightGray", "LightGreen", "LightGrey", "LightPink",
                 "LightPink1", "LightPink2", "LightPink3", "LightPink4",
                 "LightSalmon", "LightSalmon1", "LightSalmon2", "LightSalmon3",
                 "LightSalmon4", "LightSeaGreen", "LightSkyBlue",
                 "LightSkyBlue1", "LightSkyBlue2", "LightSkyBlue3",
                 "LightSkyBlue4", "LightSlateBlue", "LightSlateGray",
                 "LightSlateGrey", "LightSteelBlue", "LightSteelBlue1",
                 "LightSteelBlue2", "LightSteelBlue3", "LightSteelBlue4",
                 "LightYellow", "LightYellow1", "LightYellow2", "LightYellow3",
                 "LightYellow4", "lime", "lime green", "LimeGreen", "linen",
                 "magenta", "magenta1", "magenta2", "magenta3", "magenta4",
                 "maroon", "maroon1", "maroon2", "maroon3", "maroon4",
                 "medium aquamarine", "medium blue", "medium orchid",
                 "medium purple", "medium sea green", "medium slate blue",
                 "medium spring green", "medium turquoise", "medium violet red",
                 "MediumAquamarine", "MediumBlue", "MediumOrchid",
                 "MediumOrchid1", "MediumOrchid2", "MediumOrchid3",
                 "MediumOrchid4", "MediumPurple", "MediumPurple1",
                 "MediumPurple2", "MediumPurple3", "MediumPurple4",
                 "MediumSeaGreen", "MediumSlateBlue", "MediumSpringGreen",
                 "MediumTurquoise", "MediumVioletRed", "midnight blue",
                 "MidnightBlue", "mint cream", "MintCream", "misty rose",
                 "MistyRose", "MistyRose1", "MistyRose2", "MistyRose3",
                 "MistyRose4", "moccasin", "navajo white", "NavajoWhite",
                 "NavajoWhite1", "NavajoWhite2", "NavajoWhite3", "NavajoWhite4",
                 "navy", "navy blue", "NavyBlue", "old lace", "OldLace",
                 "olive", "olive drab", "OliveDrab", "OliveDrab1",
                 "OliveDrab2", "OliveDrab3", "OliveDrab4", "orange",
                 "orange red", "orange1", "orange2", "orange3", "orange4",
                 "OrangeRed", "OrangeRed1", "OrangeRed2", "OrangeRed3",
                 "OrangeRed4", "orchid", "orchid1", "orchid2", "orchid3",
                 "orchid4", "pale goldenrod", "pale green", "pale turquoise",
                 "pale violet red", "PaleGoldenrod", "PaleGreen", "PaleGreen1",
                 "PaleGreen2", "PaleGreen3", "PaleGreen4", "PaleTurquoise",
                 "PaleTurquoise1", "PaleTurquoise2", "PaleTurquoise3",
                 "PaleTurquoise4", "PaleVioletRed", "PaleVioletRed1",
                 "PaleVioletRed2", "PaleVioletRed3", "PaleVioletRed4",
                 "papaya whip", "PapayaWhip", "peach puff", "PeachPuff",
                 "PeachPuff1", "PeachPuff2", "PeachPuff3", "PeachPuff4",
                 "peru", "pink", "pink1", "pink2", "pink3", "pink4", "plum",
                 "plum1", "plum2", "plum3", "plum4", "powder blue",
                 "PowderBlue", "purple", "purple1", "purple2", "purple3",
                 "purple4", "red", "red1", "red2", "red3", "red4",
                 "rosy brown", "RosyBrown", "RosyBrown1", "RosyBrown2",
                 "RosyBrown3", "RosyBrown4", "royal blue", "RoyalBlue",
                 "RoyalBlue1", "RoyalBlue2", "RoyalBlue3", "RoyalBlue4",
                 "saddle brown", "SaddleBrown", "salmon", "salmon1",
                 "salmon2", "salmon3", "salmon4", "sandy brown",
                 "SandyBrown", "sea green", "SeaGreen", "SeaGreen1",
                 "SeaGreen2", "SeaGreen3", "SeaGreen4", "seashell",
                 "seashell1", "seashell2", "seashell3", "seashell4",
                 "sienna", "sienna1", "sienna2", "sienna3", "sienna4", "silver",
                 "sky blue", "SkyBlue", "SkyBlue1", "SkyBlue2", "SkyBlue3",
                 "SkyBlue4", "slate blue", "slate gray", "slate grey",
                 "SlateBlue", "SlateBlue1", "SlateBlue2", "SlateBlue3",
                 "SlateBlue4", "SlateGray", "SlateGray1", "SlateGray2",
                 "SlateGray3", "SlateGray4", "SlateGrey", "snow", "snow1",
                 "snow2", "snow3", "snow4", "spring green", "SpringGreen",
                 "SpringGreen1", "SpringGreen2", "SpringGreen3", "SpringGreen4",
                 "steel blue", "SteelBlue", "SteelBlue1", "SteelBlue2",
                 "SteelBlue3", "SteelBlue4", "tan", "tan1", "tan2", "tan3",
                 "tan4", "teal", "thistle", "thistle1", "thistle2", "thistle3",
                 "thistle4", "tomato", "tomato1", "tomato2", "tomato3",
                 "tomato4", "turquoise", "turquoise1", "turquoise2",
                 "turquoise3", "turquoise4", "violet", "violet red",
                 "VioletRed", "VioletRed1", "VioletRed2", "VioletRed3",
                 "VioletRed4", "wheat", "wheat1", "wheat2", "wheat3", "wheat4",
                 "white", "white smoke", "WhiteSmoke", "yellow",
                 "yellow green", "yellow1", "yellow2", "yellow3", "yellow4",
                 "YellowGreen")
# Also "grey0", "grey1", "grey2", ..., "grey100"
NAMED_COLOURS += tuple("grey%i" % i for i in range(101))


SETTINGS_HEADER = """
# This is a file that contains all of the settings
# There 7 types allowed:
#
#      -------- ---------------------------- -----------------
#     | Type   | Example value 1            | Example value 2 |
#      -------- ---------------------------- -----------------
#     | bool   | True                       | False           |
#     | str    | Hello world                | this is a str   |
#     | colour | black                      | #00FF00         |
#     | int    | 1                          | 5               |
#     | None   | None                       | None            |
#     | float  | 1.02                       | 3.14159         |
#     | tuple  | ("values", 1, True, False) | [0.0, None]     |
#      -------- ---------------------------- -----------------
#
# Note: tuples must be in python's format of a tuple/list
# Note:
#
# The way that the settings are written:
# class_name(block):
#     setting_name(type) = setting_value
#     setting_name(type) = setting_value
#
"""
SETTINGS_HEADER = SETTINGS_HEADER.strip()+"\n\n\n"

DEFAULT_SETTINGS = """
editor(block):
    font(tuple) = ("DejaVu Sans Mono", 11)
    height(int) = 35
    width(int) = 80
    bg(colour) = black
    fg(colour) = white
    titlebar_colour(colour) = light grey
    notactivetitle_bg(colour) = grey20
    linenumbers_bg(colour) = black
    titlebar_size(int) = 0
    linenumbers_width(int) = 35
    time_highlight_brackets_ms(int) = 1500

terminal(block):
    font(tuple) = ("DejaVu Sans Mono", 11)
    height(int) = 20
    width(int) = 80
    bg(colour) = black
    fg(colour) = white
    titlebar_colour(colour) = light grey
    notactivetitle_bg(colour) = grey20
    titlebar_size(int) = 1
    wait_next_loop_ms(int) = 30
    wait_stdin_read_ms(int) = 100
    kill_proc(str) = taskkill /f /pid {pid} /t

compiler(block):
    win_path_executable(str) = {path}\..\compiled\ccarotmodule.exe
    win_compile(str) = g++ -O3 -w "{_in}" -o "{out}"
    win_run_command(str) = "{file}"
"""

DEFAULT_SETTINGS = SETTINGS_HEADER+DEFAULT_SETTINGS.strip()+"\n"


class Setting:
    def __init__(self, type, value):
        self.update(type, value)

    def get(self):
        return self.value

    def __repr__(self):
        return f"Setting(type={self.type}, value={repr(self.value)})"

    def __str__(self):
        return "<Setting object at %s>" % (hex(id(self))[2:])

    def update(self, type, value):
        self.type = type
        self.value = value


class Settings:
    def __init__(self, file="settings.ini"):
        self.settings = {}
        if file is not None:
            self.update_from_file(file)

    def items(self):
        return self.settings.items()

    def __repr__(self):
        output = "Settings("
        temp = ["%s=%s"%(str(key), str(value)) for key, value in
                                                         self.settings.items()]
        output += ", ".join(temp)
        return output + ")"

    def __str__(self):
        return "<Settings object at %s>" % hex(id(self)).upper()

    def __getitem__(self, key: str):
        return self.settings[key]

    def __setitem__(self, key: str, value: PyObject):
        self.settings[key] = value

    def __getattr__(self, key: str):
        try:
            settings = self.__dict__["settings"]
            if key in settings:
                return settings[key]
        except:
            return self.__dict__[key]

    def __setattr__(self, key: str, value: PyObject):
        try:
            settings = self.__dict__["settings"]
            if key in settings:
                self.__dict__["settings"][key] = value
        except:
            self.__dict__[key] = value

    def update_from_file(self, filename: str):
        try:
            with open(filename, "r") as file:
                self.update_from_string(file.read())
        except:
            sys.stderr.write("Couldn't find the settings file so using"+\
                             "the default settings.\n")
            self.update(parse(DEFAULT_SETTINGS))

    def update_from_string(self, text: str):
        # Make sure we have all of the settings:
        #self.update(parse(DEFAULT_SETTINGS))
        self.update(parse(text))

    def update(self, settings: dict):
        for key, value in settings.items():
            if key in self.settings:
                self.__dict__[key].update(value)
                continue
            if isinstance(value, dict):
                new_value = Settings(None)
                new_value.update(value)
            else:
                new_value = Setting(*value)
            self.settings.update({key: new_value})

    def save_to_str(self, spaces=0):
        text = ""
        for key, value in self.settings.items():
            if isinstance(value, Settings):
                text += "%s(block):\n"%key
                text += value.save_to_str(spaces+4)
                text += "\n"
            else:
                type, value = value.type, value.value
                if isinstance(value, tuple):
                    value = str(value).replace("'", "\"")
                text += " "*spaces + f"{key}({str(type)}) = {value}\n"
        return text

    def save(self, filename="settings.ini"):
        with open(filename, "w") as file:
            data = self.save_to_str()
            data = SETTINGS_HEADER + data.rstrip("\n")
            file.write(data + "\n")

    def reset(self, file="settings.ini"):
        self.update(parse(DEFAULT_SETTINGS))
        self.save(file)


def parse(text: str) -> dict:
    """
    Finds all blocks and sends all of them to `parse_block`. All individual
    settings are also returned as part of the output dictionary.
    It returns this:
        {
         "block_name1": {<block parsed by `parse_block`>},
         "block_name2": {<block parsed by `parse_block`>},
         ###<setting parsed by `parse_block` (same as `parse_line`)>,
        }
    """
    #text = remove_comments(text)
    output = {}
    result = re.findall(BLOCK_REGEX, text)
    for block_name, block, *_ in result:
        output.update({block_name: parse_block(block)})
    return output

#def remove_comments(text):
#    lines_to_remove = []
#    for line in text.split("\n"):
#        if line.lstrip(" ").startswith("#"):
#            lines_to_remove.append(line)
#    for line in lines_to_remove:
#        idx_start = text.index(line)
#        idx_end = idx_start + len(line) + 1 # +1 for the "\n" at the end
#        text = text[:idx_start]+text[idx_end:]
#    return text.strip()

def parse_block(block: str) -> dict:
    output = {}
    result = re.findall(LINE_REGEX, block)
    for setting_name, type, setting_value in result:
        value = (type, parse_value(setting_value, type))
        output.update({setting_name: value})
    return output

def parse_value(value: str, type: str) -> PyObject:
    if type == "int":
        return to_int(value)
    if type == "float":
        return to_float(value)
    if type == "str":
        # DO NOT tread as safe input
        return value
    if type == "bool":
        return to_bool(value)
    if type == "None":
        return None
    if (type == "colour") or (type == "color"):
        return to_colour(value)
    if type == "tuple":
        return to_tuple(value)
    raise ValueError(f"Unknow type {type} for setting value {value}.")

def to_colour(value: str) -> str:
    if (value.lower() == "default") or (value == ""):
        return "#f0f0ed"
    if value in NAMED_COLOURS:
        return value
    if value[0] == "#":
        if len(value) == 7:
            try:
                int(value[1:], 16)
                return value
            except ValueError:
                pass
    raise ValueError(f"\"{value}\" can't be interpreted as a colour")

def to_tuple(value: str) -> tuple:
    if len(value) != 0:
        is_tuple = (value[0] == "(") and (value[-1] == ")")
        is_list = (value[0] == "[") and (value[-1] == "]")
        if is_tuple or is_list:
            try:
                return parse_tuple(value[1:-1])
            except SyntaxError:
                pass
    raise ValueError(f"\"{value}\" can't be interpreted as a tuple")

def parse_tuple(value: str) -> tuple:
    """
    value is in the form: "element1, element2, element3"
    """
    return tuple(ast.literal_eval("[%s]" % value))

def to_bool(value: str) -> bool:
    value = value.lower()
    if value not in ("true", "false"):
        raise ValueError(f"Setting \"({value})\" can't be"+\
                         "interpreted as a bool")
    return value == "true"

def to_int(value: str) -> int:
    try:
        value = int(value)
    except ValueError:
        raise ValueError(f"\"{value}\" can't be interpreted as an int")
    return value

def to_float(value: str) -> float:
    try:
        value = float(value)
    except ValueError:
        raise ValueError(f"\"{value}\" can't be interpreted as an int")
    return value


settings = Settings()


def get_os_bits() -> int:
    return 8 * struct.calcsize("P")

def get_os_extension() -> int:
    os = platform.system()
    if os.lower() == "windows":
        return ".exe"
    elif os.lower() == "linux":
        return ""
    else:
        raise OSError("Can't recognise the OS type.")


class ChangeSettings:
    def __init__(self, master):
        """
        Creates a window that allowes the user to change the
        settings.

        It also setts:
            notebook.blocks    empty list
        """
        self.root = tk.Toplevel(master)
        self.root.resizable(False, False)
        self.root.title("Settings changer")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=2, column=1, columnspan=2)
        self.notebook.blocks = []
        self.all_settings = Settings()
        self.add_entries(self.notebook, self.all_settings)
        self.button_save = tk.Button(self.root, text="Save",
                                     bg="light grey", fg="black",
                                     command=self.done)
        self.button_reset = tk.Button(self.root, text="Reset Settings",
                                      bg="light grey", fg="black",
                                      command=self.reset_settings)
        self.button_save.grid(row=1, column=1, sticky="news")
        self.button_reset.grid(row=1, column=2, sticky="news")

    def reset_settings(self):
        """
        Resets all of the settings to their default values.
        """
        self.all_settings.reset()
        self.close()

    def add_block(self, notebook, name, settings):
        """
        Adds a block of settings (as a tab) to the notebook
        by iterating over all settings and adding them 1 by 1.

        It also setts:
            frame.settings    empty list
        """
        row = 1
        frame = tk.Frame(notebook)
        frame.settings = []
        self.notebook.blocks.append(frame)
        frame.name = name
        notebook.add(frame, text=name)
        label1 = tk.Label(frame, text="Setting name")
        label2 = tk.Label(frame, text="Type")
        label3 = tk.Label(frame, text="Entry")
        separator = ttk.Separator(frame, orient="horizontal")

        label1.grid(row=row, column=1, sticky="nws")
        label2.grid(row=row, column=2, sticky="nws")
        label3.grid(row=row, column=3, sticky="news")
        separator.grid(row=row+1, column=0, columnspan=5, sticky="ew")

        row += 2
        for key, value in settings.items():
            self.add_entry(frame, key, value, row)
            row += 1

    def add_entry(self, frame, key, value, row):
        """
        Displays and entry on the screen.
        It is in the format:
            Name of setting     Date type     tkinter Entry for input
        """
        dtype = value.type
        name_label = tk.Label(frame, text=key)
        dtype_label = tk.Label(frame, text=dtype)
        name_label.grid(row=row, column=1, sticky="nws")
        dtype_label.grid(row=row, column=2, sticky="nws")
        if dtype == "bool":
            button = tk.Button(frame, text=str(value.value))
            button.grid(row=row, column=3, sticky="news")
            command = partial(self.toggle_button, button)
            button.config(command=command)
            getter = partial(button.cget, "text")
            wronger = partial(button.config, bg="red")
            righter = partial(button.config, bg="white")
        else:
            entry = tk.Entry(frame, width=40)
            entry.grid(row=row, column=3, sticky="news")
            entry.insert(0, str(value.value).replace("'", "\""))
            getter = partial(entry.get)
            wronger = partial(entry.config, bg="red")
            righter = partial(entry.config, bg="white")
        frame.settings.append((value, getter, (wronger, righter)))

    def toggle_button(self, button):
        text = button.cget("text")
        button.config(text=str(text == "False"))

    def add_entries(self, notebook, settings):
        """
        Displays the all of the settings given on the tkinter window
        """
        for key, value in settings.items():
            self.add_block(notebook, key, value)

    def done(self):
        """
        Checks if all of the data types are correct and saves them
        It also closes the window and displays a message saying:
            "Restart the program for the changes to take effect."
        """
        if self.set() != "break":
            self.all_settings.save()
            self.close()

    def close(self, coords=None):
        """
        Closes the window and and displays a message that reads:
            "Restart the program for the changes to take effect."
        """
        self.root.destroy()
        info("Restart the program for the changes to take effect.")

    def set(self) -> str:
        """
        Iterates over all of the user input and updates the settings
        that it receives.
        """
        for block_frame in self.notebook.blocks:
            block_name = block_frame.name
            for setting, getter, (wronger, righter) in block_frame.settings:
                data = getter()
                if self.check_match_type(data, setting.type):
                    righter()
                    setting.value = data
                else:
                    wronger()
                    return "break"

    def check_match_type(self, data, dtype):
        """
        Checks if the data type of the variable is correct.
        It uses the settings module and the global functions
        there
        """
        try:
            parse_value(str(data), str(dtype))
        except ValueError as error:
            print(error)
            return False
        return True


def _info(text: str) -> None:
    root = tk.Tk()
    root.resizable(False, False)
    root.title("Info")
    label = tk.Label(root, text=text)
    button = tk.Button(root, text="Ok", command=root.destroy)
    button.bind("<Return>", lambda e:root.destroy())
    button.focus()
    label.grid(row=1, column=1, sticky="news")
    button.grid(row=2, column=1, sticky="news")
    root.mainloop()

def info(text: str) -> None:
    """
    Displays a message on the screen with 1 button ("Ok")
    It takes in the message (as a string).
    To make sure that it doesn't effect the main thread
    all of it is handled in a separe thread.
    """
    # The x and the y coordinates that new new window will take
    thread = threading.Thread(target=_info, args=(text, ))
    thread.deamon = True
    thread.start()
