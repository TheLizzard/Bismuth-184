from time import perf_counter
import tkinter as tk

import images
import base_explorer


INDENTATION = 25
PADX = 5
PADY = 5


class Explorer(tk.Frame):
    def __init__(self, master, bg:str="black", fg:str="white",
                 selected_bg:str="blue", selected_fg:str=None, **kwargs):
        self.bg = bg
        self.fg = fg
        self.selected_bg = selected_bg
        self.selected_fg = selected_fg
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, **kwargs)
        super().grid_propagate(False)
        self.tree = base_explorer.BaseExplorer()

        self.shown_items = []
        self.item_to_idx = {}
        self.last_taken_row = -1
        self.selected = None # The currently selected `tk.Frame`
        self.mouse_down = False
        self.temp_holder = None
        self.dragging_file = False
        self.last_opened = perf_counter()

        self.set_up()
        super().bind_all("<Motion>", self.mouse_moved)
        super().bind_all("<ButtonPress-1>", self.mouse_pressed)
        super().bind_all("<ButtonRelease-1>", self.mouse_released)
        super().grid_columnconfigure(0, weight=1)

    def mouse_pressed(self, event:tk.Event) -> None:
        frame = self.get_frame_from_event(event)
        if frame == self:
            return None
        idx = self.item_to_idx[frame.item]
        self.temp_holder = tk.Frame(self, bg=self.bg, highlightthickness=0,
                                    bd=0, width=frame.winfo_width(),
                                    height=frame.winfo_height())
        self.temp_holder.grid(row=idx, column=0)
        frame.lift()

        self.mouse_down = True
        self.offset_x = super().winfo_pointerx() - frame.winfo_x()
        self.offset_y = super().winfo_pointery() - frame.winfo_y()

    def mouse_moved(self, event:tk.Event) -> None:
        if self.mouse_down and (self.selected is not None):
            self.dragging_file = True
            x = super().winfo_pointerx() - self.offset_x
            y = super().winfo_pointery() - self.offset_y
            self.selected.place(x=x, y=y, width=self.winfo_width())

    def mouse_released(self, event:tk.Event) -> None:
        if self.mouse_down:
            self.mouse_down = False
            if self.dragging_file:
                target = self.get_frame_from_mouse(without=self.selected)
                self.frame_moved(self.selected, target)
            self.dragging_file = False
            self.temp_holder.destroy()
            self.temp_holder = None

    def get_frame_from_mouse(self, without:tk.Frame=None) -> tk.Frame:
        y = super().winfo_pointery() - self.offset_y + \
            self.selected.winfo_height() // 2
        for target in self.shown_items:
            if (target != without) and self.y_in_frame(y, target):
                return target
        if (self.temp_holder is not None) and (self.temp_holder != without):
            if self.y_in_frame(y, self.temp_holder):
                return self.temp_holder

    def get_frame_from_immediate_mouse(self) -> tk.Frame:
        y = super().winfo_pointery() - super().winfo_rooty()
        for target in self.shown_items:
            if self.y_in_frame(y, target):
                return target

    def frame_moved(self, frame:tk.Frame, target_frame:tk.Frame) -> None:
        item = frame.item
        if target_frame == self.temp_holder:
            frame.grid(row=self.item_to_idx[item], column=0, sticky="ew")
            return None
        if target_frame is None:
            # If we put the item at the bottom
            target = self.tree.children[-1]
            target_frame = self.shown_items[self.item_to_idx[target]]
        else:
            # Get the target
            target = target_frame.item
            if target.isfile:
                target = target.master
            target_frame = self.shown_items[self.item_to_idx[target]]
        # Make sure we aren't moving the item to the same location:
        if item.master == target:
            frame.grid(row=self.item_to_idx[item], column=0, sticky="ew")
            return None
        # Make sure we aren't moving the item to a child
        targets_master = target
        while targets_master is not None:
            if targets_master == item:
                frame.grid(row=self.item_to_idx[item], column=0, sticky="ew")
                return None
            targets_master = targets_master.master
        # Move the item
        item.move_to(target)
        self._frame_moved(frame)

    def _frame_moved(self, frame:tk.Frame) -> None:
        new_idx, _ = self.slow_item_to_idx(frame.item)
        to_add = []
        to_move = [frame.item]
        while len(to_move) > 0:
            item = to_move.pop(0)
            if not item.isfile:
                to_move = item.children.copy() + to_move
            frame = self.slow_item_to_frame(item)
            self.shown_items.remove(frame)
            to_add.append(frame)
        for frame in to_add:
            self.shown_items.insert(new_idx, frame)
            frame.indentation.config(width=self.get_indentation(frame.item))
            new_idx += 1
        self.fix_item_to_idx()

    def slow_item_to_idx(self, item, tree=None) -> (int, bool):
        if tree is None:
            tree = self.tree
        idx = 0
        for child in tree:
            if child == item:
                return idx, True
            idx += 1
            if not child.isfile:
                sub_idx, found = self.slow_item_to_idx(item, child)
                idx += sub_idx
                if found:
                    return idx, True
        return idx, False

    def slow_item_to_frame(self, item) -> tk.Frame:
        for frame in self.shown_items:
            if frame.item == item:
                return frame
        raise ValueError(f"Can't find the frame for that item: {item}")

    def get_frame_from_event(self, event:tk.Event) -> tk.Frame:
        widget = event.widget
        if isinstance(widget, tk.Label):
            return widget.master
        return widget

    def y_in_frame(self, y:int, frame:tk.Frame) -> bool:
        if len(frame.grid_info()) == 0:
            return False
        frame_y = frame.winfo_y()
        return frame_y < y < frame_y + frame.winfo_height()

    def set_up(self) -> None:
        self.images = {}
        for extension in ("txt", "cpp", "file", "py"):
            image = tk.PhotoImage(file=f"images/.{extension}.png", master=self)
            self.images.update({extension: image})

    def add(self, folder:str) -> None:
        self.tree.add(folder)
        self.display(self.tree)

    def remove(self, folder:str) -> None:
        self.tree.remove(folder)

    def clean_up(self) -> None:
        for item in self.item_to_idx.copy():
            if item.garbage_collect:
                self.delete(item)

    def delete(self, item) -> None:
        idx = self.item_to_idx[item]
        if not item.isfile:
            for child in item.children:
                self.delete(child)
        del self.item_to_idx[item]
        self.shown_items[idx].destroy()
        del self.shown_items[idx]
        self.last_taken_row -= 1
        self.fix_item_to_idx()

    def fix_item_to_idx(self) -> None:
        self.item_to_idx.clear()
        to_hide = []
        for idx, frame in enumerate(self.shown_items):
            self.item_to_idx.update({frame.item: idx})
            call_grid_forget = len(frame.grid_info()) == 0
            placed = len(frame.place_info()) != 0
            frame.grid(row=idx, column=0, sticky="ew")
            if placed:
                master = self.shown_items[self.item_to_idx[frame.item.master]]
                call_grid_forget = len(master.grid_info()) == 0
                call_grid_forget |= not frame.item.master.expanded
            if call_grid_forget:
                to_hide.append(frame)
        while len(to_hide) > 0:
            frame = to_hide.pop(0)
            if not frame.item.isfile:
                for child_item in frame.item.children:
                    child = self.shown_items[self.item_to_idx[child_item]]
                    to_hide.append(child)
            self.call_grid_forget(frame)

    def change_colour(self, frame:tk.Frame, bg:str=None, fg:str=None) -> None:
        to_change = [frame]
        while len(to_change) != 0:
            widget = to_change.pop(0)
            if isinstance(widget, tk.Frame):
                to_change.extend(widget.winfo_children())
            elif isinstance(widget, tk.Label):
                widget.config(fg=fg)
            widget.config(bg=bg)

    def display(self, tree:base_explorer.Folder, idx:int=None) -> int:
        items_draw = 0
        for item in tree:
            self.show(item, idx)
            if (not item.isfile) and item.expanded:
                items_draw += self.display(item, idx)
            items_draw += 1
        return items_draw
    draw = display

    def show(self, item, idx:int=None) -> None:
        if item in self.item_to_idx:
            # Already shown
            return None

        self.last_taken_row += 1
        frame = tk.Frame(self, bg=self.bg, highlightthickness=0, bd=0)
        if idx is None:
            row = self.last_taken_row
        else:
            row = idx
        frame.grid(row=row, column=0, sticky="ew")

        indentation = tk.Frame(frame, width=self.get_indentation(item),
                               bg=self.bg)
        indentation.pack(side="left")

        if item.isfile:
            tk_icon = self.images[item.extension]
            icon = tk.Canvas(frame, bg=self.bg, bd=0, highlightthickness=0,
                             width=tk_icon.width(), height=tk_icon.height())
            icon.create_image(0, 0, anchor="nw", image=tk_icon)
            icon.pack(side="left")
            frame.icon = icon
        else:
            if item.expanded:
                text = "-"
            else:
                text = "+"
            expandeder = tk.Label(frame, text=text, bg=self.bg, fg=self.fg,
                                  font=("DejaVu Sans Mono", 9))
            expandeder.pack(side="left")
            frame.expandeder = expandeder

        name = tk.Label(frame, text=item.name, bg=self.bg, fg=self.fg,
                        anchor="w")
        name.pack(side="left")

        frame.item = item
        frame.name = name
        frame.indentation = indentation

        frame.bind_all("<ButtonPress-1>", self.user_selected, add=True)
        frame.bind_all("<Double-Button-1>", self.user_opened, add=True)

        self.shown_items.insert(row, frame)
        self.item_to_idx.update({item: row})

    def get_indentation(self, item) -> int:
        return item.indentation*INDENTATION + PADX

    def user_selected(self, event:tk.Event) -> str:
        frame = self.get_frame_from_event(event)
        if frame not in self.shown_items:
            self._select(None)
            return "break"
        item = frame.item
        if item.isfile:
            if self.selected == frame:
                return None
            frame.event_generate("<<SelectedFile>>", when="tail")
        else:
            if frame.expandeder == event.widget:
                return self.user_opened(event)
            if self.selected == frame:
                return None
            frame.event_generate("<<SelectedFolder>>", when="tail")
        self._select(frame)
        return "break"

    def _select(self, frame:tk.Frame) -> None:
        if self.selected is not None:
            explorer.change_colour(bg=self.bg, frame=self.selected,
                                   fg=self.fg)
        self.selected = frame
        if self.selected is not None:
            explorer.change_colour(bg=self.selected_bg, frame=frame,
                                   fg=self.selected_fg)

    def user_opened(self, event:tk.Event) -> str:
        if perf_counter() - self.last_opened < 0.1:
            return "break"
        self.last_opened = perf_counter()
        frame = self.get_frame_from_event(event)
        item = frame.item
        if item.isfile:
            frame.event_generate("<<OpenedFile>>", when="tail")
        else:
            if item.expanded:
                self.collapse_folder(item)
            else:
                self.expand_folder(item)
        return "break"

    def collapse_folder(self, item:base_explorer.Folder, draw:bool=True):
        for child in item.children:
            frame = self.shown_items[self.item_to_idx[child]]
            self.call_grid_forget(frame)
            if not child.isfile:
                self.collapse_folder(child, False)
        if draw:
            frame = self.shown_items[self.item_to_idx[item]]
            frame.expandeder.config(text="+")
            item.expanded = False
            # self.draw(item)

    def expand_folder(self, item:base_explorer.Folder, draw:bool=True) -> None:
        for child in item.children:
            idx = self.item_to_idx[child]
            frame = self.shown_items[idx]
            frame.grid(row=idx, column=0, sticky="ew")
            if (not child.isfile) and child.expanded:
                self.expand_folder(child, False)
        if draw:
            idx = self.item_to_idx[item]
            frame = self.shown_items[idx]
            frame.expandeder.config(text="-")
            item.expanded = True
            # self.draw(item)

    def call_grid_forget(self, frame:tk.Frame) -> None:
        if frame == self.selected:
            self._select(None)
        frame.grid_forget()


def test_delete_file_1():
    global root, explorer
    root = tk.Tk()
    root.title("Test 1")

    explorer = Explorer(root, width=180, height=240)
    explorer.pack(fill="both", expand=True)
    explorer.add(".")

    explorer.tree.children[0].children[1].garbage_collect = True
    del explorer.tree.children[0].children[1]
    explorer.clean_up()

    explorer.draw(explorer.tree)

    assert explorer.last_taken_row == 8
    assert str([i.item for i in explorer.shown_items]) == "[Folder(try2), Folder(images), File(.cpp.png), File(.file.png), File(.folder.png), File(.py.png), File(.txt.png), File(explorer.py), File(images.py)]"
    assert str([(i, j) for i, j in explorer.item_to_idx.items()]) == "[(Folder(try2), 0), (Folder(images), 1), (File(.cpp.png), 2), (File(.file.png), 3), (File(.folder.png), 4), (File(.py.png), 5), (File(.txt.png), 6), (File(explorer.py), 7), (File(images.py), 8)]"

    root.after(100, root.destroy)
    root.mainloop()

def test_delete_file_2():
    global root, explorer
    root = tk.Tk()
    root.title("Test 1")

    explorer = Explorer(root, width=180, height=240)
    explorer.pack(fill="both", expand=True)
    explorer.add(".")

    explorer.tree.children[0].children[0].garbage_collect = True
    del explorer.tree.children[0].children[0]
    explorer.clean_up()

    explorer.draw(explorer.tree)

    assert explorer.last_taken_row == 3
    assert str([i.item for i in explorer.shown_items]) == "[Folder(try2), File(base_explorer.py), File(explorer.py), File(images.py)]"
    assert str([(i, j) for i, j in explorer.item_to_idx.items()]) == "[(Folder(try2), 0), (File(base_explorer.py), 1), (File(explorer.py), 2), (File(images.py), 3)]"

    root.after(100, root.destroy)
    root.mainloop()

def test_move_file_1():
    global root, explorer

    def check_test():
        correct_tree = """
- try2
    - images
        .cpp.png
        .file.png
        .folder.png
        .txt.png
    base_explorer.py
    explorer.py
    images.py
    .py.png
"""[1:-1]
        assert explorer.tree.to_string() == correct_tree
        assert explorer.last_taken_row == 9
        assert str([i.item for i in explorer.shown_items]) == "[Folder(try2), Folder(images), File(.cpp.png), File(.file.png), File(.folder.png), File(.txt.png), File(base_explorer.py), File(explorer.py), File(images.py), File(.py.png)]"
        assert str([(i, j) for i, j in explorer.item_to_idx.items()]) == "[(Folder(try2), 0), (Folder(images), 1), (File(.cpp.png), 2), (File(.file.png), 3), (File(.folder.png), 4), (File(.txt.png), 5), (File(base_explorer.py), 6), (File(explorer.py), 7), (File(images.py), 8), (File(.py.png), 9)]"
        root.destroy()

    def test():
        explorer.temp_holder = tk.Frame()
        explorer.selected = explorer.shown_items[5]
        explorer.dragging_file = True
        explorer.offset_y = 0
        explorer.event_generate("<Motion>", warp=True, x=100, y=162)
        explorer.mouse_released("Event")

        root.after(100, check_test)

    root = tk.Tk()

    explorer = Explorer(root, width=180, height=240)
    explorer.pack(fill="both", expand=True)
    explorer.add(".")

    root.after(100, test)

    root.bind("a", lambda e: print("="*80+"\n"+explorer.tree.to_string()+"\n"+"="*80))
    root.mainloop()

if __name__ == "__main__":
    from sys import stderr
    try:
        test_delete_file_1()
        test_delete_file_2()
        test_move_file_1()
    except:
        root.destroy()
        stderr.write("Tests failed\n")

    def selected_file(event):
        print("[Debug]: Selected", event.widget.item)

    def opened_file(event):
        print("[Debug]: Opened", event.widget.item)

    root = tk.Tk()

    explorer = Explorer(root, width=180, height=240)
    explorer.pack(fill="both", expand=True)
    explorer.add(".")

    explorer.bind_all("<<OpenedFile>>", opened_file)
    explorer.bind_all("<<SelectedFile>>", selected_file)

    # root.mainloop()
    root.bind("a", lambda e: print("="*80+"\n"+explorer.tree.to_string()+"\n"+"="*80))
