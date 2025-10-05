# Partialy taken from @BryanOakley's answer here:
# https://stackoverflow.com/a/57350295/11106801
import tkinter as tk

DEBUG:bool = False


class BaseBetterScrollBar(tk.Canvas):
    __slots__ = "_thumb_colour", "_active_thumb_colour", "_thumb_colour", \
                "_command", "_thumb", "_mouse_pressed", "_p0", "_p1", \
                "_grid_kwargs", "_shown", "hide", "_offset", "_height", \
                "_width", "_height", "_high", "_low", "_destroyed"

    def __init__(self, master:tk.Misc, thickness:int=12, can_hide:bool=False,
                 thumb_colour:str="#555555", active_thumb_colour:str="#777777",
                 bg:str="black", command=None, **kwargs) -> None:
        super().__init__(master, highlightthickness=0, bd=0, bg=bg,
                         width=thickness, height=thickness, **kwargs)
        # Scrollbar specific args
        self._active_thumb_colour:str = active_thumb_colour
        self._thumb_colour:str = thumb_colour
        self._command = command
        # For dragding
        self._mouse_pressed:bool = False
        # Hide/Show
        self._grid_kwargs:dict = None
        self._destroyed:bool = False
        self._shown:bool = True
        self.hide:bool = False
        self._offset:int = 0
        # For calculations
        self._height:int = 0
        self._width:int = 0
        self._high:float = 0
        self._low:float = 0
        self._p0:int = 0
        self._p1:int = 0
        # Create thumb
        self._thumb = super().create_rectangle(0, 0, 1, 1, outline="",
                                               fill=self._thumb_colour)
        # Set up bindings
        super().bind("<B1-Motion>", self._on_drag)
        super().bind("<ButtonPress-1>", self._on_click)
        super().bind("<ButtonRelease-1>", self._on_release)
        super().bind("<Leave>", self._reset_thumb_colour)
        super().bind("<Configure>", self._on_resize)

    def config(self, **kwargs:dict) -> dict:
        """
        On config, intercept:
                              can_hide
                              thumb_colour
                              active_thumb_colour
        """
        if len(kwargs) == 0:
            return super().config()
        self._thumb_colour:str = kwargs.pop("thumb_colour", self._thumb_colour)
        self._active_thumb_colour:str = kwargs.pop("active_thumb_colour",
                                                   self._active_thumb_colour)
        self._command = kwargs.pop("command", self._command)
        self.hide:str = kwargs.pop("can_hide", self.hide)
        if kwargs:
            raise KeyError(f"Unknown arguments: {set(kwargs.keys())}")
    configure = config

    def _reset_thumb_colour(self, event:tk.Event=None) -> None:
        if not self._mouse_pressed:
            self.itemconfig(self._thumb, fill=self._thumb_colour)

    def _on_resize(self, event:tk.Event) -> None:
        self._width, self._height = event.width, event.height
        self._recalc_redraw()

    def _on_click(self, event:tk.Event) -> None:
        event_p:int = self.get_arg_from_event(event)
        if self._p0 < event_p < self._p1:
            self._offset:int = event_p - self._p0
            self._mouse_pressed:bool = True
            self._on_drag(event)

    def _on_release(self, event:tk.Event) -> None:
        if not self._mouse_pressed:
            return None
        self._mouse_pressed:bool = False
        if self._p0 < self.get_arg_from_event(event) < self._p1:
            super().itemconfig(self._thumb, fill=self._active_thumb_colour)
        else:
            self._reset_thumb_colour()

    def _on_drag(self, event:tk.Event) -> None:
        if not self._mouse_pressed:
            return None
        event_p:int = self.get_arg_from_event(event)
        if self._command is not None:
            value:float = (event_p-self._offset) / self.get_major_length()
            self._command("moveto", str(min(1.0, max(0.0, value))))

    def _recalculate(self) -> None:
        """
        Re-calculates the position+size of the thumb. Doesn't redraw anything
        """
        length:int = self.get_major_length()
        self._p0:int = max(int(length*self._low+0.5), 0)
        self._p1:int = min(int(length*self._high+0.5), length)
        if DEBUG: print(f"[DEBUG]: Draw {self._p0}, {self._p1}")

    def _recalc_redraw(self) -> None:
        """
        Re-calculates and redraws the thumb
        """
        if self._destroyed: return None
        self._recalculate()
        self._redraw()

    def destroy(self) -> None:
        self._destroyed:bool = True
        super().destroy()

    def set(self, low:str, high:str) -> None:
        low, high = float(low), float(high)
        self._low, self._high = low, high
        if self.hide:
            if self._shown:
                if (low == 0) and (high == 1):
                    self._grid_kwargs = super().grid_info()
                    self.grid_forget()
                    return None
            else:
                if (low != 0) or (high != 1):
                    if self._grid_kwargs is not None:
                        self.grid(**self._grid_kwargs)
                    return None
        self._recalc_redraw()

    def grid(self, **kwargs:dict) -> None:
        self._grid_kwargs:dict = kwargs
        self._shown:bool = True
        super().grid(**kwargs)
        self._recalc_redraw()

    def grid_forget(self) -> None:
        self._shown:bool = False
        super().grid_forget()

    def pack(self, **kwargs) -> None:
        if self.hide:
            raise NotImplementedError("Hide only works with grid")
        super().pack(**kwargs)

    def place(self, **kwargs) -> None:
        if self.hide:
            raise NotImplementedError("Hide only works with grid (I am lazy)")
        super().place(**kwargs)

    def get_arg_from_event(self, event:tk.Event) -> int:
        raise NotImplementedError("Overwrite this method or use " \
                                  "BetterScrollBarHorizontal or " \
                                  "BetterScrollBarVertical instead")

    def get_major_length(self) -> int:
        raise NotImplementedError("Overwrite this method or use " \
                                  "BetterScrollBarHorizontal or " \
                                  "BetterScrollBarVertical instead")

    def _redraw(self) -> None:
        """
        Redraw the thumb using:
          self._p0, self._p1, self._width, and self._height
        """
        raise NotImplementedError("Overwrite this method or use " \
                                  "BetterScrollBarHorizontal or " \
                                  "BetterScrollBarVertical instead")


class BetterScrollBarHorizontal(BaseBetterScrollBar):
    __slots__ = ()

    def __init__(self, master:tk.Misc, orient:str="horizontal", **kwargs):
        if orient != "horizontal":
            raise ValueError("Invalid orient for a horizontal scroll bar")
        super().__init__(master, **kwargs)

    def _redraw(self) -> None:
        super().coords(self._thumb, self._p0, 0, self._p1, self._height)

    def get_arg_from_event(self, event:tk.Event) -> int:
        return event.x

    def get_major_length(self) -> int:
        return self._width


class BetterScrollBarVertical(BaseBetterScrollBar):
    __slots__ = ()

    def __init__(self, master:tk.Misc, orient:str="vertical", **kwargs):
        if orient != "vertical":
            raise ValueError("Invalid orient for a horizontal scroll bar")
        super().__init__(master, **kwargs)

    def _redraw(self) -> None:
        super().coords(self._thumb, 0, self._p0, self._width, self._p1)

    def get_arg_from_event(self, event:tk.Event) -> int:
        return event.y

    def get_major_length(self) -> int:
        return self._height


class ScrolledText:
    __slots__ = "text_widget", "vscroll", "hscroll", "line_numbers"

    def __init__(self, master:tk.Misc, text_widget:tk.Text, vscroll:bool=True,
                 hscroll:bool=False, lines_numbers:bool=False,
                 line_numbers_width:int=32):
        self.assert_assertions(master, text_widget)
        self.text_widget:tk.Text = text_widget
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
        self.text_widget:ScrolledText = None
        self.last_redrawn:tuple[int] = None
        self.width:int = width

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

        self.redraw_loop()

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

    test:str = "\n".join(" ".join(map(str, range(i+1))) for i in range(100))
    text.insert("end", test)

    make_scrolled(root, text, vscroll=True, hscroll=True, lines_numbers=True)