import tkinter as tk


class LineNumbers(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        self.textwidget = text_widget

    def redraw(self, event=None):
        if self.textwidget is None:
            raise Exception("First attach a text widget.")
        self.delete("all")
        i = self.textwidget.index("@0,0")
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None:
                break
            text = self.create_text(37, dline[1], anchor="nw",
                                    text=int(float(i)))

            bounds = self.bbox(text)
            super().move(text, bounds[0]-bounds[2], 0)

            i = self.textwidget.index("%s+1line"%i)
