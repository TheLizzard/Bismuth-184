import tkinter as tk


FIT_WIDTH = "fit_width"
FIT_HEIGHT = "fit_height"


# A canvas that implements all of the scrollbar stuff by moving all of
# the items. Useless for now.
class BetterCanvas(tk.Canvas):
    __slots__ = ("deltax", "deltay", "xscrollcommand", "yscrollcommand",
                 "scrollregion")

    def __init__(self, master, **kwargs):
        self.deltax = 0
        self.deltay = 0
        self.xscrollcommand = None
        self.yscrollcommand = None
        self.scrollregion = [0, 0, 1, 1]
        super().__init__(master, **self.parse_kwargs(kwargs))

    def parse_kwargs(self, kwargs) -> None:
        xscrollcommand = kwargs.pop("xscrollcommand", None)
        yscrollcommand = kwargs.pop("yscrollcommand", None)
        scrollregion = kwargs.pop("scrollregion", None)
        if xscrollcommand is not None:
            self.xscrollcommand = xscrollcommand
        if yscrollcommand is not None:
            self.yscrollcommand = yscrollcommand
        if scrollregion is not None:
            self.scrollregion = scrollregion
        return kwargs

    def config(self, **kwargs) -> None:
        return super().config(**self.parse_kwargs(kwargs))
    configure = config

    def bbox(self, what) -> tuple:
        x1, y1, x2, y2 = super().bbox(what)
        x1 += self.deltax
        x2 += self.deltax
        y1 += self.deltay
        y2 += self.deltay
        return (x1, y1, x2, y2)

    def yview(self, *args) -> (float, float) or None:
        if len(args) == 0:
            return self._yview()

        if len(args) == 2:
            if args[0] == "moveto":
                self.set_first_y(float(args[1]))
                return None

        if len(args) == 3:
            if args[0] == "scroll":
                self.yview_scroll(int(args[1]), args[2])
                return None

        args = ", ".join(map(repr, args))
        raise ValueError(f"Unhandled: yview({args})")

    def set_first_y(self, first:float) -> None:
        old_first, _ = self.yview()
        number = (first - old_first) * (self.scrollregion[3] - self.scrollregion[1])
        self.yview_scroll(int(number), "units", scale=False)

    def _yview(self) -> (float, float):
        canvas_size = super().winfo_height()
        scrollregion = self.scrollregion[3] - self.scrollregion[1]
        first = self.deltay / scrollregion
        last = first + canvas_size / scrollregion
        return first, last

    def yview_scroll(self, number:int, what:str, /, scale:bool=True) -> None:
        if what == "pages":
            first, last = self.yview()
            first += (last - first) * number
            self.set_first_y(first)
        elif what == "units":
            if scale:
                number *= 20
            self.scroll_y_pixels(number)
        else:
            raise ValueError(f"Unknown value for \"what\": \"{what}\"")
        if self.yscrollcommand is not None:
            self.yscrollcommand(*self.yview())

    def scroll_y_pixels(self, pixels:int) -> None:
        # Some magic:
        canvas_size = super().winfo_height()
        if pixels > 0:
            pixels = min(pixels, self.scrollregion[3]-self.deltay-canvas_size)
        elif pixels < 0:
            pixels = max(pixels, self.scrollregion[1]-self.deltay)
        if pixels != 0:
            super().move("all", 0, -pixels)
            self.deltay += pixels


class BetterFrame(tk.Frame):
    """
    Also known as `ScrollableFrame`
    There is no way to scroll <tkinter.Frame> so we are
    going to create a canvas and place the frame there.
    Scrolling the canvas will give the illusion of scrolling
    the frame
    Partly taken from:
        https://blog.tecladocode.com/tkinter-scrollable-frames/
        https://stackoverflow.com/a/17457843/11106801

    master_frame---------------------------------------------------------
    | dummy_canvas-----------------------------------------  y_scroll--  |
    | | self---------------------------------------------  | |         | |
    | | |                                                | | |         | |
    | | |                                                | | |         | |
    | | |                                                | | |         | |
    | |  ------------------------------------------------  | |         | |
    |  ----------------------------------------------------   ---------  |
    | x_scroll---------------------------------------------              |
    | |                                                    |             |
    |  ----------------------------------------------------              |
     --------------------------------------------------------------------
    """
    def __init__(self, master=None, scroll_speed:int=2, hscroll:bool=False,
                 vscroll:bool=True, bd:int=0, scrollbar_kwargs={},
                 HScrollBarClass=tk.Scrollbar, bg="#f0f0ed",
                 VScrollBarClass=tk.Scrollbar, **kwargs):
        assert isinstance(scroll_speed, int), "`scroll_speed` must be an int"
        self.scroll_speed = scroll_speed

        self.master_frame = tk.Frame(master, bd=bd, bg=bg)
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.grid_columnconfigure(0, weight=1)
        self.dummy_canvas = tk.Canvas(self.master_frame, highlightthickness=0,
                                      bd=0, bg=bg, **kwargs)
        super().__init__(self.dummy_canvas, bg=bg)

        # Create the 2 scrollbars
        if vscroll:
            self.v_scrollbar = VScrollBarClass(self.master_frame,
                                               orient="vertical",
                                               command=self.dummy_canvas.yview,
                                               **scrollbar_kwargs)
            self.v_scrollbar.grid(row=0, column=1, sticky="news")
            self.dummy_canvas.configure(yscrollcommand=self.v_scrollbar.set)
        if hscroll:
            self.h_scrollbar = HScrollBarClass(self.master_frame,
                                               orient="horizontal",
                                               command=self.dummy_canvas.xview,
                                               **scrollbar_kwargs)
            self.h_scrollbar.grid(row=1, column=0, sticky="news")
            self.dummy_canvas.configure(xscrollcommand=self.h_scrollbar.set)

        # Bind to the mousewheel scrolling
        self.dummy_canvas.bind_all("<MouseWheel>", self.scrolling_windows,
                                   add=True)
        self.dummy_canvas.bind_all("<Button-4>", self.scrolling_linux, add=True)
        self.dummy_canvas.bind_all("<Button-5>", self.scrolling_linux, add=True)
        self.bind("<Configure>", self.scrollbar_scrolling, add=True)

        # Place `self` inside `dummy_canvas`
        self.dummy_canvas.create_window((0, 0), window=self, anchor="nw")
        # Place `dummy_canvas` inside `master_frame`
        self.dummy_canvas.grid(row=0, column=0, sticky="news")

        self.pack = self.master_frame.pack
        self.grid = self.master_frame.grid
        self.place = self.master_frame.place
        self.pack_forget = self.master_frame.pack_forget
        self.grid_forget = self.master_frame.grid_forget
        self.place_forget = self.master_frame.place_forget

    def scrolling_windows(self, event:tk.Event) -> None:
        assert event.delta != 0, "On Windows, `event.delta` should never be 0"
        y_steps = int(-event.delta/abs(event.delta)*self.scroll_speed)
        self.dummy_canvas.yview_scroll(y_steps, "units")

    def scrolling_linux(self, event:tk.Event) -> None:
        y_steps = self.scroll_speed
        if event.num == 4:
            y_steps *= -1
        self.dummy_canvas.yview_scroll(y_steps, "units")

    def scrollbar_scrolling(self, event:tk.Event) -> None:
        region = list(self.dummy_canvas.bbox("all"))
        region[2] = max(self.dummy_canvas.winfo_width(), region[2])
        region[3] = max(self.dummy_canvas.winfo_height(), region[3])
        self.dummy_canvas.configure(scrollregion=region)

    def resize(self, fit:str=None, height:int=None, width:int=None) -> None:
        """
        Resizes the frame to fit the widgets inside. You must either
        specify (the `fit`) or (the `height` or/and the `width`) parameter.
        Parameters:
            fit:str       `fit` can be either `FIT_WIDTH` or `FIT_HEIGHT`.
                          `FIT_WIDTH` makes sure that the frame's width can
                           fit all of the widgets. `FIT_HEIGHT` is simmilar
            height:int     specifies the height of the frame in pixels
            width:int      specifies the width of the frame in pixels
        To do:
            ALWAYS_FIT_WIDTH
            ALWAYS_FIT_HEIGHT
        """
        if height is not None:
            self.dummy_canvas.config(height=height)
        if width is not None:
            self.dummy_canvas.config(width=width)
        if fit == FIT_WIDTH:
            super().update()
            self.dummy_canvas.config(width=super().winfo_width())
        if fit == FIT_HEIGHT:
            super().update()
            self.dummy_canvas.config(height=super().winfo_height())
    fit = resize


# Example 1
if __name__ == "__main__":
    root = tk.Tk()
    frame = BetterFrame(root, width=300, height=200, hscroll=True, vscroll=True)
    frame.pack()

    # Add the widgets in the main diagonal to see the horizontal and
    # vertical scrolling
    for i in range(51):
        label = tk.Label(frame, text=i, anchor="w")
        label.grid(row=i, column=i)

    root.mainloop()


# Example 2
if __name__ == "__main__":
    root = tk.Tk()
    frame = BetterFrame(root, height=200, hscroll=False, vscroll=True)
    frame.pack()

    for i in range(51):
        label = tk.Label(frame, text=f"Label number {i}")
        label.pack(anchor="w")

    # Force the frame to resize to fit all of the widgets:
    frame.resize(FIT_WIDTH)

    root.mainloop()
