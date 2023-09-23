from __future__ import annotations
from time import perf_counter
import tkinter as tk
import os

try:
    from .base_explorer import Item, Root, isfile, isfolder, FileSystem
    from .idxgiver import IdxGiver, Idx
    from .gridgiver import GridGiver
    from . import images
except ImportError:
    from base_explorer import Item, Root, isfile, isfolder, FileSystem
    from idxgiver import IdxGiver, Idx
    from gridgiver import GridGiver
    import images

def iter_skip(iterator:Iterator[T], *, n:int) -> Iterator[T]:
    for i in range(n):
        next(iterator)
    yield from iterator

def generator_len(iterator:Iterator[T]) -> int:
    return sum(1 for element in iterator)

def create_circle(self, x:int, y:int, r:int, **kwargs):
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
tk.Canvas.create_circle = create_circle


INDENTATION:int = 15
PADX:int = 10
PADY:int = 5
DEBUG:bool = False
UPDATE_DELAY:int = 2000
HIGHLIGHT_UPDATES:bool = False
COLLAPSE_BEFORE_MOVE:bool = True
REDRAW_HIGHLIGHT_DELAY:int = 1000
SELECTED_COLOUR:str = "dark orange"

AUTO_UPDATE:bool = True

PATH:str = os.path.abspath(os.path.dirname(__file__))


class Explorer:
    __slots__ = "master", "changing", "ggiver", "root", "item_to_frame", \
                "expanded_before"

    def __init__(self, master:tk.Misc) -> Explorer:
        self.changing:tk.Frame = None
        self.master:tk.Misc = master
        master.grid_columnconfigure(1, weight=1)
        self.root:Root = Root(FileSystem(), autoexpand=False)
        self.item_to_frame:dict[Item:tk.Frame] = dict()
        self.ggiver:GridGiver = GridGiver(self.master)
        self.ggiver.select:Function[tk.Frame,tk.Frame] = self._selected
        self.ggiver.move_frame:Function[tk.Frame,tk.Frame,None] = self.move
        self.ggiver.start_move:Function[tk.Frame,list[tk.Frame]] = self.start_move
        self.ggiver.cancel_move:Function[None] = self.cancel_move
        self.ggiver.double_click:Function[tk.Frame,str] = self.double_click

        images.init(self.master)
        self.update_loop()

    # Helpers
    def _get_closest_folder(self, frame:tk.Frame) -> tk.Frame:
        if isfile(frame.item):
            item:Folder = frame.item.master
            assert isfolder(item), "SanityCheck"
            return self.item_to_frame[item]
        elif isfolder(frame.item):
            return frame
        raise NotImplementedError(f"What is {frame.item}?")

    def _get_sprite(self, extension:str) -> ImageTk.PhotoImage:
        if extension in images.EXTENSIONS:
            return images.TK_IMAGES[extension]
        else:
            return images.TK_IMAGES["*"]

    def _get_shown_children(self, frame:tk.Frame, *, withself:bool):
        iterator = frame.item.recurse_children(withself=withself,
                                               only_shown=True)
        if DEBUG:
            for item, shown in iterator:
                assert shown, "SanityCheck"
                yield self.item_to_frame[item]
        else:
            yield from map(lambda x: self.item_to_frame[x[0]], iterator)

    def fix_indentation(self, frame:tk.Frame) -> None:
        if frame.indent == frame.item.indentation:
            return None
        frame.indent:int = frame.item.indentation
        frame.indentation.config(width=(frame.indent-1)*INDENTATION + PADX)

    @property
    def selected(self) -> tk.Frame:
        return self.ggiver.get_selected()

    @selected.setter
    def selected(self, frame:tk.Frame) -> None:
        assert isinstance(frame, tk.Frame), "TypeError"
        self.ggiver._select(frame)
        self.master.event_generate("<<Explorer-Selected>>", data=(frame,))

    def get_selected(self) -> tk.Frame:
        return self.selected

    def fix_icon(self, frame:tk.Frame) -> None:
        image:tk.PhotoImage = self._get_sprite(frame.item.extension)
        frame.icon.itemconfig(frame.icon.id, image=image)

    def recolour_frame(self, frame:tk.Frame, bg:str) -> None:
        if frame is None:
            return None
        frame.config(bg=bg)
        frame.indentation.config(bg=bg)
        frame.name.config(bg=bg)
        if isfile(frame.item):
            frame.icon.config(bg=bg)
        else:
            frame.expandeder.config(bg=bg)

    # Update/loop
    def update_loop(self) -> None:
        if (self.changing is None) and AUTO_UPDATE:
            self.update(soft=False)
        elif AUTO_UPDATE and DEBUG:
            print(f"[DEBUG]: Skipping update")
        self.master.after(UPDATE_DELAY, self.update_loop)

    def update(self, *, soft:bool=False):
        if DEBUG:
            start:float = perf_counter()
            print("[DEBUG]: Updating")
        if not soft:
            self.root.update() # Don't remove (root is BaseExplorer)
            self._update_remove_dead()
        for item, show in self.root.recurse_children(withself=False):
            assert not item.idx.deleted, "SanityCheck"
            # create_frame must check if the frame already exists
            frame:tk.Frame = self.create_frame(item)
            if show and (item.idx.dirty or (not frame.shown)):
                self._update_show(frame)
            if (not show) and frame.shown:
                self._update_hide(frame)
        if DEBUG:
            print(f"[DEBUG]: Updated in {perf_counter()-start} seconds")

    def _update_remove_dead(self) -> None:
        for item in tuple(self.item_to_frame):
            if item.idx.deleted:
                self.delete_item(item, apply_filesystem=False)

    def _update_show(self, frame:tk.Frame) -> None:
        frame.shown:bool = True
        self.fix_indentation(frame)
        frame.item.idx.dirty:bool = False
        self.ggiver.add_frame(frame, frame.item.idx.value)
        if DEBUG:
            print(f"[DEBUG]: {frame.item} moved to to={frame.item.idx}")
        if HIGHLIGHT_UPDATES:
            frame.after(REDRAW_HIGHLIGHT_DELAY, self.recolour_frame, frame, frame.cget("bg"))
            self.recolour_frame(frame, "red")

    def _update_hide(self, frame:tk.Frame) -> None:
        if DEBUG: print(f"[DEBUG]: Hiding: {frame.item}")
        self.ggiver.remove_frame(frame)
        frame.shown:bool = False

    def delete_item(self, item:Item, *, apply_filesystem:bool=True) -> None:
        frame:tk.Frame = self.item_to_frame.pop(item)
        if not item.idx.deleted: # Check item still in tree
            frame.item.delete(apply_filesystem=apply_filesystem)
        self.ggiver.remove_frame(frame, grid_forget=False)
        frame.destroy()

    # Create frame
    def create_frame(self, item:Item) -> tk.Frame:
        frame:tk.Frame = self.item_to_frame.get(item, None)
        if frame is not None:
            return frame
        if DEBUG: print(f"[DEBUG]: Creating frame for {item}")
        frame = tk.Frame(self.master, bg="black", highlightthickness=0, bd=0)
        self.item_to_frame[item] = frame
        frame.shown:bool = False
        frame.item:Item = item

        indentation = tk.Canvas(frame, width=1, bd=0, bg="black",
                                height=1, highlightthickness=0)
        indentation.grid(row=1, column=1, sticky="ns")
        frame.indentation = indentation
        frame.indent:int = None
        self.fix_indentation(frame)

        if isfile(item):
            tk_icon = self._get_sprite(item.extension)
            icon = tk.Canvas(frame, bg="black", bd=0, highlightthickness=0,
                             width=tk_icon.width(), height=tk_icon.height())
            icon.id:int = icon.create_image(0, 0, anchor="nw", image=tk_icon)
            icon.grid(row=1, column=2)
            frame.icon = icon
        elif isfolder(item):
            if item.expanded:
                text = "-"
            else:
                text = "+"
            expandeder = tk.Label(frame, text=text, bg="black", fg="white",
                                  font=("DejaVu Sans Mono", 9))
            expandeder.grid(row=1, column=2, sticky="news")
            frame.expandeder = expandeder
        else:
            raise NotImplementedError(f"Don't have a clue to what {item} is")

        name = tk.Label(frame, text=item.purename, bg="black", fg="white",
                        anchor="w")
        name.grid(row=1, column=4, sticky="news")
        frame.name = name
        return frame

    # Event handlers
    def _selected(self, old:tk.Frame, new:tk.Frame) -> None:
        self.recolour_frame(old, "black")
        self.recolour_frame(new, SELECTED_COLOUR)

    def start_move(self, frame:tk.Frame) -> list[tk.Frame]:
        if frame.item.indentation == 1:
            return []
        if self.changing is not None:
            return []
        self.changing:tk.Frame = frame
        if COLLAPSE_BEFORE_MOVE:
            if isfolder(frame.item):
                self.expanded_before:bool = frame.item.expanded
                self._collapse(frame)
            else:
                self.expanded_before:bool = False
            return [frame]
        else:
            children = list(self._get_shown_children(frame, withself=True))
            return children

    def cancel_move(self) -> None:
        if isfolder(self.changing.item) and self.expanded_before:
            self._expand(self.changing)
        self.changing:tk.Frame = None

    def move(self, src:tk.Frame, dis:tk.Frame) -> None:
        dis:tk.Frame = self._get_closest_folder(dis)
        self.changing:tk.Frame = None
        src.item.move(dis.item)
        if isfolder(src.item) and self.expanded_before:
            self._expand(src)
        if isfolder(dis.item):
            self._expand(dis)
        self.update(soft=True)

    def double_click(self, frame:tk.Frame|None) -> str:
        if frame is None:
            return None
        if isfolder(frame.item):
            return self._toggle_expand(frame)
        else:
            self.master.event_generate("<<Explorer-Open>>", data=(frame.item,))

    def _toggle_expand(self, frame:tk.Frame) -> str:
        assert isfolder(frame.item), "TypeError"
        if frame.item.expanded:
            self._collapse(frame)
        else:
            self._expand(frame)

    def _expand(self, frame:tk.Frame) -> None:
        if frame.item.expanded:
            return None
        if DEBUG: print(f"[DEBUG]: Expanding {frame.item}")
        frame.item.expanded:bool = True
        frame.expandeder.config(text="-")
        self.update(soft=True)

    def _collapse(self, frame:tk.Frame) -> None:
        if not frame.item.expanded:
            return None
        frame.item.expanded:bool = False
        frame.expandeder.config(text="+")
        self.update(soft=True)

    def expand(self, item:Item) -> None:
        assert isfolder(item), "TypeError"
        self._expand(self.item_to_frame[item])

    # Functions you can call:
    def add(self, path:str) -> None:
        folder:Folder = self.root.add(path)
        if folder is not None:
            folder.update()
            self.update(soft=True)

    def remove(self, path:str) -> None:
        self.root.remove(path)
        self.update(soft=True)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("320x130+0+0")
    root.config(bg="black")
    root.grid_columnconfigure(1, weight=1)
    e = Explorer(root)
    e.add("test/")
