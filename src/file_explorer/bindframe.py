from __future__ import annotations
import tkinter as tk


class BindFrame(tk.Frame):
    __slots__ = ()

    def bind(self, seq:str, func:Function, add:bool=False) -> str:
        def wrapper(event:tk.Event) -> str:
            if isinstance(event.widget, str):
                return ""
            ewidget:str = event.widget._w
            swidget:str = self._w
            if not ewidget.startswith(swidget):
                return ""
            if "toplevel" in ewidget.removeprefix(swidget):
                return ""
            return func(event)
        self.bind_all(seq, wrapper, add=add)

def make_bind_frame(frame:tk.Frame) -> None:
    frame.bind = lambda *args, **kwargs: BindFrame.bind(frame, *args, **kwargs)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("200x200")

    other_frame = tk.Frame(root, bg="green", width=200, height=100)
    other_frame.pack(fill="both", expand=True)

    outter_frame = tk.Frame(root, bg="blue", width=200, height=100)
    outter_frame.pack(fill="both", expand=True)
    make_bind_frame(outter_frame)

    outter_frame.bind("<Button-1>", lambda e: print(e.widget), "+")

    inner_frame = tk.Frame(outter_frame, bg="red", width=100, height=100)
    inner_frame.grid(row=1, column=1)

    print("Clicking the red/blue frames should print the event")
    print("All events on the green frame should be ignored")
