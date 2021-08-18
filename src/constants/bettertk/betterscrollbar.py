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
    __slots__ = ("mouse_pressed", "x0", "x1")

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

    def set(self, low:str, high:str) -> None:
        width = self.winfo_width()
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


class ScrolledText(tk.Text):
    def __init__(self, master, vscroll:bool=True, hscroll:bool=False,
                 bg:str="black", fg:str="white", **kwargs):
        self.master_frame = tk.Frame(master, highlightthickness=0, bd=0, bg=bg)
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.grid_columnconfigure(0, weight=1)
        super().__init__(self.master_frame, bg=bg, fg=fg, **kwargs)
        super().grid(row=0, column=0, sticky="news")
        if vscroll:
            self.vscroll = BetterScrollBarVertical(self.master_frame,
                                                   command=self.yview)
            self.vscroll.grid(row=0, column=1, sticky="news")
            super().config(yscrollcommand=self.vscroll.set)
        if hscroll:
            self.hscroll = BetterScrollBarHorizontal(self.master_frame,
                                                     command=self.xview)
            self.hscroll.grid(row=1, column=0, sticky="news")
            super().config(xscrollcommand=self.hscroll.set)

    def pack(self, **kwargs) -> None:
        self.master_frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        self.master_frame.grid(**kwargs)

    def place(self, **kwargs) -> None:
        self.master_frame.place(**kwargs)

    def pack_forget(self) -> None:
        self.master_frame.pack_forget()

    def grid_forget(self) -> None:
        self.master_frame.grid_forget()

    def place_forget(self) -> None:
        self.master_frame.place_forget()


if __name__ == "__main__":
    from bettertk import BetterTk
    from betterframe import BetterFrame

    root = BetterTk()
    root.title("New")
    # root.resizable(False, False)

    frame = BetterFrame(root, bg="black", height=200, hscroll=True, vscroll=True,
                        VScrollBarClass=BetterScrollBarVertical,
                        HScrollBarClass=BetterScrollBarHorizontal)
    frame.pack(fill="both", expand=True)

    for i in range(30):
        text = f"This is text label number {i}"
        text = " "*50 + text + " "*50
        label = tk.Label(frame, text=text, bg="black",
                         fg="white")
        label.pack(fill="x")

    root.mainloop()
