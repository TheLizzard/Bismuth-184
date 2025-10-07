from __future__ import annotations
import tkinter as tk


NOT_DRAG_DIST:float = 30   # max pixels distance to not count as dragging
BUTTON1_TK_STATE:int = 256 # Taken from tkinter.Event.__repr__'s code
FRAME_KWARGS:dict = dict(highlightthickness=0, bd=0, bg="black")
DEBUG:bool = False


def allisinstance(iterable:Iterable, T:type) -> bool:
    return all(map(lambda elem: isinstance(elem, T), iterable))


class ExpGridFrame:
    __slots__ = "frame"

    def __init__(self, frame:tk.Misc) -> ExpGridFrame:
        assert isinstance(frame, tk.Frame|tk.Tk|tk.Toplevel), "TypeError"
        self.frame:tk.Misc = frame

    def grid_add(self, widget:tk.Misc, row:int, column:int, **kwargs) -> None:
        assert "in" not in kwargs, "The in_ argument is implied"
        assert "in_" not in kwargs, "The in_ argument is implied"
        widget.grid(row=row, column=column, **kwargs, in_=self.frame)


class GridGiver:
    __slots__ = "dragging", "b1pressed", "master", "selected", "sel_frame", \
                "tmp", "dragx", "dragy", "expgrid", \
                "select", "move_frame", "start_move", "cancel_move", \
                "right_click", "double_click"

    def __init__(self, master:tk.Misc) -> GridGiver:
        assert isinstance(master, tk.Misc), "TypeError"
        if master.__class__ == tk.Frame:
            print("[WARNING]: Mouse events might not be captured properly. " \
                  "Try using `file_explorer.bindframe.BindFrame` instead")
        self.expgrid:ExpGridFrame = ExpGridFrame(master)
        self.selected:list[tk.Frame] = [None]
        self.master:tk.Misc = master
        self.b1pressed:bool = False
        self.dragging:bool = False
        master.bind("<Motion>", self._mouse_moved, add=True)
        master.bind("<B1-Motion>", self._mouse_moved, add=True)
        master.bind("<ButtonPress-1>", self._mouse_pressed, add=True)
        master.bind_all("<<CancelAll>>", self._mouse_pressed, add=True)
        master.bind("<ButtonRelease-1>", self._mouse_released, add=True)
        master.bind("<<FocusOutExplorer>>", lambda e: self._select(None), add=True)
        master.bind("<Double-Button-1>", self._double_click, add=True)
        master.bind("<Button-3>", self._right_click, add=True)

        self.select:Function[tk.Frame|None,tk.Frame|None] = lambda frame: None
        self.start_move:Function[tk.Frame,list[tk.Frame]] = lambda f: [f]
        self.move_frame:Function[tk.Frame,tk.Frame|None,None] = lambda src,dis: None
        self.cancel_move:Function[None] = lambda: None
        self.right_click:Function[tk.Frame|None,str] = lambda frame: None
        self.double_click:Function[tk.Frame|None,str] = lambda frame: None

    # Helpers
    def _get_true_frame(self, widget:tk.Misc) -> tk.Frame|None:
        while True:
            if widget.master is None:
                return None
            if widget.master == self.master:
                return widget
            widget:tk.Misc = widget.master

    def _get_true_event(self, event:tk.Event) -> tk.Event:
        true_frame = self._get_true_frame(event.widget)
        event.widget:tk.Frame = true_frame
        if true_frame is None:
            event.x = event.y = None
        else:
            event.x:int = event.x_root - true_frame.winfo_rootx()
            event.y:int = event.y_root - true_frame.winfo_rooty()
        return event

    def get_selected(self) -> tk.Frame:
        return self.selected[0]

    # Calls before calling bindings
    def _select(self, frame:tk.Frame|None) -> None:
        if self.get_selected() == frame:
            return None
        if DEBUG: print(f"[DEBUG]: Select {frame}")
        self.select(self.get_selected(), frame)   # Don't move this line down
        self.selected:list[tk.Frame] = [frame]

    def _right_click(self, event:tk.Event) -> str:
        return self.right_click(self._get_true_frame(event.widget))

    def _double_click(self, event:tk.Event) -> str:
        return self.double_click(self._get_true_frame(event.widget))

    # Frame dragging code
    def _mouse_pressed(self, event:tk.Event) -> None:
        self.b1pressed:bool = True
        event:tk.Event = self._get_true_event(event)
        # It's possible for event.x to be None??? Why???
        self.dragx, self.dragy = (event.x or 0), (event.y or 0)
        self._select(event.widget)

    def _start_dragging(self, event:tk.Event) -> None:
        width:int = self.master.winfo_width()
        self.tmp:tk.Frame = tk.Frame(self.master, **FRAME_KWARGS)
        self.sel_frame:tk.Frame = tk.Frame(self.master, **FRAME_KWARGS)
        sel_frame_exp:ExpGridFrame = ExpGridFrame(self.sel_frame)
        height:int = 0
        min_row:int = min(map(lambda x: x.row, self.selected))
        for sel in self.selected:
            sel.lift() # sel must be above all other siblings
            height += sel.winfo_height()
            row:int = sel.row - min_row
            sel_frame_exp.grid_add(sel, row=row, column=1, sticky="news")
        self.sel_frame.config(width=width, height=height)
        self.sel_frame.grid_columnconfigure(1, weight=1)
        self.sel_frame.grid_propagate(False)
        self.tmp.config(width=width, height=height)
        self.expgrid.grid_add(self.tmp, row=self.get_selected().row, column=1,
                              sticky="news")

    def _mouse_moved(self, event:tk.Event) -> None:
        if not self.b1pressed:
            return None
        # Mouse released outside of the window
        if not (event.state & BUTTON1_TK_STATE):
            self._mouse_released(event, cancelled=True)
            return None
        event:tk.Event = self._get_true_event(event)

        if not self.dragging:
            if event.widget is None:
                return None
            dist:int = (event.x-self.dragx)**2 + (event.y-self.dragy)**2
            if dist < NOT_DRAG_DIST:
                return None
            selected:tuple[tk.Frame] = self.start_move(self.get_selected())
            assert isinstance(selected, tuple|list), "TypeError"
            assert allisinstance(selected, tk.Frame), "TypeError"
            if len(selected) == 0: return None
            assert selected[0] == self.get_selected(), "ValueError"
            self.selected:list[tk.Frame] = selected
            self.dragging:bool = True
            self._start_dragging(event)

        # If we are already dragging (or we are starting to drag):
        x:int = event.x_root - self.master.winfo_rootx()
        y:int = event.y_root - self.master.winfo_rooty()
        self.sel_frame.place(x=x-self.dragx, y=y-self.dragy)

    def _mouse_released(self, event:tk.Event, *, cancelled:bool=False) -> None:
        self.b1pressed:bool = False # Don't move this line down!
        if not self.dragging:
            return None
        self.dragging:bool = False
        for i, sel in enumerate(self.selected):
            self.expgrid.grid_add(sel, row=sel.row, column=1, sticky="news")
        self.sel_frame.destroy()
        self.tmp.destroy()
        self.selected:list[tk.Frame] = self.selected[:1]
        if cancelled:
            if DEBUG: print(f"[DEBUG]: Cancel move")
            self.cancel_move()
        else:
            # This works using magic, don't touch
            x, y = self.get_selected().winfo_pointerxy()
            distination:tk.Frame = self.master.winfo_containing(x, y)
            distination:tk.Frame = self._get_true_frame(distination)
            if distination is None:
                if DEBUG: print(f"[DEBUG]: Cancel move")
                self.cancel_move()
            else:
                if DEBUG: print(f"[DEBUG]: Move {distination.item=}")
                self.move_frame(self.get_selected(), distination)

    # Add/remove frame
    def add_frame(self, frame:tk.Frame, row:int) -> None:
        assert isinstance(frame, tk.Frame), "TypeError"
        assert isinstance(row, int), "TypeError"
        assert not self.dragging, "RuntimeError"
        self.expgrid.grid_add(frame, row=row, column=1, sticky="news")
        frame.row:int = row
        if DEBUG: print(f"[DEBUG]: Added frame {frame} to row {row}")

    def remove_frame(self, frame:tk.Frame, grid_forget:bool=True) -> None:
        assert not self.dragging, "RuntimeError"
        assert len(self.selected) == 1, "SanityCheck"
        assert isinstance(frame, tk.Frame), "TypeError"
        if DEBUG: print(f"[DEBUG]: Removed frame {frame} from row {frame.row}")
        frame.row:int = None
        if grid_forget:
            frame.grid_forget()
        if frame == self.get_selected():
            self._select(None)


if __name__ == "__main__":
    def select(old:tk.Frame, new:tk.Frame) -> None:
        print("Selected:", new.cget("bg"))
    def move_frame(src:tk.Frame, dis:tk.Frame) -> None:
        print(f'Move: {src.cget("bg")} => {dis.cget("bg")}')
    def start_move(frame:tk.Frame) -> tuple[tk.Frame]:
        if frame == f1:
            return f1, f2
        return [frame]

    frame_kwargs = dict(width=100, highlightthickness=0, bd=0)
    root = tk.Tk()
    ggiver = GridGiver(root)
    ggiver.select = select
    ggiver.move_frame = move_frame
    ggiver.start_move = start_move
    f1 = tk.Frame(root, height=50, bg="red", **frame_kwargs)
    f2 = tk.Frame(root, height=50, bg="green", **frame_kwargs)
    f3 = tk.Frame(root, height=50, bg="blue", **frame_kwargs)
    ggiver.add_frame(f1, 1)
    ggiver.add_frame(f2, 2)
    ggiver.add_frame(f3, 3)