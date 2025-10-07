from __future__ import annotations
from idlelib.percolator import Percolator
from idlelib.delegator import Delegator
import tkinter as tk


DEBUG_SEE:bool = False


class DLineInfoWrapper:
    """
    Text.dlineinfo only works if the line is visible:
    > If the display line containing index is not visible on the screen
    > then the return value is an empty list.
    >   From https://www.tcl.tk/man/tcl8.4/TkCmd/text.htm#M81
    This class fixes that by forcing Text.see on each line before calling
    dlineinfo
    """
    __slots__ = "text", "xview", "yview", "_inside", "_assume_monospaced", \
                "_monospaced_size", "_shown_monospace_err"

    def __init__(self, text:tk.Text) -> DLineInfo:
        self._shown_monospace_err:bool = False
        self._assume_monospaced:bool = False
        self._monospaced_size:int = 0
        self._inside:bool = False
        self.text:tk.Text = text

    def __enter__(self) -> DLineInfo:
        self._inside:bool = True
        if not self._assume_monospaced:
            self.xview:str = self.text.xview()[0]
            self.yview:str = self.text.yview()[0]
        return self

    def __exit__(self, exc_t:type, exc_val:BaseException, tb:Traceback) -> bool:
        self._inside:bool = False
        if not self._assume_monospaced:
            self.text.xview("moveto", self.xview)
            self.text.yview("moveto", self.yview)
        return False

    def get_width(self, line:int) -> int:
        assert self._inside, "You can only call this if inside the context"
        tkline:str = f"{line+1}.0" # lines in tkinter start from 1
        if self._monospaced_size != 0:
            width:int = self._monospaced_get_width(tkline)
            if width != -1: # if there's a tab in the input, fail gracefully
                return width
        self.text.see(tkline, no_xscroll=True)
        dlineinfo:tuple[int] = self.text.dlineinfo(tkline)
        if dlineinfo is None:
            return 0
        width:int = dlineinfo[2]
        if self._assume_monospaced:
            chars:str = self.text.get(tkline, f"{tkline} lineend")
            if chars and ("\t" not in chars): # if tab/s, don't store value
                size:float = width/len(chars)
                if (int(size) != size) and (not self._shown_monospace_err):
                    self._shown_monospace_err:bool = True
                    raise RuntimeError("Not a monospaced font but you called " \
                                       ".assume_monospaced()")
                self._monospaced_size:int = int(size)
        return width

    def _monospaced_get_width(self, tkline:str) -> int:
        """
        If we are using monospaced font and we already know it's size
          just calculate the line length in python instead of
          using Text.xview, Text.yview, Text.see, and Text.dlineinfo
          which sometimes cause flickering and is super slow
        Fails and returns -1 if there is a tab in the input.
        """
        chars:str = self.text.get(tkline, f"{tkline} lineend")
        if "\t" in chars: # force fail on tabs
            return -1
        return len(chars) * self._monospaced_size

    def assume_monospaced(self) -> None:
        """
        Assumes the whole text is monospaced and only calls `Text.dlineinfo`
        once. The rest of the time, it only calls `Text.get`
        WARNING: Nothing really checks this assumption so it's the caller's
                 responsibility to make sure it's correct.
        """
        assert not self._inside, "Don't call this from inside the context"
        self._assume_monospaced:bool = True

    def unknown_if_monospaced() -> None:
        assert not self._inside, "Don't call this from inside the context"
        self._assume_monospaced:bool = False
        self._monospaced_size:int = 0


# Not faster than the python code above but I had to check
TCL_CODE:str = """
proc dline_all {w} {
    update idletasks
    set cur_xview [lindex [$w xview] 0]
    set cur_yview [lindex [$w yview] 0]
    scan [$w index "end"] %f end
    set output {}
    set i 1
    while {$i < $end} {
        set index [format "%d.0" $i]
        $w see $index
        lappend output [lindex [$w dlineinfo $index] 2]
        incr i
    }
    $w xview moveto $cur_xview
    $w yview moveto $cur_yview
    return $output
}
"""


# XViewFix
"""
def get_methods(Class:type) -> set:
    return set(getattr(Class, m) for m in dir(Class) if not m.startswith("_"))

managers = get_methods(tk.Pack) | get_methods(tk.Place) | get_methods(tk.Grid)
methods = set(m for m in get_methods(tk.Text) & managers)
INHERIT_FROM_CANVAS = []
for n in dir(tk.Text):
    if (not n.startswith("_")) and (getattr(tk.Text, n) in methods):
        INHERIT_FROM_CANVAS.append(n)
"""
INHERIT_FROM_CANVAS:tuple[str] = (
            "columnconfigure", "forget", "grid", "grid_bbox",
            "grid_columnconfigure", "grid_configure", "grid_forget",
            "grid_info", "grid_location", "grid_propagate", "grid_remove",
            "grid_rowconfigure", "grid_size", "grid_slaves", "info",
            "location", "pack", "pack_configure", "pack_forget", "pack_info",
            "pack_propagate", "pack_slaves", "place", "place_configure",
            "place_forget", "place_info", "place_slaves", "propagate",
            "rowconfigure", "size", "slaves"
                                 )
SCROLL_SPEED:int = 12 # In pixels (probably should be an attribute)


class XViewFix(Delegator):
    def __init__(self, text:tk.Text) -> XViewFix:
        self.dlineinfo:DLineInfoWrapper = DLineInfoWrapper(text)
        self.line_lengths:list[int] = [0]
        self.dirty:set[int] = set()
        self.text:tk.Text = text
        super().__init__()

    def fix_dirty(self) -> None:
        try:
            with self.dlineinfo:
                for line in self.dirty:
                    length:int = self.dlineinfo.get_width(line=line)
                    self.line_lengths[line] = length
                self.dirty.clear()
        except RuntimeError as err:
            if hasattr(self.text, "report_full_exception"):
                self.text.report_full_exception(err)
            else:
                self.text._report_exception()

    def lines_dirtied(self, idxa:str, idxb:str) -> None:
        # tkinter lines start from 1 and not 0
        linea:int = int(idxa.split(".")[0]) - 1
        lineb:int = int(idxb.split(".")[0]) - 1
        for line in range(linea, lineb+1):
            self.dirty.add(line)

    # On insert/delete (called even from inside control-z)
    def insert(self, index:str, chars:str, tags:tuple[str]|str=None) -> None:
        self.delegate.event_generate("<<XViewFix-Before-Insert>>")
        self._on_before_insert(index, chars)
        self.delegate.insert(index, chars, tags)
        self.fix_dirty()
        self.delegate.event_generate("<<XViewFix-After-Insert>>")

    def delete(self, index1:str, index2:str|None=None) -> None:
        self.delegate.event_generate("<<XViewFix-Before-Delete>>")
        self._on_before_delete(index1, index2)
        self.delegate.delete(index1, index2)
        self.fix_dirty()
        self.delegate.event_generate("<<XViewFix-After-Delete>>")

    # Add lines to dirty when the text is modified
    def _on_before_insert(self, idx:str, chars:str) -> None:
        idx:str = self.text.index(idx)
        if self.text.compare(idx, "==", "end"):
            idx:str = self.text.index("end -1c")
        linestart:int = int(idx.split(".")[0]) - 1 # list idxs not text idxs
        self.dirty.add(linestart)
        for line in range(linestart+1, linestart+chars.count("\n")+1):
            self.line_lengths.insert(line, -1)
            self.dirty.add(line)

    def _on_before_delete(self, idxa:str, idxb:str) -> None:
        if idxb is None:
            idxa:str = self.text.index(f"{idxa} +1c")
            if idxa == "": return None
            linea, chara = idxa.split(".")
            linea:int = int(linea)
            if chara == "0":
                self.dirty.add(linea-2)
                self.line_lengths.pop(linea-1)
            else:
                self.dirty.add(linea-1)
        else:
            idxa:str = self.text.index(idxa)
            idxb:str = self.text.index(idxb)
            if not (idxa and idxb): return None
            if self.text.compare(idxb, "==", "end"):
                idxb:str = self.text.index("end -1c")
            low:int = int(idxa.split(".")[0])
            high:int = int(idxb.split(".")[0])
            self.dirty.add(low-1)
            for _ in range(low, high):
                self.line_lengths.pop(low)


# This is an ok solution to https://stackoverflow.com/q/35412972/11106801
#   which barely works. It calls dlineinfo on each line to figure out the
#   width of all of the lines which it caches and updates only when
#   necessary It can go through around 4.6k lines (tkinter/__init__.py from
#   cpython) in 0.43 sec (without assuming monospaced font)
class BetterText(tk.Text):
    def __init__(self, master:tk.Misc=None, **kwargs:dict) -> BetterText:
        self._xscrollcmd:Callable = lambda *args: None
        self._disabled:bool = True # Set to false at the end of __init__
        self._xoffset:int = 0
        self._canvasx:int = 0
        bg:str = kwargs.pop("background", kwargs.pop("bg", "white"))
        # Deal with kwargs
        self._width:int = kwargs.pop("width", 646)
        self._height:int = kwargs.pop("height", 646)
        self._fix_kwargs(kwargs)
        # Canvas
        self._canvas:tk.Canvas = tk.Canvas(master, bd=0, highlightthickness=0,
                                           bg=bg, width=self._width,
                                           height=self._height, cursor="xterm")
        self._canvas.bind("<Configure>", self._on_resize)
        # Frame (to allow text to be resized in pixels)
        self._frame = tk.Frame(self._canvas, highlightthickness=0, bd=0)
        self._frame.pack_propagate(False)
        # Text
        super().__init__(self._frame, bd=0, highlightthickness=0, wrap="none",
                         xscrollcommand=self._on_xscroll_cmd, padx=0, pady=0,
                         **kwargs)
        super().pack(fill="both", expand=True)
        self._canvas.create_window((0,0), anchor="nw", window=self._frame,
                                   tags=("text",))
        # Copy some methods from canvas
        for method in INHERIT_FROM_CANVAS:
            setattr(self, method, getattr(self._canvas, method))
        # Add XViewFix
        self._xviewfix:XViewFix = XViewFix(self)
        self.percolator:Percolator = Percolator(self)
        self.percolator.insertfilter(self._xviewfix)
        # Bind scrolling
        super().bind("<MouseWheel>", self._scroll_windows)
        super().bind("<Button-4>", self._scroll_linux)
        super().bind("<Button-5>", self._scroll_linux)
        # Redirect some methods to text
        self._canvas.bind("<MouseWheel>", self._scroll_windows)
        self._canvas.bind("<Button-4>", self._scroll_linux)
        self._canvas.bind("<Button-5>", self._scroll_linux)
        self._canvas.bind("<B1-Motion>", self._redirect_event)
        self._canvas.bind("<ButtonPress-1>", self._redirect_event)
        self._canvas.bind("<ButtonRelease-1>", self._redirect_event)
        self._canvas.bind("<Double-Button-1>", self._redirect_event)
        self._canvas.bind("<Triple-Button-1>", self._redirect_event)
        # Enable self
        self._disabled:bool = False
        # Re-parent self so that master is our self.master instead of inner
        self.master:tk.Misc = master

    # Events redirector
    def _redirect_event(self, event:tk.Event) -> None:
        """
        Redirects mouse events from the canvas into the text box.
        """
        name:str = getattr(event.type, "name", event.type)
        kwargs:dict = dict(x=self._width-2, y=event.y, state=event.state)
        if isinstance(event.num, int):
            kwargs["button"] = event.num
        super().event_generate(f"<{name}>", **kwargs)

    # On canvas resize
    def _on_resize(self, event:tk.Event) -> None:
        """
        Whenever the dummy canvas is resized, cache the new size
        and resize the text widget to the same size
        """
        self._width, self._height = event.width, event.height
        self._frame.config(width=self._width, height=self._height)
        if not self._disabled:
            self._update_viewport(xoffset=self._xoffset)

    # kwargs fixer
    def _fix_kwargs(self, kwargs:dict) -> dict:
        """
        Intercept changes to wrap and make sure they are "none"
        Intercept changes to xscrollcommand and keep a reference to the
          function so we can call it later
        Intercept changes to background/cursor and apply them to the
          canvas as well
        """
        def wrap_xscrollcmd(func:Callable|None) -> Callable:
            if not func:
                return lambda *args: None
            def inner(low:str, high:str) -> None:
                try:
                    return func(low, high)
                except tk.TclError:
                    pass
            return inner

        if len(kwargs) == 0:
            return super().config()
        if not self._disabled:
            assert kwargs.pop("wrap", "none") == "none", "wrap must be none"
        assert not kwargs.pop("border", 0), "border must be 0"
        # https://stackoverflow.com/q/78802587/11106801
        assert not kwargs.pop("padx", 0), "padx must be 0"
        assert not kwargs.pop("pady", 0), "pady must be 0"
        assert not kwargs.pop("bd", 0), "border must be 0"
        assert not kwargs.pop("highlightthickness", 0), \
                                             "highlightthickness must be 0"
        if "bg" in kwargs:
            self._canvas.config(bg=kwargs["bg"])
        if "cursor" in kwargs:
            self._canvas.config(cursor=kwargs["cursor"])
        if "xscrollcommand" in kwargs:
            self._xscrollcmd = wrap_xscrollcmd(kwargs.pop("xscrollcommand"))
        if self._xscrollcmd and (not self._disabled):
            self._update_viewport(xoffset=self._xoffset)
        return kwargs

    # Destroy
    def destroy(self) -> None:
        """
        We have to override this function since canvas is the widget that
          is inside the master passed in in __init__.
        """
        self._frame.children.pop(self._name, None)
        self._canvas.destroy()
        super().destroy()

    # Enable/Disable
    def enable(self) -> None:
        """
        Enables BetterText so it acts like a fixed tk.Text
        """
        self._disabled:bool = False
        self._update_viewport(low=0.0)
        wrap:str = self.cget("wrap")
        assert wrap == "none", "Disable wrap when enabling BetterText"

    def disable(self) -> None:
        """
        Disables BetterText so it acts like a normal tk.Text
        """
        self._canvas.moveto("text", 0)
        self._disabled:bool = True

    def assume_monospaced(self) -> None:
        self._xviewfix.dlineinfo.assume_monospaced()

    def unknown_if_monospaced(self) -> None:
        self._xviewfix.dlineinfo.unknown_if_monospaced()

    # config/configure/cget
    def config(self, **kwargs:dict) -> dict|None:
        """
        Overwrite this method with our own where we can intercept some
          arguments. For more info look at `_fix_kwargs`
        """
        return super().config(**self._fix_kwargs(kwargs))
    configure = config

    def cget(self, key:str) -> object:
        if key == "xscrollcommand":
            return self._xscrollcmd
        return super().cget(key)

    # Scrolling
    def _scroll_linux(self, event:tk.Event) -> str:
        steps:int = SCROLL_SPEED * (1-(event.num == 4)*2)
        return self._scroll_event(steps, event)

    def _scroll_windows(self, event:tk.Event) -> str:
        assert event.delta != 0, "On Windows, `event.delta` should never be 0"
        steps:int = int(-event.delta/abs(event.delta)*SCROLL_SPEED+0.5)
        return self._scroll_event(steps, event)

    def _scroll_event(self, steps:int, event:tk.Event) -> str:
        """
        If we get a scrolling event event:
         -------- --------------------- -----------------------
        |        |     Horizontal      |       Vertical        |
         -------- --------------------- -----------------------
        | Canvas | self._scroll(steps) | Send to Text widget   |
        | Text   | self._scroll(steps) | Allow to pass through |
         -------- --------------------- -----------------------
        """
        if event.widget not in (self, self._canvas):
            return ""
        if not (event.state&1):
            if event.widget == self._canvas:
                super().event_generate(f"<Button-{event.num}>")
            return ""
        self._scroll(steps)
        return "break"

    def _scroll(self, steps:int) -> None:
        """
        Calculate the new xoffset and call `update_viewport`.
        """
        if self._disabled:
            return None
        new_xoffset:int = self._xoffset + steps
        max_xoffset:int = max(self._xviewfix.line_lengths) - self._width
        xoffset:int = min(max_xoffset, max(0, new_xoffset))
        if xoffset != self._xoffset:
            self._update_viewport(xoffset=xoffset)

    def _on_xscroll_cmd(self, low:str, high:str) -> None:
        """
        If the text widget tries to scroll, do complicated maths
        """
        if self._disabled:
            self.cget("xscrollcommand")(str(low), str(high))
        else:
            low, high = float(low), float(high)
            max_line_width:int = self._get_longest_visible_line_length()
            new_xoffset:int = low * max_line_width
            if new_xoffset != self._xoffset:
                self._update_viewport(xoffset=new_xoffset)

    # Helpers/xview
    def _get_longest_visible_line_length(self) -> int:
        """
        Gets the length of the longest visible line on the screen in pixels
        """
        xview:tuple[str,str]|None = super().xview()
        if xview is None: return -1
        low, high = xview
        low, high = float(low), float(high)
        return int(self._width/(high-low) + 0.5)

    def textx(self, x:int, real:bool=True) -> int:
        """
        Converts text viewbox x coordinate into the real x coordinate.
        This is probably a value that tcl internally stores but doesn't
          expose so we have to calculate it based on the fractions from
          `Text.xview`
        """
        xview:tuple[str]|None = super().xview()
        if not xview: return x
        low, _ = super().xview()
        # Use the first fraction from `xview()` to calculate the base x offset
        #   of the viewport
        max_line_width:int = self._get_longest_visible_line_length()
        return int(max_line_width*float(low)+0.5) + x - self._canvasx*real

    def fixed_xview(self) -> tuple[str,str]:
        """
        This acts like tkinter.Text.xview with 0 arguments if the text
          widget was large enough (vertically) to show all of the lines
        """
        # Get base x offset of the viewport and the max line length
        if self._disabled:
            return super().xview()
        max_line_width:int = max(self._xviewfix.line_lengths)
        if max_line_width == 0:
            # error: max(self._xviewfix.line_lengths)=0"
            return ("0.0", "1.0")
        # Use the 2 values to calculate the new (low,high) values
        #   that we can pass through to the xscrollcommand
        low:float  = self._xoffset/max_line_width
        high:float =  self._width/max_line_width + low
        return str(low), str(min(high,1.0))

    def xview(self, *args:tuple) -> tuple[str]|None:
        """
        Redo everything inside xview from scratch because that is the main
          issue. This was a pain...
        Note: 'xview scroll XXX units' not allowed because I can't be bothered
              to compute the size of units
        """
        if self._disabled:
            return super().xview(*args)
        if len(args) == 0:
            return self.fixed_xview()
        if args[0] == "moveto":
            assert len(args) == 2, "xview moveto expects 1 extra argument"
            try:
                low:float = max(0.0, float(args[1]))
            except ValueError:
                raise ValueError(f"'xview moveto' expects a float not " \
                                 f"{args[1]!r}")
            self._update_viewport(low=low)
            return None
        if args[0] == "scroll":
            if len(args) == 2:
                args:tuple = (*args, "pixels")
            assert len(args) == 3, "'xview scroll' expects 1/2 extra arguments"
            _, size, what = args
            try:
                size:float = float(size)
            except ValueError:
                raise ValueError(f"'xview scroll' expects an int/float")
            if what == "pixels":
                self._scroll(int(size+0.5))
            elif what == "units":
                raise ValueError("'xview scroll XXX units' not implemented yet")
            elif what == "pages":
                self._scroll(int(size*self._width+0.5))
            else:
                raise ValueError(f"Unknown unit {what!r} in 'xview scroll'")
            return None
        raise NotImplementedError(f"Implement {args!r}")

    # See
    def see(self, idx:str, *, no_xscroll:bool=False) -> None:
        """
        This acts like `tkinter.Text.see` with a hidden `no_xscroll`
          parameter only used in `DLineInfoWrapper.get_width`
        """
        if no_xscroll or self._disabled:
            return super().see(idx)
        idx:str = super().index(idx)
        # Threshold for long (target far away) vs shot (target close) scroll
        threshold:float = 0.346*self._width + 13.34
        cur_xoffset:int = self._xoffset
        if super().compare(f"{idx} linestart", "==", idx):
            tar_xoffset:int = 0
        else:
            tar_xoffset:int = super().count(f"{idx} linestart", idx,
                                            f"xpixels")[0]
        # Calculate if target is already horizontally in the viewport
        #   or we need to make a short/long horizontal jump
        diff:int = tar_xoffset - cur_xoffset
        if DEBUG_SEE: print(f"{diff=}, {cur_xoffset=}, {tar_xoffset=}")
        if 0 <= diff <= self._width: # Do not modify this line (causes jitter)
            # Target already horizontally visible
            if DEBUG_SEE: print("Target already horizontally visible")
            super().yview_pickplace(idx) # Vertical scroll
            return None
        elif -threshold < diff < self._width+threshold:
            # Scroll (near) so that idx is at the edge of the text box
            if DEBUG_SEE: print("Scroll near")
            new_xoffset:int = tar_xoffset
            new_xoffset -= (self._width-3) * (diff>0) # cursor.width ≈ -3
        else:
            # Scroll (far) so that idx is at the middle of the text box
            if DEBUG_SEE: print("Scroll long")
            new_xoffset:int = tar_xoffset - self._width//2
        # Actual horizontal scroll
        longest_line_length:int = max(self._xviewfix.line_lengths)
        max_xoffset:int = longest_line_length - self._width
        new_xoffset:int = min(max_xoffset, max(0, new_xoffset))
        if cur_xoffset != new_xoffset:
            self._update_viewport(xoffset=new_xoffset)
        # Vertical scroll
        super().yview_pickplace(idx)

    def _update_viewport(self, low:float=None, xoffset:int=None) -> None:
        """
        Scroll horizontally to match either the passed in low or xoffset
        """
        assert not self._disabled, "This shouldn't be called if disabled"
        super().update_idletasks()
        longest_line_length:int = max(self._xviewfix.line_lengths)
        longest_line_length:int = max(longest_line_length, self._width)
        low_high_diff:float = self._width/longest_line_length
        max_low:float = 1 - low_high_diff
        if xoffset is None:
            assert low is not None, "pass in either low or xoffset not both"
            low:float = max(0.0, min(max_low, low))
            self._xoffset:int = int(low*longest_line_length + 0.5)
        elif low is None:
            max_xoffset:int = longest_line_length - self._width
            self._xoffset = min(max_xoffset, max(0, xoffset))
            low:float = max(0.0, min(max_low,
                                     self._xoffset/longest_line_length))
        else:
            raise RuntimeError("pass in either low or xoffset")
        high:float = min(1.0, max(0.0, low+low_high_diff))

        # Set xview
        longest_visible_width:int = self._get_longest_visible_line_length()
        longest_visible_width:int = max(1, longest_visible_width)
        max_vis_low:float = 1 - self._width/longest_visible_width
        vis_low:float = min(max_vis_low, self._xoffset / longest_visible_width)
        super().xview("moveto", str(vis_low))

        # Get current xoffset that's in implemented in the tk.Text internally
        curr_text_xoffset:int = self.textx(0, real=False)
        self._canvasx:int = min(0, curr_text_xoffset-self._xoffset)
        self._canvas.moveto("text", max(-self._width,self._canvasx))
        # print(f"{self._xoffset=}, {low=:.2f}, {high=:.2f} {curr_xoffset=}")
        self.cget("xscrollcommand")(str(low), str(high))


if __name__ == "__main__":
    from os.path import dirname, join
    from time import perf_counter

    from betterscrollbar import BetterScrollBarHorizontal

    start:float = perf_counter()
    root:tk.Tk = tk.Tk()

    text:BetterText = BetterText(root, width=400, height=200, undo=True)
    text.mark_set("insert", "1.0")
    text.pack(fill="both", expand=True)
    text.config(font=("DejaVu Sans Mono", 9, "normal", "roman"))
    text.assume_monospaced()

    filepath:str = tk.__file__
    # filepath:str = join(dirname(dirname(dirname(__file__))), "bad.py")
    with open(filepath, "r") as file:
        text.insert("end", file.read())

    evs:tuple[str] = ("<<XViewFix-Before-Insert>>", "<<XViewFix-After-Insert>>",
                      "<<XViewFix-After-Delete>>", "<Left>", "<Right>", "<Up>",
                      "<Down>", "<KeyRelease-Left>", "<KeyRelease-Right>",
                      "<KeyRelease-Up>", "<KeyRelease-Down>")
    for ev in evs:
        text.bind(ev, lambda e: text.see("insert"))

    # hbar = tk.Scrollbar(root, orient="horizontal", command=text.xview)
    hbar = BetterScrollBarHorizontal(root, command=text.xview)
    text.config(xscrollcommand=hbar.set)
    hbar.pack(fill="x")

    def label_loop() -> None:
        # For debugging
        low, high = text.fixed_xview()
        msg:str = f"BetterText({float(low):.3f}, {float(high):.3f}) "
        low, high = tk.Text.xview(text)
        msg += f"Text({float(low):.3f}, {float(high):.3f})"
        label.config(text=msg)
        label.after(100, label_loop)

    label:tk.Label = tk.Label(root)
    label.pack()
    label_loop()

    print(f"Took {perf_counter()-start:.2f} sec")
    root.mainloop()