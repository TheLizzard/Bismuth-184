import tkinter as tk
from constants.settings import settings


LINENUMBERS_WIDTH = settings.editor.linenumbers_width.get()
LINENUMBERS_BG = settings.editor.linenumbers_bg.get()
FG_COLOUR = settings.editor.fg.get()
FONT = settings.editor.font.get()


class LineNumbers(tk.Canvas):
    def __init__(self, master, bd=0, highlightthickness=0, colour=FG_COLOUR,
                 width=LINENUMBERS_WIDTH, bg=LINENUMBERS_BG, font=FONT,
                 **kwargs):
        super().__init__(master, bd=bd, highlightthickness=highlightthickness,
                         bg=bg, width=width, **kwargs)
        self.textwidget = None
        self.font = font
        self.colour = colour

    def attach(self, text_widget):
        self.textwidget = text_widget

    def redraw(self, event=None):
        if self.textwidget is None:
            raise Exception("First attach a text widget.")
        self.delete("all")
        # width = super().winfo_width()
        i = self.textwidget.index("@0,0")
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None:
                break
            text = super().create_text(34, dline[1], anchor="nw",
                                       font=self.font, text=int(float(i)),
                                       fill=self.colour)

            bounds = self.bbox(text)
            super().move(text, bounds[0]-bounds[2], 0)

            i = self.textwidget.index("%s+1line"%i)
