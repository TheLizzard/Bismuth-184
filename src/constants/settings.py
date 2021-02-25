#https://stackoverflow.com/questions/1405913/how-do-i-determine-if-my-python-shell-is-executing-in-32bit-or-64bit-mode-on-os
from tkinter import ttk
import tkinter as tk
import threading
import platform
import struct
import copy
import os
import re

BLOCK_REGEX = "([^:\n]+):( *#[^\n]*){0,1}(\n[ \t]+[^\n]*)+"
LINE_REGEX = "(.*?) *= *(.+)"
TUPLE_REGEX = "\((([\w. \"]+),* *)+\)"


SETTINGS_HEADER = """
# This is a file that contains all of the settings
# There 6 types allowed:
#
#      --------- ---------------------------- -----------------
#     | Type    | Example value 1            | Example value 2 |
#      --------- ---------------------------- -----------------
#     | boolean | True                       | False           |
#     | string  | "Hello world"              | "this is a str" |
#     | integer | 1                          | 5               |
#     | None    | None                       | None            |
#     | float   | 1.02                       | 3.14159         |
#     | tuple   | ("values", 1, True, False) | (0.0, None)     |
#      --------- ---------------------------- -----------------
#
"""
SETTINGS_HEADER = SETTINGS_HEADER.strip()+"\n\n\n"

DEFAULT_SETTINGS = """
editor:
    font = ("DejaVu Sans Mono", 11)
    height = 35
    width = 80
    bg = "black"
    fg = "white"
    titlebar_colour = "light grey"
    titlebar_size = 0

terminal:
    font = ("DejaVu Sans Mono", 11)
    height = 20
    width = 80
    bg = "black"
    fg = "white"
    titlebar_colour = "light grey"
    titlebar_size = 1

compiler:
    win_path_executable = "{path}\..\compiled\ccarotmodule.exe"
    win_compile = "g++ -O3 -w "{_in}" -o "{out}""
    win_run_command = ""{file}""
"""

DEFAULT_SETTINGS = SETTINGS_HEADER+DEFAULT_SETTINGS.strip()+"\n"


class Setting: pass
class Settings: pass


class Setting:
    def __init__(self, *args, **kwargs):
        if (args == [None]) and (len(kwargs.keys()) == 0):
            pass
        else:
            for key, value in kwargs.items():
                if isinstance(value, dict):
                    value = Setting(**value)
                self.__dict__.update({key: value})

    def __str__(self) -> str:
        return str(self.__dict__)

    def __getitem__(self, key: str):
        return self.__dict__[key]

    def __setitem__(self, key: str, value) -> None:
        self.__dict__.update({key: value})

    def items(self):
        return self.__dict__.items()

    def pop(self, idx=None):
        return self.__dict__.pop(idx)

    def items(self):
        return self.__dict__.items()

    def set(self, key, value):
        self[key] = value

    def update(self, dictionary: dict) -> None:
        self.__dict__.update(dictionary)

    def deepcopy(self):
        return copy.deepcopy(self)

    def dict(self) -> dict:
        return self.__dict__


class Settings:
    def __init__(self, file="settings.ini"):
        if file is not None:
            self.update(file)

    def pop(self, *args):
        return self.__dict__.pop(*args)

    def __getitem__(self, key: str):
        return self.__dict__[key]

    def __setitem__(self, key: str, value) -> None:
        self.__dict__.update({key: value})

    def items(self):
        return self.__dict__.items()

    def parse(self, data: str) -> dict:
        return parse(data)

    def set_settings(self, settings: dict) -> None:
        settings = self.lower_case_key(settings)
        for key, value in settings.items():
            if isinstance(value, dict):
                value = Setting(**value)
            self.__dict__.update({key: value})

    def lower_case_key(self, setting: dict) -> dict:
        if isinstance(setting, dict):
            output = {}
            for key, value in setting.items():
                output.update({key.lower(): self.lower_case_key(value)})
            return output
        else:
            return setting

    def reset(self, file="settings.ini") -> None:
        """
        Resets to the default settings.
        """
        with open(file, "w") as file:
            file.write(DEFAULT_SETTINGS)

    def update(self, file="settings.ini") -> None:
        """
        Reads the settings from the file if it exists.
        """
        if os.path.exists(file):
            with open(file, "r") as file:
                # Adding default settings just for backup.
                data = DEFAULT_SETTINGS+"\n"+file.read()
            settings = self.parse(data)
        else:
            print("Couldn't read the settings file so using the default ones.")
            settings = self.parse(DEFAULT_SETTINGS)
        self.set_settings(settings)

    def save(self):
        contents = self.get_all("", self)
        contents = SETTINGS_HEADER+contents.strip()
        with open("settings.ini", "w") as file:
            file.write(contents)

    def get_all(self, contents, settings_subtree, indent=0):
        for key, value in settings_subtree.items():
            if type(value) == Setting:
                contents += key.lower()+":\n"
                contents = self.get_all(contents, value, indent+1)
                contents += "\n"
            else:
                if not isinstance(value, str):
                    value = str(value)
                contents += " "*4*indent + key + " = "
                contents += value.replace("'", "\"") + "\n"
        return contents


def parse(data: str) -> dict:
    output = {}
    result = re.finditer(BLOCK_REGEX, data)

    if result is not None:
        for block in result:
            block = block.group()
            for key, value in parse_block(block).items():
                if key in output.keys():
                    output[key].update(value)
                    value = output[key]
                output.update({key: value})
            data = data.replace(block, "", 1)

    for line in data.split("\n"):
        output.update(parse_line(line))

    return output

def parse_line(line: str) -> dict:
    """Returns a dict of the parsed line or None"""

    line = line.lstrip()
    # check if the line is empty or a comment
    if (line == "") or (line[0] == "#"):
        return {}

    result = re.search(LINE_REGEX, line)
    if result is not None:
        result = result.groups()
        if len(result) == 2:
            key, value = result
            return {key: parse_value(value)}
    raise ValueError("Can't parse this line: "+line)

def parse_value(value: str):
    if value == "None": # check if the value is None
        return None

    if value.isdigit():  #check if the value is int
        return int(value)

    if check_if_float(value):  #check if the value is float
        return float(value)

    if string_to_bool(value) is not None:  #check if the value is bool
        return string_to_bool(value)

    if check_if_tuple(value) is not None:  #check if the value is tuple
        return check_if_tuple(value)

    if value[0] == value[-1] == "\"":  #check if the value is str
        return value[1:][:-1]

    if value[0] == "(":
        raise ValueError("Open braket without a closing one.")
    return "\""+value+"\""

    raise ValueError("The value is not a valid type: "+value)


def check_if_float(string: str) -> bool:
    has_max_one_dot = string.replace(".", "", 1).isdigit()
    dot_not_at_end = string[-1] != "."
    return has_max_one_dot and dot_not_at_end

def check_if_tuple(string: str):
    if (string[0] == "(") and (string[-1] == ")"):
        result = string[1:][:-1].split(", ")
        output = []
        for substring in result:
            output.extend(substring.split(","))
        output = tuple(map(parse_value, output))
        return output
    return None

def string_to_bool(string: str) -> bool:
    if string.lower() in ("y", "yes", "t", "true", "on"):
        return True
    if string.lower() in ("n", "no", "f", "false", "off"):
        return False
    return None

def parse_block(block: str) -> dict:
    result = re.search(BLOCK_REGEX, block)
    if result is not None:
        name = result.group(1)
        block = block.split("\n", 1)[1]
        result = {}
        for line in block.split("\n"):
            parsed_line = parse_line(line)
            result.update(parsed_line)
        return {name.replace(" ", ""): result}
    raise ValueError("Can't parse this block: "+block)

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
        """
        self.root = tk.Toplevel(master)
        self.root.resizable(False, False)
        self.root.title("Settings changer")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=2, column=1, columnspan=2)
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
        """
        row = 1
        frame = tk.Frame(notebook)
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
        dtype_name = self.stringify(type(value).__name__)
        label = tk.Label(frame, text=key)
        dtype = tk.Label(frame, text=dtype_name)
        entry = tk.Entry(frame, width=40)
        entry.insert(0, str(value).replace("'", "\""))
        label.grid(row=row, column=1, sticky="nws")
        dtype.grid(row=row, column=2, sticky="nws")
        entry.grid(row=row, column=3, sticky="news")

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
        new_settings = Settings(None)
        if self.set(new_settings) != "error":
            new_settings.save()
            self.close()

    def close(self, coords=None):
        """
        Closes the window and and displays a message that reads:
            "Restart the program for the changes to take effect."
        """
        self.root.destroy()
        info("Restart the program for the changes to take effect.")

    def set(self, settings: Settings) -> str:
        """
        Iterates over all of the user input and updates the settings
        that it receives.
        """
        for block_frame in self.notebook.winfo_children():
            block_name = block_frame.name
            children = block_frame.winfo_children()[4:]
            settings_block = Setting(None)

            i = 0
            while i+3 <= len(children):
                name_label, dtype_label, entry = children[i:i+3]
                i += 3
                setting_name = name_label["text"]
                dtype = dtype_label["text"]
                data = entry.get()
                if self.check_match_type(data, dtype):
                    entry["bg"] = "white"
                else:
                    entry["bg"] = "red"
                    return "error"
                settings_block[setting_name] = parse_value(data)

            settings[block_name] = settings_block
        return "success"

    def stringify(self, name: str):
        """
        Converts the type names into a more user fiendly format like:
            str => string
            int => whole number
            bool => boolean
            ...
        """
        if name == "bool":
            return "boolean"
        if name == "str":
            return "string"
        if name == "tuple":
            return "list" # Most users wouldn't know what a tuple is
        if name == "int":
            return "whole number"
        if name == "float":
            return "decimal"
        else:
            return name

    def unstringify(self, name: str):
        """
        The reverse of self.stringify(name)
        """
        if name == "boolean":
            return "bool"
        if name == "string":
            return "str"
        if name == "list":
            return "tuple"
        if name == "whole number":
            return "int"
        if name == "decimal":
            return "float"
        else:
            return name

    def check_match_type(self, data, dtype_stringified):
        """
        Checks if the data type of the variable is correct.
        It uses the settings module and the global functions
        there
        """
        dtype = self.unstringify(dtype_stringified)
        try:
            data = parse_value(data)
        except:
            return False
        return type(data).__name__ == dtype


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


settings = Settings()
