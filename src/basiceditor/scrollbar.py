from functools import partial
import tkinter as tk


class AutoScrollbar(tk.Scrollbar):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.geometry_manager_add = lambda: None
        self.geometry_manager_forget = lambda: None

    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.geometry_manager_forget()
        else:
            self.geometry_manager_add()
        super().set(lo, hi)

    def grid(self, **kwargs):
        self.geometry_manager_add = partial(super().grid, **kwargs)
        self.geometry_manager_forget = super().grid_forget

    def pack(self, **kwargs):
        self.geometry_manager_add = partial(super().pack, **kwargs)
        self.geometry_manager_forget = super().pack_forget

    def place(self, **kwargs):
        self.geometry_manager_add = partial(super().place, **kwargs)
        self.geometry_manager_forget = super().place_forget
