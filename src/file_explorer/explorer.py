import tkinter as tk

try:
    from . import images
    from . import base_explorer
except ImportError:
    import images
    import base_explorer


INDENTATION = 25
PADX = 5
PADY = 5 # Not honoured


class Explorer:
    def __init__(self, master, fg:str="white", selected_bg:str="blue",
                 bg:str="black", selected_fg:str=None):
        self.bg = bg
        self.fg = fg
        self.selected_bg = selected_bg
        self.selected_fg = selected_fg
        self.master = master
        self.master.grid_propagate(False)
        self.tree = base_explorer.BaseExplorer()

        self.shown_items = []
        self.selected = None # The currently selected `tk.Frame`
        self.renaming = False # Set by classes inhetiting from us
        self.temp_holder = None
        self.dragging_file = False

        # Make sure we get the correct y value for scrollable frames:
        self.framey = lambda y: y
        if hasattr(self.master, "framey"):
            self.framey = self.master.framey

        self.set_up_images()
        self.bind_frame(self.master, "<B1-Motion>", self.mouse_moved)
        self.bind_frame(self.master, "<ButtonPress-1>", self.mouse_pressed)
        self.bind_frame(self.master, "<ButtonRelease-1>", self.mouse_released)
        self.master.bind("<FocusOut>", lambda e: self.select(None))
        self.master.grid_columnconfigure(0, weight=1)

    def mouse_pressed(self, event:tk.Event) -> None:
        frame = self.get_frame_from_event(event)
        if (frame == self.master) or self.renaming:
            return None
        self.master.focus_set()
        self.temp_holder = tk.Frame(self.master, highlightthickness=0,
                                    height=frame.winfo_height(), bd=0,
                                    width=frame.winfo_width(), bg=self.bg)
        self.temp_holder.grid(row=frame.item.idx, column=0)
        frame.lift()

        self.offset_x = self.master.winfo_pointerx() - frame.winfo_x()
        self.offset_y = self.framey(self.master.winfo_pointery()) - frame.winfo_y()

    def mouse_moved(self, event:tk.Event) -> None:
        if (not self.renaming) and (self.selected is not None):
            self.dragging_file = True
            x = self.master.winfo_pointerx() - self.offset_x
            y = self.framey(self.master.winfo_pointery()) - self.offset_y
            self.selected.frame.place(width=self.master.winfo_width(), x=x, y=y)

    def mouse_released(self, event:tk.Event) -> None:
        if self.renaming:
            return None
        if self.dragging_file:
            target = self.get_frame_from_mouse(without=self.selected.frame)
            self.frame_moved(self.selected.frame, target)
        self.dragging_file = False
        if self.temp_holder is not None:
            self.temp_holder.destroy()
            self.temp_holder = None

    def get_frame_from_mouse(self, without:tk.Frame=None) -> tk.Frame:
        y = self.framey(self.master.winfo_pointery()) - self.offset_y + \
            self.selected.frame.winfo_height() // 2
        for target in self.shown_items:
            if (target.frame != without) and self.y_in_frame(y, target.frame):
                return target.frame
        if (self.temp_holder is not None) and (self.temp_holder != without):
            if self.y_in_frame(y, self.temp_holder):
                return self.temp_holder

    def get_frame_from_immediate_mouse(self) -> tk.Frame:
        y = self.framey(self.master.winfo_pointery()) - \
            self.master.winfo_rooty()
        for target in self.shown_items:
            if self.y_in_frame(y, target.frame):
                return target.frame

    def frame_moved(self, frame:tk.Frame, target_frame:tk.Frame) -> None:
        item = frame.item
        # If we didn't move the item
        if target_frame == self.temp_holder:
            frame.grid(row=item.idx, column=0, sticky="ew")
            return None
        # If we put the item at the bottom
        if target_frame is None:
            target = self.tree.children[-1]
        else:
            # Get the target
            target = target_frame.item
            if target.isfile:
                target = target.master
        target_frame = target.frame
        # Make sure we aren't moving the item to the same location:
        if item.master == target:
            frame.grid(row=item.idx, column=0, sticky="ew")
            return None
        # Make sure we aren't moving the folder to a child folder
        targets_master = target
        while targets_master is not None:
            if targets_master == item:
                frame.grid(row=item.idx, column=0, sticky="ew")
                return None
            targets_master = targets_master.master
        # Move the item
        item.move_to(target)
        # Make sure we grid_forget everything if the target isn't expanded
        if not target.expanded:
            frame.place_forget()
            if not item.isfile:
                self.hide_folder(item)
            else:
                # Just unselect it
                self.call_grid_forget(item)
        self._frame_moved(frame)

    # ????????????????????????????????????????????????????????????????
    def _frame_moved(self, frame:tk.Frame) -> None:
        new_idx, found = self.slow_item_to_idx(frame.item)
        assert found
        to_add = []
        to_move = [frame.item]
        while len(to_move) > 0:
            item = to_move.pop(0)
            if not item.isfile:
                to_move = item.children.copy() + to_move
            item.frame.item.idx = new_idx
            self.shown_items.remove(item)
            item.frame.indentation.config(width=self.get_indentation(item))
            to_add.append(item)
            new_idx += 1
        for item in to_add:
            self.shown_items.insert(item.idx, item)
        self.fix_idxs()

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

    def get_frame_from_event(self, event:tk.Event) -> tk.Frame:
        widget = event.widget
        if isinstance(widget, (tk.Label, tk.Canvas)):
            return widget.master
        return widget

    def y_in_frame(self, y:int, frame:tk.Frame) -> bool:
        if len(frame.grid_info()) == 0:
            # frame has beeen placed:
            return False
        frame_y = frame.winfo_y()
        return frame_y < y < frame_y + frame.winfo_height()

    def set_up_images(self) -> None:
        self.images = {}
        for extension in ("txt", "cpp", "file", "py"):
            image = tk.PhotoImage(file=f"sprites/.{extension}.png",
                                  master=self.master)
            self.images.update({extension: image})

    def add(self, folder_name:str) -> None:
        folder = self.tree.add(folder_name)
        self._update()
        self.expand_folder(folder)

    def remove(self, folder:str) -> None:
        raise ValueError("Unimplemented???")
        self.tree.remove(folder)

    def clean_up(self) -> None:
        for item in self.shown_items.copy():
            if item.garbage_collect:
                self.delete(item)
        self.fix_idxs()

    def _update(self, update_tree:bool=True) -> None:
        if update_tree:
            self.tree._update()
        self.check_add_new_items(self.tree)
        self.clean_up()

    def delete(self, item) -> None:
        if item == self.selected:
            self.select(None)
        if not item.isfile:
            for child in item.children.copy():
                self.delete(child)
        item.destroy()
        item.frame.destroy()
        self.shown_items.remove(item)

    def fix_idxs(self) -> None:
        for idx, item in enumerate(self.shown_items):
            item.idx = idx
            if len(item.frame.grid_info()) + len(item.frame.place_info()) > 0:
                item.frame.grid(row=idx, column=0, sticky="ew")

    def change_colour(self, frame:tk.Frame, bg:str=None, fg:str=None) -> None:
        to_change = [frame]
        while len(to_change) != 0:
            widget = to_change.pop(0)
            if isinstance(widget, tk.Frame):
                to_change.extend(widget.winfo_children())
            elif isinstance(widget, tk.Label):
                widget.config(fg=fg)
            widget.config(bg=bg)

    def check_add_new_items(self, tree:base_explorer.Folder, idx:int=0) -> int:
        start_idx = idx
        for child in tree:
            if child.new:
                self.show(child, idx)
                if (child.master is not None) and (not child.master.expanded):
                    self.call_grid_forget(child)
            idx += 1
            if not child.isfile:
                idx += self.check_add_new_items(child, idx)
        return idx - start_idx

    def show(self, item, row:int) -> None:
        if item in self.shown_items:
            # Already shown
            return None

        frame = tk.Frame(self.master, bg=self.bg, highlightthickness=0, bd=0)
        frame.grid(row=row, column=0, sticky="ew")

        indentation = tk.Frame(frame, width=self.get_indentation(item),
                               bg=self.bg)
        indentation.grid(row=0, column=0)

        if item.isfile:
            tk_icon = self.images[item.extension]
            icon = tk.Canvas(frame, bg=self.bg, bd=0, highlightthickness=0,
                             width=tk_icon.width(), height=tk_icon.height())
            icon.create_image(0, 0, anchor="nw", image=tk_icon)
            icon.grid(row=0, column=1)
            frame.icon = icon
        else:
            if item.expanded:
                text = "-"
            else:
                text = "+"
            expandeder = tk.Label(frame, text=text, bg=self.bg, fg=self.fg,
                                  font=("DejaVu Sans Mono", 9))
            expandeder.grid(row=0, column=1)
            frame.expandeder = expandeder

        name = tk.Label(frame, text=item.name, bg=self.bg, fg=self.fg,
                        anchor="w")
        name.grid(row=0, column=2)

        frame.item = item
        frame.name = name
        frame.indentation = indentation

        item.frame = frame
        item.idx = row

        self.bind_frame(frame, "<B1-Motion>", self.mouse_moved)
        self.bind_frame(frame, "<ButtonPress-1>", self.mouse_pressed)
        self.bind_frame(frame, "<ButtonRelease-1>", self.mouse_released)

        # These functions should `return "break"`
        self.bind_frame(frame, "<ButtonPress-1>", self.user_selected, add=True)
        self.bind_frame(frame, "<Double-Button-1>", self.user_opened, add=True)
        self.bind_frame(frame, "<ButtonPress-3>", self.right_clicked, add=True)

        self.shown_items.insert(row, item)
        self.master.event_generate("<<HeightChanged>>", when="tail")

    def bind_frame(self, frame, *args, **kwargs) -> None:
        to_bind = [frame]
        while len(to_bind) > 0:
            widget = to_bind.pop()
            widget.bind(*args, **kwargs)
            to_bind.extend(widget.winfo_children())

    def fix_icon(self, item) -> None:
        # Folders have no icons right now
        if not item.isfile:
            return None
        canvas = item.frame.icon
        tk_icon = self.images[item.extension]
        canvas.config(width=tk_icon.width(), height=tk_icon.height())
        canvas.create_image(0, 0, anchor="nw", image=tk_icon)

    def get_indentation(self, item) -> int:
        return item.indentation*INDENTATION + PADX

    def user_selected(self, event:tk.Event) -> str:
        frame = self.get_frame_from_event(event)
        # User clicked at the end to remove selection
        if not hasattr(frame, "item"):
            self.select(None)
            return "break"
        item = frame.item
        if item.isfile:
            # User clicked on the same item again (not a double click)
            if self.selected == item:
                return "break"
            frame.event_generate("<<SelectedFile>>", when="tail")
        else:
            if frame.expandeder == event.widget:
                return self.user_opened(event)
            if self.selected == item:
                return "break"
            frame.event_generate("<<SelectedFolder>>", when="tail")
        self.select(item)
        return "break"

    def user_opened(self, event:tk.Event) -> str:
        frame = self.get_frame_from_event(event)
        if frame == self.master:
            return "break"
        item = frame.item
        if item.isfile:
            frame.event_generate("<<OpenedFile>>", when="tail")
        else:
            if item.expanded:
                self.collapse_folder(item)
            else:
                self.expand_folder(item)
            self.master.event_generate("<<HeightChanged>>", when="tail")
        return "break"

    def collapse_folder(self, folder:base_explorer.Folder) -> None:
        for child in folder.children:
            self.hide_folder(child)
        folder.frame.expandeder.config(text="+")
        folder.expanded = False

    def hide_folder(self, folder:base_explorer.Folder) -> None:
        to_hide = [folder]
        while len(to_hide) > 0:
            item = to_hide.pop(0)
            self.call_grid_forget(item)
            if not item.isfile:
                to_hide.extend(item.children)

    def expand_folder(self, item:base_explorer.Folder, draw:bool=True) -> None:
        for child in item.children:
            child.frame.grid(row=child.idx, column=0, sticky="ew")
            if (not child.isfile) and child.expanded:
                self.expand_folder(child, False)
        if draw:
            item.frame.expandeder.config(text="-")
            item.expanded = True

    def select(self, item) -> None:
        if isinstance(item, tk.Misc):
            raise VaueError("`item` must be an item not a frame.")
        if self.selected is not None:
            self.change_colour(bg=self.bg, frame=self.selected.frame,
                               fg=self.fg)
        self.selected = item
        if self.selected is not None:
            self.change_colour(bg=self.selected_bg, frame=item.frame,
                               fg=self.selected_fg)

    def call_grid_forget(self, item) -> None:
        if item == self.selected:
            self.select(None)
        item.frame.grid_forget()

    def right_clicked(self, event:tk.Event) -> str:
        return "break"


if __name__ == "__main__":
    def selected_file(event):
        print("[Debug]: Selected", event.widget.item)

    def opened_file(event):
        print("[Debug]: Opened", event.widget.item)

    root = tk.Tk()

    explorer_frame = tk.Frame(root, highlightthickness=0, bd=0, width=180,
                              height=260, bg="black")
    explorer_frame.pack(fill="both", expand=True)

    explorer = Explorer(explorer_frame)
    explorer.add("testing")

    explorer_frame.bind_all("<<OpenedFile>>", opened_file)
    explorer_frame.bind_all("<<SelectedFile>>", selected_file)

    # root.mainloop()
    root.bind("a", lambda e: print("="*80+"\n"+explorer.tree.to_string()+"\n"+"="*80))
