import tkinter as tk

try:
    from .expanded_explorer import ExpandedExplorer
except ImportError:
    from expanded_explorer import ExpandedExplorer


from constants.bettertk import BetterScrollBarHorizontal, BetterFrame, \
                               BetterScrollBarVertical


class Explorer(BetterFrame):
    def __init__(self, master, width:int, height:int, bg:str="black", **kwargs):
        super().__init__(master, hscroll=True, vscroll=True, **kwargs,
                         VScrollBarClass=BetterScrollBarVertical,
                         HScrollBarClass=BetterScrollBarHorizontal, bg=bg)

        self.explorer = ExpandedExplorer(self, bg=bg, **kwargs)

        super().config(width=width, height=height)
        super().resize("fit_width")
        super().bind("<<HeightChanged>>", self.update_height)

    def add(self, folder:str) -> None:
        self.explorer.add(folder)

    def update_height(self, event:tk.Event=None) -> None:
        super().update()
        items = self.explorer.shown_items
        if len(items) == 0:
            return None
        last_frame = items[-1].frame
        height = last_frame.winfo_height() + last_frame.winfo_y()
        super().config(height=height)

    def get_state(self) -> dict:
        folders = self.explorer.tree.children
        return {"folders": tuple(folder.full_path for folder in folders)}

    def set_state(self, state:dict) -> None:
        caller_added_folders = state.pop("folders", [])
        for folder in caller_added_folders:
            try:
                self.explorer.add(folder)
            except:
                pass
        if len(state) > 0:
            print("[FileExplorer] Didn't handle this part of `state`:", state)


if __name__ == "__main__":
    from constants.bettertk import BetterTk
    root = BetterTk()
    # root.geometry("180x200")

    explorer = Explorer(root, width=180, height=2600)
    explorer.pack(fill="y", expand=True, side="left")
    explorer.add("old")

    text = tk.Text(root, bg="black", fg="white")
    text.pack(fill="both", expand=True, side="right")
