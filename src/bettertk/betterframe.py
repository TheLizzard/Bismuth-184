from __future__ import annotations
import tkinter as tk


# .bind on this frame binds to all its children
class BindFrame(tk.Frame):
    """
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
    """
    __slots__ = ()

    def bind(self, seq:str, func:Function, add:bool=False) -> str:
        self_name:str = self._w
        def wrapper(event:tk.Event) -> str:
            widget:tk.Misc|str|None = event.widget # might be a str
            while True:
                if not isinstance(widget, tk.Misc):
                    return ""
                if widget == self:
                    return func(event)
                if isinstance(widget, tk.Toplevel|tk.Tk):
                    return ""
                widget:tk.Misc|None = widget.master
        return self.bind_all(seq, wrapper, add=add)

def make_bind_frame(frame:tk.Frame, *, method:str="bind") -> None:
    func = lambda *args, **kwargs: BindFrame.bind(frame, *args, **kwargs)
    setattr(frame, method, func)


# A canvas that implements all of the scrollbar stuff by moving all of
# the items. Unused - deprecated.
class BetterCanvas(tk.Canvas):
    __slots__ = "deltax", "deltay", "xscrollcommand", "yscrollcommand", \
                "scrollregion"

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
        number = (first-old_first) * (self.scrollregion[3]-self.scrollregion[1])
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
    Partly taken from:
        https://blog.tecladocode.com/tkinter-scrollable-frames
        https://stackoverflow.com/a/17457843/11106801
        https://web.archive.org/web/20170514022131id_/
                http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame
        https://stackoverflow.com/a/59663408

    outter---------------------------------------------------------------
    | canvas-----------------------------------------------  y_scroll--  |
    | | inner--------------------------------------------  | |         | |
    | | | self-----------------------------------------  | | |         | |
    | | | |                                            | | | |         | |
    | | | |                                            | | | |         | |
    | | |  --------------------------------------------  | | |         | |
    | |  ------------------------------------------------  | |         | |
    |  ----------------------------------------------------   ---------  |
    | x_scroll---------------------------------------------              |
    | |                                                    |             |
    |  ----------------------------------------------------              |
     --------------------------------------------------------------------

    Outter: The outter frame holds everything in a neat package.
    Canvas: The canvas is one of the 3 widgets that can be scrolled in tkinter
    Inner:  Holds self and inforces minsize using grid_*configure()
    Self:   Holds all of the widgets you want to scroll

    Notes:
        * Setting the width/height using config/__init__ will freeze the
            width/height respectively
        * By default this widget's size is determined the same way as a
            tk.Label in the direction where there is a scroll bar. In the
            direction without scrollbar, this widget tries to expand.

    TODO:
        Overwrite in `.config` and `.configure`
            width, height, bd, highlightthickness, bg, background, borderwidth
            relief
    """

    def __init__(self, master=None, scroll_speed:int=2, hscroll:bool=False,
                 vscroll:bool=True, bd:int=0, scrollbar_kwargs:dict={},
                 hscrolltop:bool=False, bg:str="#f0f0ed",
                 highlightthickness:int=0,
                 HScrollBarClass=tk.Scrollbar, VScrollBarClass=tk.Scrollbar,
                 **kwargs):
        assert isinstance(scroll_speed, int), "`scroll_speed` must be an int"
        self.scroll_speed:int = scroll_speed
        # Create outter frame
        self.outter:tk.Frame = tk.Frame(master, bd=bd, bg=bg,
                                        highlightthickness=highlightthickness)
        self.outter.grid_rowconfigure(1, weight=1)
        self.outter.grid_columnconfigure(1, weight=1)
        # Create canvas
        self.canvas:tk.Canvas = tk.Canvas(self.outter, highlightthickness=0,
                                          bd=0, **kwargs)
        self.canvas.grid(row=1, column=1, sticky="news")
        # Create inner frame and put inside canvas
        self.inner:tk.Frame = tk.Frame(self.canvas, bd=bd, highlightthickness=0)
        self.id:int = self.canvas.create_window((0,0), window=self.inner,
                                                anchor="nw")
        self.inner.grid_columnconfigure(1, weight=1)
        self.inner.grid_rowconfigure(1, weight=1)
        # Put self inside inner frame
        super().__init__(self.inner, bg=bg, bd=0, highlightthickness=0)
        super().grid(row=1, column=1, sticky="news")
        # Create the 2 scrollbars
        self.v_scrollbar = self.h_scrollbar = None
        if vscroll:
            self.v_scrollbar = VScrollBarClass(self.outter,
                                               orient="vertical",
                                               command=self.canvas.yview,
                                               **scrollbar_kwargs)
            self.v_scrollbar.grid(row=1, column=2, sticky="news")
            self.canvas.config(yscrollcommand=self.v_scrollbar.set)
        if hscroll:
            self.h_scrollbar = HScrollBarClass(self.outter,
                                               orient="horizontal",
                                               command=self.canvas.xview,
                                               **scrollbar_kwargs)
            self.h_scrollbar.grid(row=2*(1-hscrolltop), column=1, sticky="news")
            self.canvas.config(xscrollcommand=self.h_scrollbar.set)
        # Bind to the mousewheel scrolling
        make_bind_frame(self.canvas, method="bind_children")
        self.canvas.bind_children("<MouseWheel>", self._scroll_windows,
                                  add=True)
        self.canvas.bind_children("<Button-4>", self._scroll_linux, add=True)
        self.canvas.bind_children("<Button-5>", self._scroll_linux, add=True)
        # Copy all of the geometry manager methods from outter
        for manager in ("pack", "grid", "place"):
            for attr in dir(tk.Frame):
                if manager in attr:
                    setattr(self, attr, getattr(self.outter, attr))
        # Copy xview and yview from canvas
        self.xview = self.canvas.xview
        self.yview = self.canvas.yview
        # Bind so we can resize canvas and inner frame
        super().bind("<Configure>", self._inner_resized, add=True)
        self.canvas.bind("<Configure>", self._outter_resized, add=True)

    def get_x_offset(self) -> tuple[int,int]:
        """
        Returns the real x value of the (0, 0) coordinate.
        """
        low, high = self.canvas.xview()
        x1, _, x2, _ = self.canvas.cget("scrollregion").split(" ")
        x1, x2 = int(x1), int(x2)
        return tuple(int(x1 + (x2-x1)*float(i)) for i in (low,high))

    def get_y_offset(self) -> tuple[int,int]:
        """
        Returns the real y value of the (0, 0) coordinate.
        """
        low, high = self.canvas.yview()
        _, y1, _, y2 = self.canvas.cget("scrollregion").split(" ")
        y1, y2 = int(y1), int(y2)
        return tuple(int(y1 + (y2-y1)*float(i)) for i in (low,high))

    def framex(self, x:int) -> int:
        """
        Same as `tk.Canvas.canvasx(x)` but for this frame.
        """
        return x + self.get_x_offset()[0]

    def framey(self, y:int) -> int:
        """
        Same as `tk.Canvas.canvasy(y)` but for this frame.
        """
        return y + self.get_y_offset()[0]

    def _scroll_windows(self, event:tk.Event) -> None:
        assert event.delta != 0, "On Windows, `event.delta` should never be 0"
        steps = int(-event.delta/abs(event.delta)*self.scroll_speed)
        if event.state&1:
            self.canvas.xview_scroll(steps, "units")
        else:
            self.canvas.yview_scroll(steps, "units")

    def _scroll_linux(self, event:tk.Event) -> None:
        steps:int = self.scroll_speed
        if event.num == 4:
            steps *= -1
        if event.state&1:
            self.canvas.xview_scroll(steps, "units")
        else:
            self.canvas.yview_scroll(steps, "units")

    def _check_mouse_over_self(self, event:tk.Event) -> bool:
        # Unused - depricated
        return str(event.widget).startswith(str(self.outter))

    def _inner_resized(self, _:tk.Event=None) -> None:
        region = list(self.canvas.bbox("all"))
        region[2] = max(self.canvas.winfo_width(), region[2])
        region[3] = max(self.canvas.winfo_height(), region[3])
        self.canvas.config(scrollregion=region)
        mod:dict = dict()
        if self.h_scrollbar is None:
            width:int = super().winfo_reqwidth()
            cwidth:int = self.canvas.winfo_width()
            if cwidth != width:
                mod["width"] = width
        if self.v_scrollbar is None:
            height:int = super().winfo_reqheight()
            cheight:int = self.canvas.winfo_height()
            if cheight != height:
                mod["height"] = height
        if mod:
            self.canvas.config(**mod)

    def _outter_resized(self, _:tk.Event=None) -> None:
        super().update_idletasks()
        mod:dict = dict()
        width:int = super().winfo_reqwidth()
        height:int = super().winfo_reqheight()
        cwidth:int = self.canvas.winfo_width()
        cheight:int = self.canvas.winfo_height()

        if self.h_scrollbar is None:
            if width != cwidth:
                mod["width"] = cwidth
        elif width < cwidth:
            self.inner.grid_columnconfigure(1, minsize=cwidth)

        if self.v_scrollbar is None:
            if height != cheight:
                mod["height"] = cheight
        elif height < cheight:
            self.inner.grid_rowconfigure(1, minsize=cheight)

        if mod:
            self.canvas.itemconfigure(self.id, **mod)

    def bind(self, sequence:str, callback:Callable[tk.Event,str|None],
             add:bool=None) -> tuple[str,str,str]:
        b1:str = self.outter.bind(sequence, callback, add=add)
        b2:str = self.canvas.bind(sequence, callback, add=add)
        b3:str = super().bind(sequence, callback, add=add)
        return b1, b2, b3


# Example 1
if __name__ == "__main__":
    root = tk.Tk()
    frame = BetterFrame(root, width=300, height=200, hscroll=True, vscroll=True)
    frame.pack(fill="both", expand=True)

    for i in range(51):
        tk.Label(frame, text=i, anchor="w").grid(row=i, column=i)

    root.mainloop()


# Example 2
if __name__ == "__main__":
    root = tk.Tk()

    frame = BetterFrame(root, height=200, hscroll=False, vscroll=True)
    frame.pack(fill="both", expand=True)

    def add():
        for i in range(5):
            label = tk.Label(frame, text=f"Label number {i}", bg="cyan")
            label.pack(anchor="w", fill="x")
    tk.Button(frame, text="Add widgets", command=add).pack(fill="x")
    frame.config(bg="cyan")

    root.mainloop()