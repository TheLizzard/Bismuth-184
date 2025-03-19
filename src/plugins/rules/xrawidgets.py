from __future__ import annotations
from idlelib.sidebar import LineNumbers
import tkinter as tk

from .baserule import Rule
from bettertk.menu import BetterMenu
from bettertk.betterscrollbar import BetterScrollBarVertical, \
                                     BetterScrollBarHorizontal


class SingletonMeta(type):
    def __call__(Class:type, plugin:BasePlugin, text:tk.Text) -> Class:
        name:str = "_singleton_" + Class.__name__.lower()
        self:Cls = getattr(text, name, None)
        if self is None:
            self:Cls = super().__call__(plugin, text)
            setattr(text, name, self)
        return self


class BarManager(Rule, metaclass=SingletonMeta):
    __slots__ = "label", "text"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("reparentmanager",True)]

    FORMAT:str = "Ln: {line} Col: {column}"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> BarManager:
        super().__init__(plugin, text, ons=("<<Insert-Moved>>",))
        self.label:tk.Label = tk.Label(plugin.master, text="", bg="black",
                                       fg="white", anchor="e")
        self.text:tk.Text = text

    def attach(self) -> None:
        super().attach()
        self.text.add_widget(self.label, row=4, padx=10)

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        idx:str = self.text.index("insert")
        if idx == "": # No idea why this happens
            return False
        return idx, True

    def do(self, on:str, idx:str) -> Break:
        line, column = idx.split(".")
        self.label.config(text=self.FORMAT.format(line=line, column=column))


class LineManager(Rule, LineNumbers, metaclass=SingletonMeta):
    __slots__ = "text", "parent", "prev_end", "sidebar_text"
    REQUESTED_LIBRARIES:tuple[str] = "reparentmanager", "scrollbarmanager"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("reparentmanager",True),
                                                 ("scrollbarmanager",True)]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> BarManager:
        evs:tuple[str] = (
                           # Update the linenumbers
                           "<<Raw-After-Insert>>", "<<Raw-After-Delete>>",
                           "<<Undo-Triggered>>", "<<Redo-Triggered>>",
                           "<<Reloaded-File>>",
                           # If the text widget scrolls, scroll the linenumbers
                           "<<Y-Scroll>>",
                           # Display user marks
                           "<<Set-UMark>>", "<<Remove-UMark>>",
                         )
        Rule.__init__(self, plugin, text, ons=evs)
        self.text:tk.Text = text
        self.parent:tk.Misc = plugin.master
        LineNumbers.init_widgets(self)

        bounce:tuple[str] = (
                              "<MouseWheel>", "<FocusIn>",
                              # Redirect all of these events to the tk.Text
                              "<Button-1>", "<B1-Motion>", "<Double-Button-1>",
                              "<Triple-Button-1>", "<B1-Motion>",
                              "<Button-4>", "<Button-5>",
                            )
        for on in bounce:
            better_on:str = on.removeprefix("<").removesuffix(">").lower()
            func = lambda e, bon=better_on, on=on: self.bounce(e, bon, on)
            self.sidebar_text.bind(on, func)
        for on in ("<Enter>", "<Leave>"):
            self.sidebar_text.bind(on, lambda e: "break")

    # Override idlelib's implementation of update_font
    def update_font(self):
        self.sidebar_text.config(font=self.text.cget("font"))

    def attach(self) -> None:
        super().attach()
        self.text.add_widget(self.sidebar_text, column=-2)
        self.sidebar_text.config(bg=self.text.cget("bg"),
                                 fg=self.text.cget("fg"))
        self.sidebar_text.tag_remove("umark", "1.0", "end")
        self.sidebar_text.tag_config("umark", foreground="cyan")
        self.text.after(10, self.update_font)
        #self.sidebar_text.tag_config("sel", foreground="", background="")

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        umark_line:int = -1
        if on == "<raw-after-insert>":
            if "\n" not in event.data["raw"][1]:
                return False
        if on.endswith("-umark>"):
            umark_line:int = event.data
        return umark_line, True

    def do(self, on:str, umark_line:int) -> Break:
        if on in ("<y-scroll>", "<reloaded-file>"):
            self.sidebar_text.yview("moveto", self.text.yview()[0])
            return False
        if on in ("<raw-after-insert>", "<raw-after-delete>",
                  "<undo-triggered>", "<redo-triggered>"):
            end:int = int(float(self.text.index("end -1c")))
            LineNumbers.update_sidebar_text(self, end)
            return False
        if on == "<set-umark>":
            self.sidebar_text.tag_add("umark", f"{umark_line}.0",
                                      f"{umark_line}.0 lineend")
            return False
        if on == "<remove-umark>":
            self.sidebar_text.tag_remove("umark", f"{umark_line}.0",
                                         f"{umark_line}.0 lineend")
            return False
        raise RuntimeError(f"Unhandled {on!r} in {self.__class__.__name__}")

    def bounce(self, event:tk.Event, on:str, proper_on:str) -> str:
        if on == "focusin":
            self.text.focus_set()
            return "break"

        mouse_event = on.startswith("button-") or on.startswith("b1-") or \
                      on.startswith("double-") or on.startswith("triple-") or \
                      (on == "mousewheel")
        if mouse_event:
            self.text.focus_set()
            kwargs:dict = {} if on != "mousewheel" else {"delta":event.delta}
            self.text.event_generate(proper_on, x=0, y=event.y, **kwargs)
            return "break"

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")


class ScrollbarManager(Rule, metaclass=SingletonMeta):
    __slots__ = "old_yscrollcommand", "old_xscrollcommand", "yscrollbar", \
                "xscrollbar"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("reparentmanager",True)]

    # https://stackoverflow.com/q/35412972/11106801
    HORIZONTAL_BAR:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ScrollBarManager:
        super().__init__(plugin, text, ons=())
        self.yscrollbar = BetterScrollBarVertical(plugin.master,
                                                  command=text.yview)
        if self.HORIZONTAL_BAR:
            self.xscrollbar = BetterScrollBarHorizontal(plugin.master,
                                                        command=text.xview)
            self.xscrollbar.hide:bool = True

    def attach(self) -> None:
        super().attach()
        self.old_yscrollcommand = self.widget.cget("yscrollcommand")
        self.widget.config(yscrollcommand=self.yset)
        self.widget.add_widget(self.yscrollbar, column=2)
        if self.HORIZONTAL_BAR:
            self.old_xscrollcommand = self.widget.cget("xscrollcommand")
            self.widget.config(xscrollcommand=self.xset)
            self.widget.add_widget(self.xscrollbar, row=2)

    def detach(self) -> None:
        super().detach()
        if self.HORIZONTAL_BAR:
            self.widget.config(xscrollcommand=self.old_xscrollcommand)
        self.widget.config(yscrollcommand=self.old_yscrollcommand)

    def yset(self, low:str, high:str) -> None:
        self.widget.event_generate("<<Y-Scroll>>")
        self.yscrollbar.set(low, high)

    def xset(self, low:str, high:str) -> None:
        self.widget.event_generate("<<X-Scroll>>", data=(low, high))
        self.xscrollbar.set(low, high)


class MenuManager(Rule, metaclass=SingletonMeta):
    __slots__ = "menu"
    REQUESTED_LIBRARIES:list[tuple[str,bool]] = [("reparentmanager",True)]

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ScrollBarManager:
        super().__init__(plugin, text, ons=())
        self.menu:BetterMenu = BetterMenu(plugin.master, direction="horizontal")
        self._create_menu()

    def _create_menu(self) -> None:
        filemenu = self.menu.add_submenu("File", "vertical")
        editmenu = self.menu.add_submenu("Edit", "vertical")
        formatmenu = self.menu.add_submenu("Format", "vertical")
        runmenu = self.menu.add_submenu("Run", "vertical")
        settingsmenu = self.menu.add_submenu("Settings", "vertical")
        helpmenu = self.menu.add_submenu("Help", "vertical")

        filemenu.add_command("Open")
        filemenu.add_command("Save")
        filemenu.add_command("Save As")

        editmenu.add_command("Undo")
        editmenu.add_command("Redo")
        editmenu.add_separator()
        editmenu.add_command("Select All")
        editmenu.add_command("Cut")
        editmenu.add_command("Copy")
        editmenu.add_command("Paste")
        editmenu.add_separator()
        editmenu.add_command("Find")
        editmenu.add_command("Replace")
        editmenu.add_separator()
        editmenu.add_command("Go to Line")

        formatmenu.add_command("Indent Region")
        formatmenu.add_command("Dedent Region")
        formatmenu.add_separator()
        formatmenu.add_command("Toggle Comment Out Region")

        runmenu.add_command("Run")
        runmenu.add_command("Run with args")
        runmenu.add_separator()
        runmenu.add_command("Python Shell")

        helpmenu.add_command("About")
        helpmenu.add_command("Search Help Docs")

    def attach(self) -> None:
        super().attach()
        self.widget.add_widget(self.menu, row=-5, column=-5, columnspan=10)