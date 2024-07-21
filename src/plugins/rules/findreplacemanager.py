from __future__ import annotations
import tkinter as tk
import re

from bettertk.messagebox import tell as telluser
from bettertk import BetterTk
from .baserule import Rule

from ..baseplugin import AllPlugin
from .undomanager import UndoManager
from .wrapmanager import WrapManager
from .colourmanager import ColourManager
from .selectmanager import SelectManager
from .shortcutmanager import RemoveShortcuts
from .clipboardmanager import ClipboardManager
from .whitespacemanager import WhiteSpaceManager

# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4

ESCAPED:dict[str,str] = {
                          "a": "\a",
                          "b": "\b",
                          "f": "\f",
                          "n": "\n",
                          "r": "\r",
                          "t": "\t",
                          "v": "\v",
                        }


class MiniPlugin(AllPlugin):
    __slots__ = ()

    def __init__(self, text:tk.Text) -> PythonPlugin:
        rules:list[Rule] = [
                             WrapManager,
                             UndoManager,
                             ColourManager,
                             SelectManager,
                             ClipboardManager,
                             RemoveShortcuts,
                           ]
        super().__init__(text, rules)


class Checkbox(tk.Frame):
    __slots__ = "ticked", "box"

    def __init__(self, master:tk.Misc, text:str) -> Checkbox:
        super().__init__(master, bd=0, highlightthickness=0, bg="black")
        label = tk.Label(self, text="#", bg="black", fg="white")
        label.pack(side="right")
        width:int = int(label.winfo_reqwidth()*2/3)
        self.box = tk.Canvas(self, bd=0, highlightthickness=1, width=width,
                             height=width)
        self.box.pack(side="right")
        self.ticked:bool = False
        self.box.bind("<Button-1>", self.toggle)
        label.bind("<Button-1>", self.toggle)
        label.config(text=text)

    def toggle(self, event:tk.Event=None) -> None:
        self.ticked:bool = not self.ticked
        self.box.config(bg="grey" if self.ticked else "white")


class FindReplaceManager(Rule):
    __slots__ = "text", "window", "find", "replace", "regex", "matchcase", \
                "wholeword", "button", "shown", "geom", "replace_label", \
                "replace_str", "find_cache", "swap"
    MAX_FINDS:int = 100
    HIT_TAG:str = "hit"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> None:
        self.swap:bool = False
        evs:tuple[str] = (
                           # Find
                           "<Control-F>", "<Control-f>",
                           # Replace
                           "<Control-R>", "<Control-r>",
                           "<Control-H>", "<Control-h>",
                           # Hit invalidation (something else is doing this?)
                           # "<<Before-Insert>>", "<<Before-Delete>>",
                         )
        super().__init__(plugin, text, evs)
        self.find_cache:tuple[str,int] = None
        self.text:tk.Text = self.widget
        self.window:BetterTk = None
        self.replace_str:str = ""
        self.shown:bool = False
        self.geom:str = None

    def attach(self) -> None:
        super().attach()
        self.text.tag_config(self.HIT_TAG, background="blue", foreground="white")
        self.text.tag_raise(self.HIT_TAG)

    def detach(self) -> None:
        super().detach()
        self.hide()

    def init(self) -> None:
        self.window:BetterTk = BetterTk(self.text)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.resizable(False, False)
        self.window.topmost(True)
        self.replace:tk.Misc = None
        self.shown:bool = True

        # Left
        left = tk.Frame(self.window, bg="black", highlightthickness=0, bd=0)
        left.pack(fill="both", expand=True, side="left")
        label = tk.Label(left, text="Find:", bg="black", fg="white", anchor="w")
        label.grid(row=1, column=1, sticky="news", padx=5, pady=5)
        self.find:tk.Text = tk.Text(left, height=1, bd=2, width=30,
                                    highlightthickness=0)
        self.find.grid(row=1, column=2, columnspan=3, pady=5, sticky="news")
        self.find.bind("<Tab>", self.tab_pressed)
        self.find.bind("<Return>", self.return_pressed)
        self.find.bind("<Shift-Return>", self.unreturn_pressed)
        self.find.bind("<KP_Enter>", self.return_pressed)
        self.find.bind("<Escape>", lambda e: self.hide())
        MiniPlugin(self.find).attach()
        # Checkboxes
        l = tk.Label(left, text="Options:", bg="black", fg="white", anchor="w")
        l.grid(row=3, column=1, padx=5, pady=(0,5))
        self.regex:Checkbox = Checkbox(left, text="Regex")
        self.matchcase:Checkbox = Checkbox(left, text="Match case")
        self.wholeword:Checkbox = Checkbox(left, text="Whole word")
        self.regex.grid(row=3, column=2, pady=(5,), padx=(0,5))
        self.matchcase.grid(row=3, column=3, pady=(5,), padx=5)
        self.wholeword.grid(row=3, column=4, pady=(5,), padx=(5,0))

        # Right
        right = tk.Frame(self.window, bg="black", bd=0)
        right.pack(fill="both", expand=True, side="right")
        close = tk.Button(right, activebackground="grey", bg="black",
                          activeforeground="white", fg="white",
                          text="Close", command=self.hide, highlightthickness=0)
        close.pack(fill="x", side="top", pady=(5,0), padx=5)
        self.button = tk.Button(right, activebackground="grey", bg="black",
                                activeforeground="white", fg="white",
                                text="Find Next", command=self._find,
                                highlightthickness=0)
        self.button.pack(fill="x", side="top", pady=5, padx=5)
        self.button.bind("<Tab>", self.tab_pressed)
        self.find.focus_set()
        self.fill_in_find()

    def __new__(Cls, plugin:BasePlugin, text:tk.Text, *args, **kwargs):
        self:FindReplaceManager = getattr(text, "findreplacemanager", None)
        if self is None:
            self:FindReplaceManager = super().__new__(Cls, *args, **kwargs)
            text.findreplacemanager:FindReplaceManager = self
        return self

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if event.state&SHIFT:
            return False
        return True

    def do(self, on:str) -> Break:
        if on == "control-f":
            self.open_find()
            return True
        if on in ("control-r", "control-h"):
            self.open_replace()
            return True
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def open_find(self) -> None:
        self.show()
        self.window.title("Find")
        # Already setup correctly
        if self.replace is None:
            return None
        # Replace => Find
        else:
            self.replace_str:str = self.replace.get("1.0", "end -1c")
            self.replace_label.destroy()
            self.replace.destroy()
            self.replace:tk.Misc = None
            self.button.config(text="Find", command=self._find)
        self.window.focus_force()
        self.window.focus_set()
        self.find.focus_set()

    def open_replace(self) -> None:
        self.show()
        self.window.title("Replace")
        # Find => Replace
        if self.replace is None:
            self.button.config(text="Replace All", command=self._replace)
            self.replace = tk.Text(self.find.master, height=1, bd=2, width=30,
                                    highlightthickness=0)
            self.replace.grid(row=2, column=2, columnspan=3, pady=(0, 10),
                              sticky="news")
            self.replace.bind("<Tab>", self.tab_pressed)
            self.replace.bind("<Return>", self.return_pressed)
            self.replace.bind("<KP_Enter>", self.return_pressed)
            self.replace_label = tk.Label(self.find.master, text="Replace:",
                                          bg="black", fg="white", anchor="w")
            self.replace_label.grid(row=2, column=1, sticky="news", padx=5,
                                    pady=(0,5))
            MiniPlugin(self.replace).attach()
            self.replace.insert("end", self.replace_str)
            self.replace.bind("<Escape>", lambda e: self.hide())
        self.window.focus_force()
        self.window.focus_set()

    def fill_in_find(self) -> None:
        # Add whatever the user has selected in the editor
        start, end = self.text.plugin.get_selection()
        if start != end:
            self.find.delete("1.0", "end")
            self.find.insert("1.0", self.text.get(start, end))
        # Select everything in the find box
        self.find.plugin.set_selection("1.0", "end -1c")
        self.find.focus_set()

    def show(self) -> None:
        if self.window is None:
            self.init()
        self.fill_in_find()
        if self.shown:
            return None
        self.shown:bool = True
        self.window.deiconify()
        if self.geom is not None:
            self.window.geometry(self.geom)

    def hide(self) -> None:
        self.clear_hits()
        if self.window is None:
            return None
        if not self.shown:
            return None
        self.shown:bool = False
        geom:str = self.window.geometry()
        self.geom:str = geom[geom.index("+"):]
        self.window.withdraw()
        self.text.focus_set()

    def _find(self, start:str=None) -> None:
        if start is None:
            fst, snd = self.plugin.get_selection()
            start:str = fst if self.swap else snd
        find, flags = self.get_find_params()
        if (find, flags) == self.find_cache:
            if self.swap:
                res = self.text.tag_prevrange(self.HIT_TAG, start)
            else:
                res = self.text.tag_nextrange(self.HIT_TAG, start)
            if res:
                a, b = res
            else:
                res = self.text.tag_nextrange(self.HIT_TAG, "1.0", "end")
                if res:
                    a, b = res
                else:
                    return None
        else:
            self.clear_hits()
            self.find_cache:tuple[str,int] = (find, flags)
            a, b = self._find_all(find, flags, start)
        self.plugin.set_selection(a, b)
        self.text.event_generate("<<Move-Insert>>", data=(b,))

    def _find_all(self, find:str, flags:int, start:str) -> tuple[str,str]:
        finds:int = 0
        first_a = first_b = None
        while True:
            start:str = self.text.index(start)
            a, b = start.split(".")
            a, b = int(a), int(b)
            text:str = self.text.get(start, "end")
            l, c, size = self._search(text, find, flags)
            if size == -1:
                self.report_error(l, c)
                return first_a, first_b
            if size == 0:
                a, b = 1, 0
                text:str = self.text.get("1.0", start)
                l, c, size = self._search(text, find, flags)
            if size == 0:
                return first_a, first_b
            if l == 0:
                a:str = f"{a}.{b+c}"
            else:
                a:str = f"{a+l}.{c}"
            b:str = f"{a} +{size}c"
            self.text.tag_add(self.HIT_TAG, a, b)

            finds += 1
            if first_a is None:
                first_a, first_b = a, b
            elif first_a == a:
                break
            if finds >= self.MAX_FINDS:
                print("[ERROR]: Too many matches")
                break
            start:str = b
        return first_a, first_b

    def _replace(self, start:str="insert") -> None:
        find, replace, flags = self.get_replace_params()
        print(f"Implement: replace {find!r} {replace!r} {flags}")

    def _search(self, string:str, reg:str, flags:int) -> tuple[int,int,int]:
        try:
            reg = re.compile(reg, flags)
        except re.error as error:
            return error.msg, error.pos, -1
        match = re.search(reg, string)
        if match is None:
            return 0, 0, 0
        s, e = match.span()
        size:str = e - s
        before:str = string[:s]
        line:int = before.count("\n")
        if line == 0:
            chars:int = len(before)
        else:
            chars:int = len(before)-before.rfind("\n")-1
        return line, chars, size

    def report_error(self, msg:str, pos:int) -> None:
        title:str = "Bad regex"
        msg:str = f"The regex has an error at {pos=}:\n{msg!r}"
        telluser(self.text, title=title, message=msg, center=True,
                 center_widget=self.text, icon="error")

    def get_find_params(self) -> tuple[str,int]:
        find:str = self.format_str(self.find.get("1.0", "end -1c"))
        flags:int = 0
        if not self.matchcase.ticked:
            flags |= re.IGNORECASE
        if not self.regex.ticked:
            find:str = re.escape(find)
        if self.wholeword.ticked:
            find:str = fr"(?<=\b){find}(?=\b)"
        return find, flags

    def get_replace_params(self) -> tuple[str,str,dict]:
        find, kwargs = self.get_find_params()
        replace:str = self.format_str(self.replace.get("1.0", "end -1c"))
        return find, replace, kwargs

    def tab_pressed(self, event:tk.Event) -> str:
        if event.widget == self.button:
            self.find.focus_set()
        elif event.widget == self.find:
            if self.replace is None:
                self.button.focus_set()
            else:
                self.replace.focus_set()
        elif event.widget == self.replace:
            self.button.focus_set()
        return "break"

    def return_pressed(self, event:tk.Event=None) -> str:
        self.button.invoke()
        return "break"

    def unreturn_pressed(self, event:tk.Event=None) -> str:
        self.swap:bool = True
        self.button.invoke()
        self.swap:bool = False
        return "break"

    def format_str(self, string:str) -> str:
        output:str = ""
        escaping:bool = False
        for char in string:
            if char == "\\":
                if escaping:
                    output += "\\"
                escaping:bool = not escaping
            elif escaping and (char in ESCAPED):
                output += ESCAPED[char]
                escaping:bool = False
            else:
                if escaping:
                    output += "\\"
                output += char
        return output

    def clear_hits(self) -> None:
        if self.find_cache is None:
            return None
        self.text.tag_remove(self.HIT_TAG, "1.0", "end")
        self.find_cache:tuple[str,int] = None