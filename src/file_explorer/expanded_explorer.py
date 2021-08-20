from __future__ import annotations
import tkinter as tk
import shutil
import os

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
        super().add_command(label="New folder", command=self.new_folder)
        self.explorer = explorer

    def delete(self, event:tk.Event=None) -> str:
        if self.explorer.selected is None:
            return "break"
        filename = self.explorer.selected.name
        msg = f"Are you sure you want to delete \"{filename}\"?"
        result = askyesno(title="Delete file?", message=msg, icon="warning")
        if result:
            self._delete(self.explorer.selected)

    def _delete(self, item) -> None:
        if item.isfile:
            os.remove(item.full_path)
        else:
            shutil.rmtree(item.full_path)
        self.explorer.delete(item)

    def new_file(self) -> None:
        self.new_item("file")

    def new_folder(self) -> None:
        self.new_item("folder")

    def new_item(self, type:str) -> None:
        # Get the selected file's master:
        selected = self.explorer.selected
        if selected is None:
            selected = self.explorer.tree.children[-1]
        if selected.isfile:
            selected = selected.master
        # Make sure that the folder is expanded
        if (not selected.isfile) and (not selected.expanded):
            self.explorer.expand_folder(selected)
        # Create the new file
        if type == "file":
            new_item = selected.new_file("")
        elif type == "folder":
            new_item = selected.new_folder("")
        else:
            raise ValueError(f"Invalid `type`: \"{type}\"")
        self.explorer._update(update_tree=False)
        # Select the new file
        self.explorer.select(new_item)
        self.explorer.creating_item = True
        # Rename the new file
        self.explorer.rename()


class ExpandedExplorer(Explorer):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.menu = RightClickMenu(self)
        self.renaming = False
        self.renaming_entry = None
        self.creating_item = False
        self.bind_frame(self.master, "<Delete>", self.menu.delete)

    def add(self, folder:str) -> None:
        super().add(folder)

    def right_clicked(self, event:tk.Event) -> str:
        # Make sure we aren't renaming
        if self.renaming:
            return "break"
        # Get the frame
        frame = self.get_frame_from_event(event)
        # Make sure we clicked on something
        if not hasattr(frame, "item"):
            self.select(None)
            return "break"
        # Select the frame
        self.select(frame.item)
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
        item = self.selected
        self.renaming_entry = tk.Entry(item.frame, bg=self.bg, fg=self.fg,
                                       insertbackground=self.fg)
        self.renaming_entry.grid(row=0, column=2)
        self.renaming_entry.bind("<Escape>", self.cancel_rename)
        self.renaming_entry.bind("<Return>", self._rename)
        self.renaming_entry.insert(0, item.name)
        self.renaming_entry.select_range(0, "end")
        self.renaming_entry.icursor("end")
        self.renaming_entry.focus_set()

    def _rename(self, event:tk.Event=None) -> None:
        item = self.selected
        new_name = self.renaming_entry.get()
        old_path = item.full_path
        item.frame.name.config(text=new_name)
        item.rename(new_name)
        new_path = item.full_path
        self.renaming = False
        if self.creating_item:
            if item.isfile:
                with open(new_path, "w") as file:
                    pass
            else:
                os.mkdir(new_path)
            self.creating_item = False
        else:
            os.rename(old_path, new_path) # os.rename
        self.cancel_rename()
        self.fix_icon(item)

    def cancel_rename(self, event:tk.Event=None) -> None:
        if self.renaming_entry is None:
            return None
        self.renaming_entry.destroy()
        self.renaming_entry = None
        self.renaming = False
        if self.creating_item:
            self.delete(self.selected)
            self.creating_item = False


if __name__ == "__main__":
    root = tk.Tk()

    explorer_frame = tk.Frame(root, highlightthickness=0, bd=0, width=180,
                              height=300)
    explorer_frame.pack(fill="both", expand=True)

    explorer = ExpandedExplorer(explorer_frame)
    explorer.add("testing")

    # root.mainloop()
    root.bind("a", lambda e: print("="*80+"\n"+explorer.tree.to_string()+"\n"+"="*80))
