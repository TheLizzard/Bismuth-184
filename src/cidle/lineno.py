from .scrollbar import AutoScrollbar
import tkinter as tk


class BindedText(tk.Text):
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)
        self._orig = self._w + "_binded"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        cmd = (self._orig,) + args
        try:
            result = self.tk.call(cmd)
        except:
            return None

        changed = args[0] in ("insert", "replace", "delete")
        changed |= args[0:3] == ("mark", "set", "insert")
        changed |= args[0:2] == ("xview", "moveto")
        changed |= args[0:2] == ("xview", "scroll")
        changed |= args[0:2] == ("yview", "moveto")
        changed |= args[0:2] == ("yview", "scroll")

        if changed:
            self.event_generate("<<Change>>", when="tail")
        return result


class TextLineNumbers(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
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
            self.move(text, bounds[0]-bounds[2], 0)

            i = self.textwidget.index("%s+1line"%i)


# Unused:
class LinedText(BindedText):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.xscroll = AutoScrollbar(master, orient="horizontal")
        self.yscroll = AutoScrollbar(master, orient="vertical")
        self.config(xscrollcommand=self.xscroll.set)
        self.config(yscrollcommand=self.yscroll.set)
        self.xscroll.config(command=self.xview)
        self.yscroll.config(command=self.yview)

        self.linenumbers = TextLineNumbers(master, width=30)
        self.linenumbers.grid(row=1, column=1, sticky="news")
        self.linenumbers.attach(self)

        self.bind("<<Change>>", self.linenumbers.redraw)
        self.bind("<Configure>", self.linenumbers.redraw)

        self.grid(row=1, column=2)
        self.xscroll.grid(row=2, column=1, columnspan=2, sticky="news")
        self.yscroll.grid(row=1, column=3, sticky="news")

        text_meths = vars(self).keys()
        methods = vars(tk.Pack).keys() | vars(tk.Grid).keys() |\
                  vars(tk.Place).keys()
        methods = methods.difference(text_meths)

        self.set_word_boundaries()

        for m in methods:
            if m[0] != "_" and m != "config" and m != "configure":
                setattr(self, m, getattr(master, m))
