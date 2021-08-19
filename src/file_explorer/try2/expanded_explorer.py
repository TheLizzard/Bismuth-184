from __future__ import annotations
import tkinter as tk

try:
    from .messagebox import askyesno
    from .explorer import Explorer
except ImportError:
    from explorer import Explorer
    from messagebox import askyesno


class RightClickMenu(tk.Menu):
    def __init__(self, explorer:ExpandedExplorer):
        super().__init__(explorer.master, tearoff=False, bg=explorer.bg, bd=0,
                         fg=explorer.fg)
        super().add_command(label="Rename", command=explorer.rename)
        super().add_command(label="Delete", command=self.delete)
        super().add_command(label="New file", command=self.new_file)
        self.explorer = explorer

    def delete(self, event:tk.Event=None) -> str:
        if self.explorer.selected is None:
            return "break"
        filename = self.explorer.selected.item.name
        msg = f"Are you sure you want to delete \"{filename}\"?"
        result = askyesno(title="Delete file?", message=msg, icon="warning")
        if result:
            self._delete(self.explorer.selected)

    def _delete(self, frame:tk.Frame) -> None:
        print(f"Deleting {frame.item}")
        full_path = frame.item.full_path
        ...
        self.explorer.delete(frame.item)

    def new_file(self) -> None:
        print("New file")
        selected = self.explorer.selected
        if selected is None:
            selected = self.explorer.shown_items[self.explorer.item_to_idx[?]]
        selected.item


class ExpandedExplorer(Explorer):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.menu = RightClickMenu(self)
        self.renaming = False
        self.renaming_entry = None
        self.master.bind_all("<Delete>", self.menu.delete)

    def right_clicked(self, event:tk.Event) -> str:
        # Make sure we aren't renaming
        if self.renaming:
            return "break"
        # Get the frame
        frame = self.get_frame_from_event(event)
        # Make sure the frame isn't the whole Explorer
        if frame == self:
            self.select(None)
            return "break"
        # Select the frame
        self.select(frame)
        self.master.focus_set()
        # Popup
        self.menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def mouse_pressed(self, event=tk.Event) -> str:
        if isinstance(event.widget, tk.Entry):
            return "break"
        else:
            self.cancel_rename()
            super().mouse_pressed(event)

    def rename(self) -> None:
        self.renaming = True
        frame = self.selected
        self.renaming_entry = tk.Entry(frame, bg=self.bg, fg=self.fg,
                                       insertbackground=self.fg)
        self.renaming_entry.grid(row=0, column=2)
        default_name = frame.item.name
        self.renaming_entry.bind("<Escape>", self.cancel_rename)
        self.renaming_entry.bind("<Return>", self._rename)
        self.renaming_entry.insert(0, default_name)
        self.renaming_entry.select_range(0, "end")
        self.renaming_entry.icursor("end")
        self.renaming_entry.focus_set()

    def _rename(self, event:tk.Event=None) -> None:
        new_name = self.renaming_entry.get()
        old_path = self.selected.item.full_path
        self.selected.name.config(text=new_name)
        self.selected.item.rename(new_name)
        new_path = self.selected.item.full_path
        print(f"Renaming {self.selected.item} => {new_name}")
        ...
        self.renaming = False
        self.cancel_rename()
        # Change icon image based on `self.selected.item.extension`???

    def cancel_rename(self, event:tk.Event=None) -> None:
        if self.renaming_entry is None:
            return None
        self.renaming_entry.destroy()
        self.renaming_entry = None
        self.renaming = False


if __name__ == "__main__":
    root = tk.Tk()

    explorer_frame = tk.Frame(root, highlightthickness=0, bd=0, width=180,
                              height=300)
    explorer_frame.pack(fill="both", expand=True)

    explorer = ExpandedExplorer(explorer_frame)
    explorer.add(".")

    # root.mainloop()
    root.bind("a", lambda e: print("="*80+"\n"+explorer.tree.to_string()+"\n"+"="*80))
