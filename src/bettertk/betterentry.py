from __future__ import annotations
import tkinter as tk


class BetterEntry(tk.Text):
    def __init__(self, master:tk.Misc, **kwargs) -> None:
        super().__init__(master, **{"bg":"black", "fg":"white", "height":1,
                                    "width":20, "insertbackground":"white",
                                    "font":"Sans-Serif 10", **kwargs})
        super().bind("<KP_Enter>", self.enter_pressed)
        super().bind("<Return>", self.enter_pressed)
        super().bind("<Control-a>", self.select_all)
        super().bind("<Control-A>", self.select_all)
        super().bind("<Tab>", self.tab_pressed)
        super().bind("<Control-v>", self.paste)
        super().bind("<Control-V>", self.paste)
        super().bind("<Control-c>", self.copy)
        super().bind("<Control-C>", self.copy)
        super().bind("<Control-x>", self.cut)
        super().bind("<Control-X>", self.cut)

        super().bind("<Shift-Right>", self.shift_right)
        super().bind("<Shift-Down>", self.shift_down)

        self.return_binds:list = []

    def tab_pressed(self, event:tk.Event) -> str:
        super().tk_focusNext().focus_set()
        return "break"

    def enter_pressed(self, event:tk.Event) -> str:
        for function in self.return_binds:
            if function(event) == "break":
                break
        return "break"

    def bind(self, sequence:str, function, *args, **kwargs) -> str:
        if sequence == "<Return>":
            self.return_binds.append(function)
        else:
            super().bind(sequence, function, *args, **kwargs)

    def select(self, start:str, end:str) -> None:
        super().tag_add("sel", start, end)
        super().mark_set("insert", end)
        super().see("insert")

    def select_all(self, event:tk.Event=None) -> str:
        self.select("0.0", "end-1c")
        super().mark_set("tk::anchor1", "0.0")
        return "break"

    def copy(self, event:tk.Event=None) -> str:
        sel:tuple[str] = self.get_sel()
        if sel is not None:
            text:str = super().get(*sel)
            super().clipboard_clear()
            super().clipboard_append(text)
        return "break"

    def paste(self, event:tk.Event=None) -> str:
        sel:tuple[str] = self.get_sel()
        if sel is not None:
            super().delete(*sel)
        text:str = super().clipboard_get().replace("\n", "")
        super().insert("insert", text)
        return "break"

    def cut(self, event:tk.Event=None) -> str:
        self.copy(event)
        sel:tuple[str] = self.get_sel()
        if sel is not None:
            super().delete(*sel)

    def set(self, text:str) -> str:
        self.delete()
        super().insert("0.0", str(text).replace("\n", ""))

    def clear(self) -> None:
        super().delete("0.0", "end")

    def insert(self, index:int, text:str) -> None:
        super().insert(f"1.{index}", str(text).replace("\n", ""))

    def get(self) -> str:
        return super().get("0.0", "end").strip("\n")

    def get_sel(self) -> tuple[str]:
        sel:tuple[str] = super().tag_ranges("sel")
        if len(sel) != 2:
            return None
        return sel

    def shift_right(self, event:tk.Event) -> str:
        if super().compare("insert", "==", "end-1c"):
            return "break"

    def shift_down(self, event:tk.Event=None) -> str:
        super().mark_set("tk::anchor1", "insert")
        self.select("insert", "end-1c")
        return "break"


if __name__ == "__main__":
    root:tk.Tk = tk.Tk()

    entry:BetterEntry = BetterEntry(root)
    entry.bind("<Return>", lambda e: print(f"\"{entry.get()}\""))
    entry.pack(fill="both", expand=True)
