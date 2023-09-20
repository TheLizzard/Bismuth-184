from __future__ import annotations
from idlelib.sidebar import LineNumbers
import tkinter as tk

from .baserule import Rule
from bettertk.menu import BetterMenu
from bettertk.betterscrollbar import BetterScrollBarVertical, \
                                     BetterScrollBarHorizontal


class BarManager(Rule):
    __slots__ = "label"
    REQUESTED_LIBRARIES:tuple[str] = "add_widget", "wrapped"
    REQUESTED_LIBRARIES_STRICT:bool = True

    FORMAT:str = "Ln: {line} Col: {column}"

    def __init__(self, plugin:BasePlugin, widget:tk.Misc) -> BarManager:
        super().__init__(plugin, widget, ons=("<<Move-Insert>>",))
        self.label:tk.Label = tk.Label(widget.master, text="", bg="black",
                                       fg="white", anchor="e")

    def attach(self) -> None:
        super().attach()
        self.widget.add_widget(self.label, row=4, padx=10)

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return event.data[0], True

    def do(self, on:str, idx:str) -> Break:
        line, column = self.widget.index(idx).split(".")
        self.label.config(text=self.FORMAT.format(line=line, column=column))


class LineManager(Rule, LineNumbers):
    __slots__ = "text", "parent", "prev_end", "sidebar_text"
    REQUESTED_LIBRARIES:tuple[str] = "add_widget", "scroll_bar"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> BarManager:
        evs:tuple[str] = (
                           # After any change update the linenumbers
                           "<<After-Insert>>", "<<After-Delete>>",
                           # If the text widget scrolls, scroll the linenumbers
                           "<<Y-Scroll>>",
                           # If the user presses undo/redo
                           "<Control-Z>", "<Control-z>",
                           "<<Undo-Triggered>>", "<<Redo-Triggered>>",
                         )
        Rule.__init__(self, plugin, text, ons=evs)
        self.text:tk.Text = text
        self.parent:tk.Misc = text.master
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

    def attach(self) -> None:
        super().attach()
        self.text.add_widget(self.sidebar_text, column=-2)
        self.sidebar_text.config(bg=self.text.cget("bg"),
                                 fg=self.text.cget("fg"))
        #self.sidebar_text.tag_config("sel", foreground="", background="")

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        data:tuple[str,str] = None
        if on == "<after-insert>":
            if "\n" not in event.data[1]:
                return False
        if on == "<y-scroll>":
            data:tuple[str,str] = event.data
        return data, True

    def do(self, on:str, data:tuple[str,str]) -> Break:
        if on == "<y-scroll>":
            self.sidebar_text.yview("moveto", data[0])
            return False
        if on in ("<after-insert>", "<after-delete>", "<control-z>",
                  "<undo-triggered>", "<redo-triggered>"):
            end:int = int(float(self.text.index("end -1c")))
            LineNumbers.update_sidebar_text(self, end)
            return False
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

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


class ScrollbarManager(Rule):
    __slots__ = "old_yscrollcommand", "yscrollbar", "xscrollbar"
    REQUESTED_LIBRARIES:tuple[str] = "add_widget"
    REQUESTED_LIBRARIES_STRICT:bool = True

    HORIZONTAL_BAR:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ScrollBarManager:
        super().__init__(plugin, text, ons=())
        self.yscrollbar = BetterScrollBarVertical(text.master,
                                                  command=text.yview)
        if self.HORIZONTAL_BAR:
            self.xscrollbar = BetterScrollBarHorizontal(text.master,
                                                        command=text.xview)
            self.xscrollbar.hide:bool = True

    def attach(self) -> None:
        super().attach()
        self.widget.scroll_bar:bool = True
        self.old_yscrollcommand = self.widget.cget("yscrollcommand")
        self.widget.config(yscrollcommand=self.yset)
        self.widget.add_widget(self.yscrollbar, column=2)
        if self.HORIZONTAL_BAR:
            self.widget.config(xscrollcommand=self.xset)
            self.widget.add_widget(self.xscrollbar, row=2)

    def detach(self) -> None:
        super().detach()
        self.widget.scroll_bar:bool = False
        self.widet.config(yscrollcommand=self.old_yscrollcommand)

    def yset(self, low:str, high:str) -> None:
        self.widget.event_generate("<<Y-Scroll>>", data=(low, high))
        self.yscrollbar.set(low, high)

    def xset(self, low:str, high:str) -> None:
        self.widget.event_generate("<<X-Scroll>>", data=(low, high))
        self.xscrollbar.set(low, high)


class MenuManager(Rule):
    __slots__ = "menu"
    REQUESTED_LIBRARIES:tuple[str] = "add_widget"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> ScrollBarManager:
        super().__init__(plugin, text, ons=())
        self.menu:BetterMenu = BetterMenu(text.master, direction="horizontal")
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
