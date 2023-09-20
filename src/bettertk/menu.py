from __future__ import annotations
from itertools import zip_longest
import tkinter as tk

try:
    from . import BetterTk, IS_UNIX, IS_WINDOWS
except ImportError:
    from __init__ import BetterTk, IS_UNIX, IS_WINDOWS


FRAME_KWARGS:dict[str,str] = dict(highlightthickness=0, bd=0, bg="black")
BUTTON_KWARGS:dict[str:str] = dict(relief="flat", bg="black", fg="white",
                                   activebackground="grey",
                                   activeforeground="white", anchor="nw",
                                   highlightthickness=0, bd=0)
MENU_BD:int = 2


def remove_titlebar(root:tk.Tk|tk.Toplevel) -> None:
    if IS_UNIX:
        root.attributes("-type", "splash")
    elif IS_WINDOWS:
        root.overrideredirect()
    else:
        raise NotImplementedError("UnrecognisedOS")

def stack_diff(old:list[T], new:list[T]) -> tuple[list[T],list[T]]:
    remove:list[T] = []
    add:list[T] = []
    diverg:bool = False
    for o, n in zip_longest(old, new):
        if o != n:
            diverg:bool = True
        if diverg:
            if o:
                remove.append(o)
            if n:
                add.append(n)
    return remove, add


class MenuItem:
    __slots__ = "widget", "parentmenu"

    def __init__(self, widget:tk.Misc, parentmenu:BetterMenuBase):
        self.parentmenu:BetterMenuBase = parentmenu
        self.widget:tk.Misc = widget
        self.widget.menuitem:MenuItem = self


class BetterMenuBase:
    __slots__ = "parent", "shown", "direction", "container", "rootmenu"

    def __init__(self, parent:MenuItem, direction:str) -> BetterMenuBase:
        assert isinstance(direction, str), "TypeError"
        assert isinstance(parent, MenuItem), "TypeError"
        assert direction in ("horizontal", "vertical"), "ValueError"
        self.rootmenu:BetterMenu = parent.parentmenu.rootmenu
        self.direction:bool = direction
        self.parent:MenuItem = parent
        self.shown:bool = False

        self.container:tk.Misc = self.create_container()

    def mouse_over(self, event:tk.Event) -> None:
        if self.rootmenu == self:
            return None
        get_widget = lambda submenu: submenu.parent.widget
        stack = tuple(map(get_widget, self.rootmenu.stack))
        if event.widget in stack:
            return None
        self.rootmenu.change_shown_to(self)

    def _show(self) -> None:
        if self.shown:
            return None
        self.shown:bool = True
        self.show()

    def _hide(self) -> None:
        if not self.shown:
            return None
        self.shown:bool = False
        self.hide()

    def add_command(self, name:str, func:Function=None) -> MenuItem:
        def wrapper() -> None:
            self.rootmenu.change_shown_to(None)
            if func is not None:
                func()
        button:tk.Button = tk.Button(self.container, text=name, command=wrapper,
                                     **BUTTON_KWARGS)
        if self.direction == "horizontal":
            button.pack(side="left", anchor="nw", fill="both")
        else:
            button.pack(side="top", anchor="nw", fill="both")
        button.bind("<Enter>", self.mouse_over)
        return MenuItem(button, self)

    def add_separator(self, thickness:int=2, colour:str="grey",
                                             padding:int=5) -> MenuItem:
        if self.direction == "horizontal":
            width:int = thickness
            height:int = 0
            pack_kwargs:dict = dict(side="left")
        else:
            width:int = 0
            height:int = thickness
            pack_kwargs:dict = dict(side="top")
        canvas:tk.Canvas = tk.Canvas(self.container, bd=0, highlightthickness=0,
                                     width=width, height=height, bg=colour)
        canvas.pack(anchor="nw", fill="both", padx=padding, **pack_kwargs)
        canvas.bind("<Enter>", self.mouse_over)
        return MenuItem(canvas, self)

    def add_submenu(self, name:str, direction:str) -> BetterSubMenu:
        def wrapper(event:tk.Event=None) -> None:
            if (event is not None) and (len(self.rootmenu.stack) == 0):
                return None
            self.rootmenu.change_shown_to(submenu)
        menuitem:MenuItem = self.add_command(name, wrapper)
        menuitem.widget.bind("<Enter>", wrapper)
        submenu:BetterSubMenu = BetterSubMenu(menuitem, direction)
        return submenu

    def create_container(self) -> tk.Misc:
        raise NotImplementedError("Override this method")

    def show(self) -> None:
        raise NotImplementedError("Override this method")

    def hide(self) -> None:
        raise NotImplementedError("Override this method")


class BetterSubMenu(BetterMenuBase):
    __slots__ = "root"

    def __init__(self, parent:MenuItem, direction:str) -> BetterSubMenu:
        super().__init__(parent, direction)

    def create_container(self) -> tk.Misc:
        button:tk.Button = self.parent.widget
        self.root:tk.Misc = tk.Toplevel(button)
        self.root.config(bg="grey")
        self.root.withdraw()
        frame:tk.Frame = tk.Frame(self.root, bg="black", bd=0,
                                  highlightthickness=0)
        frame.pack(fill="both", expand=True, padx=MENU_BD, pady=MENU_BD)
        return frame

    def show(self) -> None:
        x = self.parent.widget.winfo_rootx()
        y = self.parent.widget.winfo_rooty()
        if self.parent.parentmenu.direction == "horizontal":
            y += self.parent.widget.winfo_height()
        else:
            x += self.parent.widget.winfo_width()
        self.root.geometry(f"+{x}+{y}")
        self.root.iconify()
        remove_titlebar(self.root)
        self.root.attributes("-topmost", True)

    def hide(self) -> None:
        self.root.withdraw()

    def get_stack(self) -> Iterable[BetterMenuBase]:
        return reversed(tuple(self._get_stack()))

    def _get_stack(self) -> Iterable[BetterMenuBase]:
        while self != self.parent.parentmenu:
            yield self
            self:BetterSubMenu = self.parent.parentmenu


class BetterMenu(BetterMenuBase):
    __slots__ = "stack", "rootmenu"

    def __init__(self, master:tk.Misc, direction:str) -> BetterMenu:
        self.rootmenu:BetterMenu = self
        super().__init__(MenuItem(master, self), direction)
        self.stack:tuple[BetterMenuBase] = ()
        self.shown:bool = True

    def change_shown_to(self, submenu:BetterSubMenu) -> None:
        if submenu is None:
            new:tuple[BetterMenuBase] = ()
        else:
            new:tuple[BetterMenuBase] = tuple(submenu.get_stack())
        removes, adds = stack_diff(self.stack, new)
        for submenu in removes:
            submenu._hide()
        for submenu in adds:
            submenu._show()
        self.stack = new

    def get_stack(self) -> Iterable[BetterMenuBase]:
        return ()

    def create_container(self) -> tk.Misc:
        def hide_all(event:tk.Event) -> None:
            if len(self.stack) == 0:
                return None
            widget:tk.Misc = event.widget
            if isinstance(widget, str):
                return None # Don't know why this happens
            while widget is not None:
                if widget == frame:
                    return None
                widget:tk.Misc = widget.master
            self.change_shown_to(None)
        frame:tk.Frame = tk.Frame(self.parent.widget, **FRAME_KWARGS)
        frame.bind_all("<Button-1>", hide_all, add=True)
        return frame

    def pack(self, **kwargs) -> None:
        return self.container.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        return self.container.grid(**kwargs)

    def place(self, **kwargs) -> None:
        return self.container.place(**kwargs)

    def pack_forget(self, **kwargs) -> None:
        return self.container.pack_forget(**kwargs)

    def grid_forget(self, **kwargs) -> None:
        return self.container.grid_forget(**kwargs)

    def place_forget(self, **kwargs) -> None:
        return self.container.place_forget(**kwargs)


if __name__ == "__main__":
    root = tk.Tk()
    root.config(bg="black")
    menu = BetterMenu(root, direction="horizontal")
    filemenu = menu.add_submenu("File", direction="vertical")
    filemenu.add_command("Open", lambda: print("open"))

    savemenu = filemenu.add_submenu("Save Options", direction="vertical")
    savemenu.add_command("Save", lambda: print("save"))
    savemenu.add_command("Save As", lambda: print("saveas"))

    filemenu.add_separator()
    filemenu.add_command("Close", lambda: print("close"))

    menu.add_command("Edit", lambda: print("edit"))
    menu.add_command("Format", lambda: print("format"))
    menu.pack(anchor="w")

    tk.Text(root, bg="black", fg="white", insertbackground="white").pack()


"""
from __future__ import annotations
from __init__ import BetterTk, IS_UNIX, IS_WINDOWS
import tkinter as tk


class MenuItem:
    __slots__ = "parent", "item"

    def __init__(self, parent:BetterMenuBase, item:tk.Misc) -> MenuItem:
        self.parent:BetterMenuBase = parent
        self.item:tk.Misc = item
        self.item.parent:BetterMenuBase = parent


BUTTON_KWARGS:dict[str:str] = dict(relief="flat", bg="black", fg="white",
                                   activebackground="grey",
                                   activeforeground="white", anchor="nw",
                                   highlightthickness=0, bd=0)
MENU_BD:int = 2


class BetterMenuBase:
    __slots__ = "master", "container", "direction", "shown", "parent", \
                "children", "rootmenu"

    def __init__(self, parent:BetterMenuBase, master:tk.Misc, direction:str):
        assert direction in ("horizontal", "vertical"), "ValueError"
        self.container:tk.Misc = self.create_container(master)
        self.direction:bool = (direction == "horizontal")
        self.children:list[BetterMenuBase] = []
        self.parent:BetterMenuBase = parent
        self.master:tk.Misc = master
        self.shown:bool = False
        if parent is not None:
            self.rootmenu:BetterMenu = parent.rootmenu

    def create_submenu(self, *, direction:str) -> BetterSubMenu:
        child:BetterMenuBase = BetterSubMenu(self, self.container, direction=direction)
        self.children.append(child)
        return child

    def __call__(self, *args) -> None:
        self._show(*args)

    def _show(self, *args) -> None:
        if self.shown:
            return None
        self.shown:bool = True
        self.show(*args)

    def _hide(self) -> None:
        if not self.shown:
            return None
        self.shown:bool = False
        self.hide()
        for child in self.children:
            child._hide()

    def show(self, *args) -> None:
        raise NotImplementedError("Override this method")

    def hide(self) -> None:
        raise NotImplementedError("Override this method")

    def create_container(self, master:tk.Misc) -> tk.Misc:
        raise NotImplementedError("Override this method")

    def get_stack(self) -> list[BetterMenuBase]:
        stack:list[BetterMenuBase] = []
        while self.parent is not None:
            stack.append(self)
            self:BetterMenuBase = self.parent
        return stack

    def add_command(self, name:str, func:Function=None) -> MenuItem:
        def wrapper(event:tk.Event=None) -> None:
            if event is None:
                self.rootmenu.isopen:bool = True
            if not self.rootmenu.isopen:
                return None
            else:
                self.rootmenu.set_stack(self.get_stack())
            if isinstance(func, BetterMenuBase):
                func(button)
            elif func is not None:
                self.rootmenu._hide()
                func()
        button:tk.Button = tk.Button(self.container, text=name, command=wrapper,
                                     **BUTTON_KWARGS)
        button.pack(side="left" if self.direction else "top", anchor="nw",
                    fill="both")
        if isinstance(func, BetterMenuBase):
            button.bind("<Enter>", wrapper)
        return MenuItem(self, button)

    def add_separator(self, thickness:int=2, colour:str="grey",
                      padding:int=5) -> MenuItem:
        canvas:tk.Canvas = tk.Canvas(self.container, bd=0, highlightthickness=0,
                                     width=thickness if self.direction else 0,
                                     height=0 if self.direction else thickness,
                                     bg=colour)
        canvas.pack(side="left" if self.direction else "top",
                    fill="y" if self.direction else "x", anchor="nw",
                    **{("padx" if self.direction else "pady"):padding})
        return MenuItem(self, canvas)


class BetterSubMenu(BetterMenuBase):
    __slots__ = "root"

    def create_container(self, master:tk.Misc) -> tk.Misc:
        self.root:tk.Misc = tk.Toplevel(master)
        self.root.config(bg="grey")
        self.root.withdraw()
        frame:tk.Frame = tk.Frame(self.root, bg="black", bd=0,
                                  highlightthickness=0)
        frame.pack(fill="both", expand=True, padx=MENU_BD, pady=MENU_BD)
        return frame

    def show(self) -> None:
        x, y = self.master.winfo_rootx(), self.master.winfo_rooty()
        if widget.parent.direction:
            y += self.master.winfo_height()
        else:
            x += self.master.winfo_width()
        self.root.geometry(f"+{x}+{y}")
        self.root.iconify()
        self.remove_titlebar(self.root)
        self.root.attributes("-topmost", True)
        #self.container.overrideredirect(True, border=True)
        #self.container.topmost(True)

    @staticmethod
    def remove_titlebar(root:tk.Tk|tk.Toplevel) -> None:
        if IS_UNIX:
            root.attributes("-type", "splash")
        elif IS_WINDOWS:
            root.overrideredirect()
        else:
            raise NotImplementedError("UnrecognisedOS")

    def hide(self) -> None:
        self.root.withdraw()


class BetterMenu(BetterMenuBase):
    __slots__ = "isopen"

    def __init__(self, master:tk.Misc, *, direction:str) -> BetterMenu:
        super().__init__(None, master, direction=direction)
        self.rootmenu:BetterMenu = self
        self.isopen:bool = False
        self.shown:bool = True

    def show(self, *args) -> None:
        raise RuntimeError("Don't call show on <BetterMenu>")

    def hide(self) -> None:
        self.isopen:bool = False
        self.shown:bool = True

    def set_stack(self, stack:list[BetterMenuBase]) -> None:
        self._hide()
        self.isopen:bool = True
        for submenu in stack:
            submenu._show()

    def create_container(self) -> tk.Misc:
        frame:tk.Frame = tk.Frame(master, highlightthickness=0, bg="black")
        master.bind_all("<Button-1>", self.maybe_hide, add=True)
        return frame

    def maybe_hide(self, event:tk.Event) -> None:
        if not self.shown:
            return None
        widget:tk.Event = event.widget
        if isinstance(widget, str):
            # This happens when the widget is destroyed
            #   but the bind_all still activates
            return None
        while widget is not None:
            if widget == self.container:
                return None
            widget:tk.Misc = widget.master
        self._hide()

    def pack(self, **kwargs) -> None:
        return self.container.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        return self.container.grid(**kwargs)

    def place(self, **kwargs) -> None:
        return self.container.place(**kwargs)

    def pack_forget(self, **kwargs) -> None:
        return self.container.pack_forget(**kwargs)

    def grid_forget(self, **kwargs) -> None:
        return self.container.grid_forget(**kwargs)

    def place_forget(self, **kwargs) -> None:
        return self.container.place_forget(**kwargs)


if __name__ == "__main__":
    root = tk.Tk()
    root.config(bg="black")
    menu = BetterMenu(root, direction="horizontal")
    filemenu = menu.create_submenu(direction="vertical")
    savemenu = menu.create_submenu(direction="vertical")

    savemenu.add_command("Save", lambda: print("save"))
    savemenu.add_command("Save As", lambda: print("saveas"))

    filemenu.add_command("Open", lambda: print("open"))
    filemenu.add_command("Save Options", savemenu)
    filemenu.add_separator()
    filemenu.add_command("Close", lambda: print("close"))

    menu.add_command("File", filemenu)
    menu.add_command("Edit", lambda: print("edit"))
    menu.add_command("Format", lambda: print("format"))
    menu.pack(anchor="w")

    tk.Text(root, bg="black", fg="white", insertbackground="white").pack()
"""
