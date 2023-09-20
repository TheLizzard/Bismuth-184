from __future__ import annotations
from sys import stderr
import tkinter as tk
import os

try:
    from .base_explorer import NEW_ITEM_NAME
    from .explorer import Explorer, isfile, isfolder, SELECTED_COLOUR
except ImportError:
    from base_explorer import NEW_ITEM_NAME
    from explorer import Explorer, isfile, isfolder, SELECTED_COLOUR
from bettertk import BetterTk, IS_UNIX, IS_WINDOWS
from bettertk.messagebox import askyesno, tell


if IS_UNIX:
    OPEN_IN_EXPLORER:str = 'nautilus "{path}"'
elif IS_WINDOWS:
    OPEN_IN_EXPLORER:str = 'explorer "{path}"'
else:
    OPEN_IN_EXPLORER:str = None
    sys.stderr.write("Unknown OS, can't open files/folders in real explorer.\n")


BKWARGS:dict = dict(activeforeground="white", activebackground="grey", bd=0,
                    bg="black", relief="flat", fg="white", justify="left",
                    highlightthickness=0, anchor="nw")
MENU_BD:int = 2
MENU_SEP_PADY:int = 5
MENU_SEP_HEIGHT:int = 2
CIRCLE_PADX:int = 5
CIRCLE_RADIUS:int = 4
CIRCLE_FILL:str = "cyan"
CIRCLE_PRE_NAME:bool = False
BIN_FOLDER:str = os.path.join(os.path.dirname(__file__), "$BIN", "{idx}")
DEBUG:bool = False


def chain(*funcs:tuple[Function[None]]) -> Function[None]:
    def inner() -> None:
        for func in funcs:
            func()
    return inner


class Menu:
    __slots__ = "root", "master", "children", "shown", "frame", "on_cancel"

    def __init__(self, master:tk.Misc) -> Menu:
        self.master:tk.Misc = master
        self.root:tk.Toplevel = tk.Toplevel(self.master)
        self.root.config(bg="grey")
        self.root.withdraw()
        self.shown:bool = False
        self.frame:tk.Frame = tk.Frame(self.root, bg="black", bd=0,
                                        highlightthickness=0)
        self.frame.pack(fill="both", expand=True, padx=MENU_BD, pady=MENU_BD)
        self.children:list[tk.Misc] = []
        self.master.bind_all("<Escape>", self.cancel, add=True)
        self.master.bind_all("<Button-1>", self.cancel, add=True)
        self.on_cancel:Function[None] = lambda: None

    def _ischild(self, widget:tk.Misc) -> bool:
        if isinstance(widget, str):
            # This happens when the widget is destroyed
            #   but the bind_all still activates
            return False
        while widget is not None:
            if widget == self.root:
                return True
            widget:tk.Misc = widget.master
        return False

    def hide(self, *, cancelled:bool=False) -> str|None:
        if not self.shown:
            return None
        self.shown:bool = False
        self.master.focus_set()
        self.root.withdraw()
        if cancelled:
            self.on_cancel()

    def cancel(self, event:tk.Event=None) -> None:
        if not self.shown:
            return None
        if (event is not None) and self._ischild(event.widget):
            return None
        self.hide(cancelled=True)

    def add(self, text:str, command:Function) -> int:
        command:Function = chain(self.hide, command)
        widget:tk.Button = tk.Button(self.frame, command=command, text=text,
                                     **BKWARGS)
        widget.pack(fill="x", side="top")
        self.children.append(widget)
        return len(self.children)-1

    def add_separator(self) -> int:
        widget:tk.Frame = tk.Frame(self.frame, bd=0, highlightthickness=0,
                                   bg="grey", height=MENU_SEP_HEIGHT, width=1)
        widget.pack(fill="x", side="top", pady=MENU_SEP_PADY)
        self.children.append(widget)
        return len(self.children)-1

    def config(self, id:int, **kwargs) -> None:
        if "command" in kwargs:
            kwargs["command"] = chain(self.hide, kwargs.pop("command"))
        self.children[id].config(**kwargs)

    def popup(self, widget:tk.Misc, pos:tuple[int,int]=None) -> None:
        self.root.geometry("+{}+{}".format(*(pos or widget.winfo_pointerxy())))
        if self.shown:
            return None
        self.shown:bool = True
        self.root.iconify()
        self.remove_titlebar()
        self.root.attributes("-topmost", True)

    def remove_titlebar(self) -> None:
        if IS_UNIX:
            self.root.attributes("-type", "splash")
        elif IS_WINDOWS:
            self.root.overrideredirect()
        else:
            raise NotImplementedError("UnrecognisedOS")


class ExpandedExplorer(Explorer):
    __slots__ = "cwd", "menu", "set_cwd_id", "bin_folder", "renaming", \
                "creating"

    def __init__(self, master:tk.Misc) -> ExpandedExplorer:
        self.cwd:tk.Frame = None
        super().__init__(master)
        self._create_menu()
        self.ggiver.right_click:Function[tk.Frame,str] = self.right_click
        self.bin_folder:str = self._find_empty_bin()
        os.makedirs(self.bin_folder, exist_ok=True)
        self.renaming:bool = False
        self.creating:bool = False
        self.master.bind_all("<Escape>", self.finish_rename, add=True)
        self.master.bind_all("<Button-1>", self.maybe_cancel_rename, add=True)

    # Bin
    def _find_empty_bin(self) -> str:
        i:int = 0
        while True:
            bin_folder:str = BIN_FOLDER.format(idx=i)
            if not self.root.filesystem.exists(bin_folder):
                break
            if len(self.root.filesystem.listdir(bin_folder)[0]) == 0:
                break
            i += 1
        return bin_folder

    # Menu
    def _create_menu(self) -> None:
        self.menu:Menu = Menu(self.master)
        self.menu.add("Rename", self.rename)
        self.menu.add("Delete", self.delete)
        self.menu.add_separator()
        self.menu.add("New file", self.newfile)
        self.menu.add("New folder", self.newfolder)
        self.menu.add_separator()
        self.set_cwd_id:int = self.menu.add("Set as working dir", self.set_cwd)
        self.menu.add("Open in explorer", self.open_in_explorer)
        self.menu.on_cancel:Function[None] = self.menu_cancel

    def right_click(self, frame:tk.Frame) -> str:
        if frame is None:
            return None
        self.ggiver._select(frame)
        self.changing:tk.Frame = frame
        if super()._get_closest_folder(frame) == self.cwd:
            self.menu.config(self.set_cwd_id, text="Remove exec path (cwd)",
                             command=self.remove_cwd)
        else:
            self.menu.config(self.set_cwd_id, text="Set exec path (cwd)",
                             command=self.set_cwd)
        self.menu.popup(self.master)

    def menu_cancel(self) -> None:
        self.changing:tk.Frame = None

    # Cwd stuff
    def set_cwd(self) -> None:
        self.master.update_idletasks()
        if self.cwd is not None:
            self.remove_cwd()
        self.cwd:tk.Frame = super()._get_closest_folder(super().get_selected())
        data:tuple[str] = (self.cwd.item.fullpath,)
        self.master.event_generate("<<Explorer-Set-CWD>>", data=data)
        height:int = self.cwd.winfo_height()
        self.cwd.cwd_dot = tk.Canvas(self.cwd, bd=0, bg="black",
                                     highlightthickness=0,
                                     width=CIRCLE_RADIUS*2+CIRCLE_PADX,
                                     height=height)
        self.cwd.cwd_dot.grid(row=1, column=5-2*CIRCLE_PRE_NAME)
        centrex = CIRCLE_RADIUS/2+CIRCLE_PADX
        self.cwd.cwd_dot.create_circle(centrex, int(height/2), CIRCLE_RADIUS,
                                       fill=CIRCLE_FILL, outline=CIRCLE_FILL,
                                       width=0)
        if super().get_selected() == self.cwd:
            self.cwd.cwd_dot.config(bg=SELECTED_COLOUR)
        self.changing:tk.Frame = None

    def recolour_frame(self, frame:tk.Frame, bg:str) -> None:
        super().recolour_frame(frame, bg)
        if (frame == self.cwd) and (frame is not None):
            frame.cwd_dot.config(bg=bg)

    def remove_cwd(self) -> None:
        self.master.event_generate("<<Explorer-Unset-CWD>>")
        self.cwd.cwd_dot.destroy()
        self.cwd:tk.Frame = None
        self.changing:tk.Frame = None

    # Rename
    def rename(self) -> None:
        self.renaming:bool = True
        self.changing.entry = tk.Entry(self.changing, bg="black", fg="white",
                                       insertbackground="white")
        self.changing.entry.grid(row=1, column=4, sticky="news")
        self.changing.entry.bind("<Return>", self._rename)
        self.changing.entry.bind("<KP_Enter>", self._rename)
        self.changing.entry.insert(0, self.changing.item.purename)
        self.changing.entry.select_range(0, "end")
        self.changing.entry.icursor("end")
        self.changing.entry.focus_set()

    def maybe_cancel_rename(self, event:tk.Event) -> None:
        if not self.renaming:
            return None
        if event.widget != self.changing.entry:
            self.finish_rename()

    def _rename(self, _:tk.Event=None) -> None:
        assert self.renaming, "InternalError"
        new_name:str = self.changing.entry.get()
        if self.changing.item.rename(new_name):
            if self.creating:
                action:tuple[str,str] = ("create", "creation")
            else:
                action:tuple[str,str] = ("rename", "rename")
            type:str = "file" if isfile(self.changing.item) else "folder"
            msg:str = f"Couldn't {action[0]} {type}."
            title:str = f"{type.title()} {action[1]} failure"
            tell(self.changing, title=title, message=msg, icon="info",
                 center=True)
        else:
            self.changing.name.config(text=new_name)
            if isfile(self.changing.item):
                super().fix_icon(self.changing)
        self.finish_rename()

    def finish_rename(self, _:tk.Event=None) -> None:
        if not self.renaming:
            return None
        if self.changing.item.name == NEW_ITEM_NAME:
            super().delete_item(self.changing.item, apply_filesystem=False)
        self.changing.entry.destroy()
        self.changing:tk.Frame = None
        self.renaming:bool = False
        self.creating:bool = False
        super().update(soft=True)

    # Delete
    def delete(self) -> None:
        frame:tk.Frame = self.changing
        msg:str = f'Are you sure you want to delete "{frame.item.purename}"?'
        result:bool = askyesno(frame, title="Delete file?", message=msg,
                               icon="warning", center=True)
        if result:
            target:str = self.root.filesystem.join(self.bin_folder,
                                                   frame.item.purename)
            result = self.root.filesystem.move(frame.item.fullpath, target)
            if DEBUG: print("[DEBUG]: Delete result:", result)
        self.changing:tk.Frame = None
        super().update(soft=True)

    # New file/folder
    def newfile(self) -> None:
        parent:tk.Frame = super()._get_closest_folder(self.changing)
        newfile:File = parent.item.newfile()
        self._newitem(newfile, parent)

    def newfolder(self) -> None:
        parent:tk.Frame = super()._get_closest_folder(self.changing)
        newfolder:Folder = parent.item.newfolder()
        self._newitem(newfolder, parent)

    def _newitem(self, newitem:Item, parent:tk.Frame) -> None:
        super()._expand(parent)
        newframe:tk.Frame = super().create_frame(newitem)
        super().update(soft=True)
        self.selected = self.changing = newframe
        self.creating:bool = True
        self.rename()

    # Open in explorer
    def open_in_explorer(self) -> None:
        if OPEN_IN_EXPLORER is not None:
            path:str = self.selected.item.fullpath
            os.system(OPEN_IN_EXPLORER.format(path=path))
        self.changing:tk.Frame = None


if __name__ == "__main__":
    """
    root:tk.Tk = tk.Tk()
    menu:menu = Menu(root)
    menu.add("Copy", lambda: print("Copy"))
    menu.add("Paste", lambda: print("Paste"))
    menu.add_separator()
    menu.add("Save", lambda: print("Save"))
    menu.add("Save as", lambda: print("Save as"))
    menu.on_cancel:Function[None] = lambda: print("Cancelled")

    root.bind("<Button-3>", lambda e: menu.popup(root))
    raise SystemExit
    # """
    from bindframe import BindFrame
    import gridgiver
    import base_explorer
    import explorer
    #gridgiver.DEBUG = True
    #base_explorer.WARNINGS = True
    #base_explorer.DEBUG = True
    #base_explorer.TEST = True
    #explorer.DEBUG = True
    #explorer.HIGHLIGHT_UPDATES = True
    explorer.UPDATE_DELAY = 200000

    root = tk.Tk()
    root.geometry("320x180+0+0")
    root.config(bg="black")
    f = BindFrame(root, bg="black", bd=0, highlightthickness=0)
    f.pack(fill="both", expand=True)
    e = ExpandedExplorer(f)
    e.add("test/")
