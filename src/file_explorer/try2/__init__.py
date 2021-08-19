import tkinter as tk

try:
    from .expanded_explorer import ExpandedExplorer
except ImportError:
    from expanded_explorer import ExpandedExplorer


from constants.bettertk import BetterScrollBarHorizontal, BetterFrame, \
                               BetterScrollBarVertical


class Explorer(BetterFrame):
    def __init__(self, master, width:int, height:int, bg:str="black", **kwargs):
        super().__init__(root, hscroll=True, vscroll=True, **kwargs,
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
        slaves = self.explorer.shown_items
        if len(slaves) == 0:
            return None
        last_slave = slaves[-1]
        height = last_slave.winfo_height() + last_slave.winfo_y()
        super().config(height=height)


if __name__ == "__main__":
    root = tk.Tk()

    explorer = Explorer(root, width=180, height=2600)
    explorer.pack(fill="both", expand=True)
    explorer.add(".")
