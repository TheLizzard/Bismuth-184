import tkinter as tk
from .percolator import Percolator
from .scrollbar import AutoScrollbar
from .colorizer import ColorDelegator
from .findreplacebox import FindReplaceBox
from .lineno import TextLineNumbers, BindedText


class Text(BindedText):
    def __init__(self, master=None, *args, wrap="none", autoseparators=True,
                 undo=True, maxundo=-1, **kwargs):
        self.frame = tk.Frame(master)
        self.xscroll = AutoScrollbar(self.frame, orient="horizontal")
        self.yscroll = AutoScrollbar(self.frame)

        super().__init__(self.frame, *args, autoseparators=autoseparators,
                         undo=undo, maxundo=maxundo, wrap=wrap, **kwargs)

        # Show the line numbers:
        self.linenumbers = TextLineNumbers(self.frame, width=35)
        self.linenumbers.attach(self)
        self.linenumbers.grid(row=1, column=1, sticky="news")
        self.bind("<<Change>>", self.linenumbers.redraw)
        self.bind("<Configure>", self.linenumbers.redraw)

        self.grid(row=1, column=2, sticky="news")

        self.config(xscrollcommand=self.xscroll.set)
        self.config(yscrollcommand=self.yscroll.set)
        self.xscroll.config(command=self.xview)
        self.yscroll.config(command=self.yview)

        self.xscroll.grid(row=2, column=1, columnspan=2, sticky="news")
        self.yscroll.grid(row=1, column=3, sticky="news")

        self.percolator = Percolator(self)
        self.delegator = ColorDelegator()
        self.percolator.insertfilter(self.delegator)

        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-A>", self.select_all)
        self.bind("<Control-v>", self.paste)
        self.bind("<Control-V>", self.paste)
        self.bind("<Control-c>", self.copy)
        self.bind("<Control-C>", self.copy)
        self.bind("<Control-f>", self.find)
        self.bind("<Control-F>", self.find)
        self.bind("<Control-r>", self.replace)
        self.bind("<Control-R>", self.replace)
        self.bind("<Control-Shift-Z>", self.redo)
        self.bind("<Up>", self.up)
        self.bind("<Down>", self.down)

        text_meths = vars(self).keys()
        methods = vars(tk.Pack).keys() | vars(tk.Grid).keys() |\
                  vars(tk.Place).keys()
        methods = methods.difference(text_meths)

        self.set_word_boundaries()

        for m in methods:
            if m[0] != "_" and m != "config" and m != "configure":
                setattr(self, m, getattr(self.frame, m))

    def up(self, event):
        currentline = int(self.index("insert").split(".")[0])
        firstline = 1
        if currentline == firstline:
            self.mark_set("insert", "0.0")

    def down(self, event):
        currentline = int(self.index("insert").split(".")[0])
        endline = int(self.index("end").split(".")[0])-1
        if currentline == endline:
            self.mark_set("insert", "end")

    def redo(self, event):
        self.event_generate("<Control-y>", when="tail")
        return "break"

    def find(self, event):
        replace = FindReplaceBox(self)
        replace.show("find")

    def replace(self, event):
        replace = FindReplaceBox(self)
        replace.show("replace")

    def paste(self, event):
        if len(self.tag_ranges("sel")) != 0:
            start, finish = self.tag_ranges("sel")
            self.delete(start, finish)
        text = self.clipboard_get()
        self.insert("insert", text)
        return "break"

    def copy(self, event):
        if len(self.tag_ranges("sel")) != 0:
            start, finish = self.tag_ranges("sel")
            text = self.get(start, finish)
            self.clipboard_clear()
            self.clipboard_append(text)
        return "break"

    def set_select_colour(self, bg="orange", fg="black"):
        self.tag_config("sel", background=bg, foreground=fg)
        self["inactiveselectbackground"] = bg

    def select_all(self, event):
        self.tag_add("sel", "1.0", "end")
        self.mark_set("insert", "end")
        return "break"

    def set_word_boundaries(self):
        word_chars = "a-zA-Z0-9_\n"
        self.tk.call("tcl_wordBreakAfter", "", 0)
        self.tk.call("set", "tcl_wordchars", "[%s]"%word_chars)
        self.tk.call("set", "tcl_nonwordchars", "[^%s]"%word_chars)


if __name__ == "__main__":
    root = tk.Tk()
    text = Text(root)
    text.pack()
