# Partialy taken from @BryanOakley's answer here:
# https://stackoverflow.com/a/57350295/11106801
import tkinter as tk


class BaseBetterScrollBar:
    __slots__ = ("thumb_colour", "active_thumb_colour", "bg",
                 "show_arrows", "command")

    def __init__(self, width:int=12, bg:str="black", command=None,
                 thumb_colour:str="#555555", show_arrows:bool=False,
                 active_thumb_colour:str="#777777"):
        self.bg = bg
        self.width = width
        self.command = command
        self.thumb_colour = thumb_colour
        self.active_thumb_colour = active_thumb_colour
        if show_arrows:
            raise NotImplementedError("Arrows aren't supported right now.")

    def reset_thumb_colour(self, event:tk.Event=None) -> None:
        if not self.mouse_pressed:
            self.itemconfig(self.thumb, fill=self.thumb_colour)

    def _set(self, value:float) -> None:
        if self.command is not None:
            self.command("moveto", value)


class BetterScrollBarVertical(tk.Canvas, BaseBetterScrollBar):
    __slots__ = ("mouse_pressed", "y0", "y1")

    def __init__(self, master, orient="vertical", **kwargs):
        if orient != "vertical":
            raise ValueError("Invalid orient for a vertical scroll bar")
        BaseBetterScrollBar.__init__(self, **kwargs)

        self.mouse_pressed = False
        self.offset = 0

        super().__init__(master, width=self.width, height=1,
                         bg=self.bg, highlightthickness=0, bd=0)

        self.thumb = super().create_rectangle(0, 0, 1, 1, outline="",
                                              fill=self.thumb_colour)
        super().bind("<ButtonPress-1>", self.on_click)
        super().bind("<ButtonRelease-1>", self.on_release)
        super().bind("<Motion>", self.on_motion)
        super().bind("<Leave>", self.reset_thumb_colour)

    def set(self, low:str, high:str) -> None:
        low, high = float(low), float(high)
        height = self.winfo_height()
        self.y0 = max(int(height * low), 0)
        self.y1 = min(int(height * high), height)
        super().coords(self.thumb, 0, self.y0, self.winfo_width(), self.y1)

    def on_click(self, event:tk.Event) -> None:
        if self.y0 < event.y < self.y1:
            self.mouse_pressed = True
            self.offset = event.y - self.y0
            self.on_motion(event)

    def on_release(self, event:tk.Event) -> None:
        self.mouse_pressed = False
        if not (self.y0 < event.y < self.y1):
            self.reset_thumb_colour()

    def on_motion(self, event:tk.Event) -> None:
        if self.y0 < event.y < self.y1:
            super().itemconfig(self.thumb, fill=self.active_thumb_colour)
        else:
            self.reset_thumb_colour()
        if self.mouse_pressed:
            y = (event.y - self.offset) / self.winfo_height()
            self._set(y)


class BetterScrollBarHorizontal(tk.Canvas, BaseBetterScrollBar):
    __slots__ = "mouse_pressed", "x0", "x1", "hide", "shown", "grid_kwargs"

    def __init__(self, master, orient="horizontal", **kwargs):
        if orient != "horizontal":
            raise ValueError("Invalid orient for a horizontal scroll bar")
        BaseBetterScrollBar.__init__(self, **kwargs)

        self.mouse_pressed = False
        self.offset = 0

        super().__init__(master, width=1, height=self.width,
                         bg=self.bg, highlightthickness=0, bd=0)

        self.thumb = super().create_rectangle(0, 0, 1, 1, outline="",
                                              fill=self.thumb_colour)
        super().bind("<ButtonPress-1>", self.on_click)
        super().bind("<ButtonRelease-1>", self.on_release)
        super().bind("<Motion>", self.on_motion)
        super().bind("<Leave>", self.reset_thumb_colour)

        self.hide:bool = False
        self.shown:bool = True

    def set(self, low:str, high:str) -> None:
        if (low == "0.0") and (high == "1.0") and self.hide and self.shown:
            self.grid_kwargs = super().grid_info()
            super().grid_forget()
            self.shown:bool = False
        elif ((low != "0.0") or (high != "1.0")) and self.hide and (not self.shown):
            super().grid(**self.grid_kwargs)
            self.shown:bool = True

        width = super().winfo_width()
        self.x0 = max(int(width * float(low)), 0)
        self.x1 = min(int(width * float(high)), width)
        super().coords(self.thumb, self.x0, 0, self.x1, self.winfo_height())

    def on_click(self, event:tk.Event) -> None:
        if self.x0 < event.x < self.x1:
            self.mouse_pressed = True
            self.offset = event.x - self.x0
            self.on_motion(event)

    def on_release(self, event:tk.Event) -> None:
        self.mouse_pressed = False
        if not (self.x0 < event.x < self.x1):
            self.reset_thumb_colour()

    def on_motion(self, event:tk.Event) -> None:
        if self.x0 < event.x < self.x1:
            super().itemconfig(self.thumb, fill=self.active_thumb_colour)
        else:
            self.reset_thumb_colour()
        if self.mouse_pressed:
            x = (event.x - self.offset) / self.winfo_width()
            self._set(x)

    def pack(self, **kwargs) -> None:
        if self.hide:
            raise NotImplementedError("Hide only works with grid")
        super().pack(**kwargs)

    def place(self, **kwargs) -> None:
        if self.hide:
            raise NotImplementedError("Hide only works with grid")
        super().place(**kwargs)


class ScrolledText:
    __slots__ = ("text_widget", "vscroll", "hscroll", "line_numbers")

    def __init__(self, master:tk.Misc, text_widget:tk.Text, vscroll:bool=True,
                 hscroll:bool=False, lines_numbers:bool=False,
                 line_numbers_width:int=32):
        self.assert_assertions(master, text_widget)
        self.text_widget = text_widget
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)
        self.text_widget.grid(row=0, column=1, sticky="news")
        if vscroll:
            self.vscroll = BetterScrollBarVertical(master,
                                                command=self.text_widget.yview)
            self.vscroll.grid(row=0, column=2, sticky="news")
            self.text_widget.config(yscrollcommand=self.vscroll.set)
        if hscroll:
            self.hscroll = BetterScrollBarHorizontal(master,
                                                command=self.text_widget.xview)
            self.hscroll.grid(row=1, column=1, sticky="news")
            self.text_widget.config(xscrollcommand=self.hscroll.set)
            self.text_widget.config(wrap="none")

        if lines_numbers:
            self.line_numbers = LineNumbers(master, width=line_numbers_width)
            self.line_numbers.grid(row=0, column=0, sticky="ns")
            self.line_numbers.attach(self)

    def assert_assertions(self, master:tk.Misc, text_widget:tk.Text):
        if text_widget not in master.winfo_children():
            raise RuntimeError("The text widget should be a child of the " \
                               "`master`")
        if len(master.winfo_children()) != 1:
            raise RuntimeError("The `master` should only have the text " \
                               "widget inside it.")


class LineNumbers(tk.Canvas):
    def __init__(self, master:tk.Misc, width:int=32, **kwargs):
        super().__init__(master, bd=0, highlightthickness=0, bg="black",
                         width=width, **kwargs)
        self.width:int = width
        self.text_widget:ScrolledText = None
        self.last_redrawn:tuple[int] = None

    def attach(self, text_widget:ScrolledText) -> None:
        if self.text_widget is not None:
            raise RuntimeError("Can't attach twice.")
        self.scrolled_text:ScrolledText = text_widget
        self.text_widget:tk.Text = text_widget.text_widget
        self.font:str = self.text_widget.cget("font")

        self._yview = self.text_widget.yview
        self.scrolled_text.vscroll.command = self.yview
        self.text_widget.config(yscrollcommand=self.vscroll_set)
        self._insert = self.text_widget.insert
        self.text_widget.insert = self.insert

        self.fg:str = self.text_widget.cget("fg")

        max_y:int = super().winfo_screenheight()
        super().config(bg=self.text_widget.cget("bg"))
        super().create_line((self.width-3, 0, self.width-3, max_y), width=1,
                            fill=self.fg, tags=("separator", ))

        # self.redraw_loop()

    def redraw_loop(self) -> None:
        try:
            self.redraw()
            super().after(100, self.redraw_loop)
        except tk.TclError:
            pass

    def insert(self, index:str, text:str, *args:tuple) -> None:
        result = self._insert(index, text, *args)
        self.redraw()
        return result

    def yview(self, *args:tuple) -> None:
        result = self._yview(*args)
        self.redraw()
        return result

    def vscroll_set(self, *args:tuple[str]) -> None:
        result = self.scrolled_text.vscroll.set(*args)
        self.redraw()
        return result

    def redraw(self, event:tk.Event=None) -> None:
        if self.text_widget is None:
            pass

        i:str = self.text_widget.index(f"@0,{self.text_widget.winfo_height()}")
        redraw_state_end:tuple[int] = self.text_widget.dlineinfo(i)
        i:str = self.text_widget.index("@0,0")
        redraw_state_start:tuple[int] = self.text_widget.dlineinfo(i)
        redraw_state:tuple[int] = (redraw_state_start[1], redraw_state_start[3],
                                   redraw_state_end[1], redraw_state_end[3])
        if redraw_state == self.last_redrawn:
            return None
        else:
            self.last_redrawn:tuple[int] = redraw_state

        super().delete("lines")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            text:int = super().create_text(self.width-5, dline[1], anchor="nw",
                                           font=self.font, text=int(float(i)),
                                           fill=self.fg, tags=("lines", ))

            bounds:tuple[int] = super().bbox(text)
            super().move(text, bounds[0]-bounds[2], 0)

            i:str = self.text_widget.index(f"{i} +1l")


def make_scrolled(master:tk.Misc, text_widget:tk.Text, **kwargs):
    ScrolledText(master, text_widget, **kwargs)


# Example 1
if __name__ == "__main__":
    from bettertk import BetterTk
    from betterframe import BetterFrame

    root = BetterTk()
    root.title("New")
    # root.resizable(False, False)

    frame = BetterFrame(root, bg="black", height=200, hscroll=True,
                        VScrollBarClass=BetterScrollBarVertical, vscroll=True,
                        HScrollBarClass=BetterScrollBarHorizontal)
    frame.pack(fill="both", expand=True)

    for i in range(30):
        text = f"This is text label number {i}"
        text = " "*50 + text + " "*50
        label = tk.Label(frame, text=text, bg="black",
                         fg="white")
        label.pack(fill="x")

    root.mainloop()

# Example 2
if __name__ == "__main__":
    from bettertk import BetterTk

    root:BetterTk = BetterTk()
    root.title("ScrolledLined")

    text:tk.Text = tk.Text(root, bg="black", fg="white", width=80, height=20,
                           bd=0, highlightthickness=0, insertbackground="white",
                           wrap="none")

    text.insert("end", "\n".join(" ".join(map(str, range(i+1))) for i in range(100)))

    make_scrolled(root, text, vscroll=True, hscroll=True, lines_numbers=True)