from __future__ import annotations
from idlelib.percolator import Percolator
from idlelib.delegator import Delegator
import tkinter as tk


DEBUG_SEE:bool = False
DEBUG_BG_TAG:bool = False


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

    def get_width(self, line:int, char:str="0") -> int:
        assert self._inside, "You can only call this if inside the context"
        line += 1 # lines in tkinter start from 1
        if self._monospaced_size != 0:
            width:int = self._monospaced_get_width(line)
            if width != -1: # if there's a tab in the input, fail gracefully
                return width
        self.text.see(f"{line}.{char}", no_xscroll=True)
        dlineinfo:tuple[int] = self.text.dlineinfo(f"{line}.0")
        if dlineinfo is None:
            return 0
        width:int = dlineinfo[2]
        if self._assume_monospaced:
            chars:str = self.text.get(f"{line}.0", f"{line}.0 lineend")
            if chars and ("\t" not in chars): # if tab/s, don't store value
                size:float = width/len(chars)
                if (int(size) != size) and (not self._shown_monospace_err):
                    self._shown_monospace_err:bool = True
                    raise RuntimeError("Not a monospaced font but you called " \
                                       ".assume_monospaced()")
                self._monospaced_size:int = int(size)
        return width

    def _monospaced_get_width(self, line:int) -> int:
        """
        If we are using monospaced font and we already know it's size
          just calculate the line length in python instead of
          using Text.xview, Text.yview, Text.see, and Text.dlineinfo
          which sometimes cause flickering and is super slow
        Fails and returns -1 if there is a tab in the input.
        """
        chars:str = self.text.get(f"{line}.0", f"{line}.0 lineend")
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

    def fix_dirty(self, char:str="0") -> None:
        with self.dlineinfo:
            for line in self.dirty:
                self.line_lengths[line] = self.dlineinfo.get_width(line=line,
                                                                   char=char)
            self.dirty.clear()

    def lines_dirtied(self, idxa:str, idxb:str) -> None:
        linea:int = int(idxa.split(".")[0])
        lineb:int = int(idxb.split(".")[0])
        for line in range(linea, lineb+1):
            self.dirty.add(line-1)

    # On insert/delete (called even from inside control-z)
    def insert(self, index:str, chars:str, tags:tuple[str]|str=None) -> None:
        char:str = self.delegate.index(index).split(".")[1]
        self.delegate.event_generate("<<XViewFix-Before-Insert>>")
        self._on_before_insert(index, chars)
        self.delegate.insert(index, chars, tags)
        try:
            self.fix_dirty(char=char)
        except RuntimeError as err:
            if hasattr(tk, "report_full_exception"):
                tk.report_full_exception(self.text, err)
            else:
                self.text._report_exception()
        self.delegate.event_generate("<<XViewFix-After-Insert>>")

    def delete(self, index1:str, index2:str|None=None) -> None:
        char:str = self.delegate.index(index1).split(".")[1]
        self.delegate.event_generate("<<XViewFix-Before-Delete>>")
        self._on_before_delete(index1, index2)
        self.delegate.delete(index1, index2)
        self.fix_dirty(char=char)
        self.delegate.event_generate("<<XViewFix-After-Delete>>")

    # Add lines to dirty when the text is modified
    def _on_before_insert(self, idx:str, chars:str) -> None:
        idx:str = self.text.index(idx)
        if self.text.compare(idx, "==", "end"):
            idx:str = self.text.index("end -1c")
        linestart:int = int(idx.split(".")[0])-1 # list idxs not text idxs
        self.dirty.add(linestart)
        for i in range(chars.count("\n")):
            line:int = linestart + i + 1 # list idxs not text idxs
            self.line_lengths.insert(line, -1)
            self.dirty.add(line)

    def _on_before_delete(self, idxa:str, idxb:str) -> None:
        if idxb is None:
            idxa:str = self.text.index(f"{idxa} +1c")
            if idxa == "":
                return None
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
            if (not idxa) or (not idxb):
                return None
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
        self._tags_with_bg:dict[str:str] = {"sel":"#c3c3c3"}
        self._tags_with_font:set[str] = set()
        self.ignore_tags_with_bg:bool = False
        self._lock_tags_with_bg:bool = False
        self._disabled:bool = False
        self._xscrollcmd = None
        self._xoffset:int = 0
        self._canvasx:int = 0
        bg:str = kwargs.pop("background", kwargs.pop("bg", "white"))
        self._fix_kwargs(kwargs)

        self._width:int = kwargs.pop("width", 646)
        self._height:int = kwargs.pop("height", 646)
        self._canvas:tk.Canvas = tk.Canvas(master, bd=0, highlightthickness=0,
                                           bg=bg, width=self._width,
                                           height=self._height, cursor="xterm")
        self._frame = tk.Frame(self._canvas, highlightthickness=0, bd=0)
        self._frame.pack_propagate(False)
        # https://stackoverflow.com/q/78802587/11106801
        super().__init__(self._frame, bd=0, highlightthickness=0, wrap="none",
                         xscrollcommand=self._on_xscroll_cmd, padx=0, pady=0,
                         **kwargs)
        self._tags_with_bg["sel"] = super().tag_cget("sel", "background")
        super().pack(fill="both", expand=True)
        self._canvas.create_window((0,0), anchor="nw", window=self._frame,
                                   tags=("text",))
        self._canvas.bind("<Configure>", self._on_resize)

        for method in INHERIT_FROM_CANVAS:
            setattr(self, method, getattr(self._canvas, method))

        self._xviewfix:XViewFix = XViewFix(self)
        self.percolator:Percolator = Percolator(self)
        self.percolator.insertfilter(self._xviewfix)

        super().bind("<MouseWheel>", self._scroll_windows)
        super().bind("<Button-4>", self._scroll_linux)
        super().bind("<Button-5>", self._scroll_linux)
        super().bind("<B1-Motion>", self._redraw_sel_bg)
        super().bind("<ButtonPress-1>", self._redraw_sel_bg)
        super().bind("<ButtonRelease-1>", self._redraw_sel_bg)

        self._canvas.bind("<MouseWheel>", self._scroll_windows)
        self._canvas.bind("<Button-4>", self._scroll_linux)
        self._canvas.bind("<Button-5>", self._scroll_linux)
        self._canvas.bind("<B1-Motion>", self._redirect_event)
        self._canvas.bind("<ButtonPress-1>", self._redirect_event)
        self._canvas.bind("<ButtonRelease-1>", self._redirect_event)
        self._canvas.bind("<Double-Button-1>", self._redirect_event)
        self._canvas.bind("<Triple-Button-1>", self._redirect_event)

        # self.after(100, lambda: self._update_viewport(xoffset=self._xoffset))

    def disable(self) -> None:
        self._disabled:bool = True

    def enable(self) -> None:
        self._disabled:bool = False
        assert self.cget("wrap") == "none", "Disable wrap when enabling" \
                                            " BetterText"

    def _redraw_sel_bg(self, event:tk.Event=None) -> None:
        """
        Redraw the sel tag on the canvas
        """
        self._redraw_tags_with_bg(tag="sel")

    def _redirect_event(self, event:tk.Event) -> None:
        """
        Redirects mouse events from the canvas into the text box.
        """
        name:str = getattr(event.type, "name", event.type)
        kwargs:dict = dict(x=self._width-2, y=event.y, state=event.state)
        if isinstance(event.num, int):
            kwargs["button"] = event.num
        super().event_generate(f"<{name}>", **kwargs)

    def config(self, **kwargs:dict) -> dict|None:
        """
        Overwrite this method with our own where we can intercept some
          arguments. For more info look at `_fix_kwargs`
        """
        return super().config(**self._fix_kwargs(kwargs))
    configure = config

    def _fix_kwargs(self, kwargs:dict) -> dict:
        """
        Intercept changes to wrap and make sure they are "none"
        Intercept changes to xscrollcommand and keep a reference to the
          function so we can call it later
        Intercept changes to background/cursor and apply them to the
          canvas as well
        """
        if len(kwargs) == 0:
            return super().config()
        if not self._disabled:
            assert kwargs.pop("wrap", "none") == "none", "wrap must be none"
        assert not kwargs.pop("border", 0), "border must be 0"
        assert not kwargs.pop("padx", 0), "padx must be 0"
        assert not kwargs.pop("pady", 0), "pady must be 0"
        assert not kwargs.pop("bd", 0), "border must be 0"
        assert not kwargs.pop("highlightthickness", 0), \
                                             "highlightthickness must be 0"
        if "bg" in kwargs:
            self._canvas.config(bg=kwargs["bg"])
        if "cursor" in kwargs:
            self._canvas.config(cursor=kwargs["cursor"])
        self._xscrollcmd = kwargs.pop("xscrollcommand", self._xscrollcmd)
        if self._xscrollcmd:
            self._update_viewport(xoffset=self._xoffset)
        return kwargs

    def cget(self, key:str) -> object:
        if key == "xscrollcommand":
            return self._xscrollcmd
        return super().cget(key)

    def _on_resize(self, event:tk.Event) -> None:
        """
        Whenever the dummy canvas is resized, cache the new size
        and resize the text widget to the same size
        """
        self._width, self._height = event.width, event.height
        self._frame.config(width=self._width, height=self._height)
        self._update_viewport(xoffset=self._xoffset)

    def _get_longest_visible_line_length(self) -> int:
        """
        Gets the length of the longest visible line on the screen in pixels.
        Used in `BetterText.textx`
        """
        xview:tuple[str,str]|None = super().xview()
        if xview is None:
            return -1
        return int(self._width/(float(xview[1])-float(xview[0]))+0.5)

        # Get the current viewport (y-axis)
        top:str = super().index("@0,0")
        bottom:str = super().index(f"@0,{self._height-1}")
        top, bottom = int(top.split(".")[0]), int(bottom.split(".")[0])
        # Get the max line width out of each of the lines in the viewport
        line_widths:list[int] = self._xviewfix.line_lengths[top-1:bottom]
        if len(line_widths) == 0:
            print("error self._xviewfix.line_lengths[top-1:bottom]=[]", top,
                  bottom, self._xviewfix.line_lengths)
            return -1
        return max(line_widths)

    def textx(self, x:int, real:bool=True) -> int:
        """
        Converts text viewbox x coordinate into the real x coordinate.
        This is probably a value that tcl internally stores but doesn't
        expose so we have to calculate it based on the fractions from
        `Text.xview`
        """
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
            print("error max(self._xviewfix.line_lengths)=0")
            return ("0.0", "1.0")
        # Use the 2 values to calculate the new (low,high) values
        #   that we can pass through to the xscrollcommand
        low:float = self._xoffset/max_line_width
        high:float = (self._xoffset+self._width)/max_line_width
        high:float = min(high, 1.0) # self._width might be > max_line_width
        return str(low), str(high)

    def xview(self, *args:tuple) -> tuple[str]|None:
        """
        Redo everything inside xview from scratch because that is the main
        issue. This was a pain...
        Note: 'xview scroll XXX units' not allowed because I can't be bothered
              to compute the size of units
        """
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
            assert len(args) == 3, \
                            "'xview scroll' expects 1 or 2 extra arguments"
            _, size, what = args
            try:
                size:float = float(size)
            except ValueError:
                raise ValueError(f"'xview scroll' expects an int/float not " \
                                 f"{size!r}")
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

    def _scroll_linux(self, event:tk.Event) -> str:
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
            return None
        if not (event.state&1):
            if event.widget == self._canvas:
                super().event_generate(f"<Button-{event.num}>")
            else:
                super().after(1, self._redraw_tags_with_bg)
            return None
        steps:int = SCROLL_SPEED * (1-(event.num == 4)*2)
        self._lock_tags_with_bg:bool = True
        self._scroll(steps)
        self._lock_tags_with_bg:bool = False
        return "break"

    def _scroll_windows(self, event:tk.Event) -> str:
        """
        Same as `_scroll_linux` but for windows which uses `<MouseWheel>`
        events with `event.delta`
        """
        if event.widget not in (self, self._canvas):
            return None
        if not (event.state&1):
            if event.widget == self._canvas:
                super().event_generate("<MouseWheel>", delta=event.delta)
            else:
                super().after(1, self._redraw_tags_with_bg)
            return None
        assert event.delta != 0, "On Windows, `event.delta` should never be 0"
        steps:int = int(-event.delta/abs(event.delta)*SCROLL_SPEED+0.5)
        self._lock_tags_with_bg:bool = True
        self._scroll(steps)
        self._lock_tags_with_bg:bool = False
        return "break"

    def _scroll(self, steps:int) -> None:
        """
        Calculate the new xoffset and call `update_viewport`.
        """
        if self._disabled:
            xoffset:int = 0
        else:
            xoffset:int = min(max(self._xviewfix.line_lengths)-self._width,
                              max(0, self._xoffset+steps))
        self._update_viewport(xoffset=xoffset)

    def _on_xscroll_cmd(self, low:str, high:str) -> None:
        """
        If the text widget tries to scroll, endo the scrolling and reset
          using `self._xoffset`
        """
        self._update_viewport(xoffset=self._xoffset)

    def see(self, idx:str, *, no_xscroll:bool=False) -> None:
        """
        This took so much time (4h) and I am not 100% sure how/why it works
        but it works :D
        This acts like `tkinter.Text.see` with a hidden `no_xscroll`
          parameter only used in `DLineInfoWrapper.get_width`
        """
        # This is to disable BetterText.see while still allowing
        #   DLineInfoWrapper.get_width to work
        # low, _ = tk.Text.xview(self)
        # super().see(idx)
        # super().after(10, tk.Text.xview, self, "moveto", low)
        # return None

        if no_xscroll:
            return super().see(idx)
        idx:str = super().index(idx)
        threshold:float = 0.346*self._width + 13.34
        cur_xoffset:int = self._xoffset
        if super().compare(f"{idx} linestart", "==", idx):
            tar_xoffset:int = 0
        else:
            xpixels:list[int] = super().count(f"{idx} linestart", idx,
                                              f"xpixels")
            if xpixels is None:
                assert self._disabled, "This should only happen when disabled"
                xpixels:list[int] = [0]
            tar_xoffset:int = xpixels[0]
        diff:int = cur_xoffset - tar_xoffset
        if DEBUG_SEE: print(f"{diff=}, {cur_xoffset=}, {tar_xoffset=}")
        if diff <= 0 <= diff+self._width-3:
            if DEBUG_SEE: print("No need")
            # No need to scroll
            xoffset:int = cur_xoffset
        elif diff-threshold < 0 < diff+self._width+threshold:
            if DEBUG_SEE: print("Scroll near")
            # Scroll (near) so that idx is at the edge of the text box
            xoffset:int = tar_xoffset-1
            xoffset -= (self._width-4)*(diff<0)
        else:
            if DEBUG_SEE: print("Scroll long")
            # Scroll (far) so that idx is at the middle of the text box
            xoffset:int = tar_xoffset - int(self._width/2+0.5)
        if cur_xoffset != xoffset:
            lln:int = max(1, *self._xviewfix.line_lengths)
            xoffset:int = min(lln-self._width, max(0, xoffset))
            self._update_viewport(xoffset=xoffset)

        super().yview_pickplace(idx)

    # Keep track of the tags with background/font
    def tag_config(self, tagname:str, **kwargs) -> None:
        super().tag_config(tagname, **kwargs)
        if kwargs.get("background", None) is not None:
            self._tags_with_bg[tagname] = kwargs.get("background")
            self._redraw_tags_with_bg()
        if kwargs.get("font", None) is not None:
            self._tags_with_font.add(tagname)
            for start, end in super().tag_ranges(tagname):
                self._xviewfix.lines_dirtied(start, end)
            self._xviewfix.fix_dirty()
    tag_configure = tag_config

    def tag_add(self, tagname:str, *idxs:tuple[str]) -> None:
        super().tag_add(tagname, *idxs)
        if len(idxs) == 0:
            raise ValueError("You must specify at least one index with tag_add")
        if len(idxs) == 1:
            idxs:tuple[str] = idxs*2
        assert len(idxs) % 2 == 0, "Indices passed in must be in pairs"
        if tagname in self._tags_with_font:
            for i in range(len(idxs)):
                self._xviewfix.lines_dirtied(*idxs[i:i+2])
            self._xviewfix.fix_dirty()
        if tagname in self._tags_with_bg:
            self._redraw_tags_with_bg()

    def tag_remove(self, tagname:str, idxa:str, idxb:str) -> None:
        super().tag_remove(tagname, idxa, idxb)
        if tagname in self._tags_with_font:
            self._xviewfix.lines_dirtied(idxa, idxb)
            self._xviewfix.fix_dirty()

    def tag_delete(self, *tagnames:tuple[str]) -> None:
        assert len(tagnames) > 0, "You must provide at least one tag name"
        for tagname in tagnames:
            self.tag_remove(tagname, "1.0", "end")
            if tagname in self._tags_with_bg:
                self._tags_with_bg.pop(tagname)
            if tagname in self._tags_with_font:
                self._tags_with_font.remove(tagname)
        super().tag_delete(tagnames)

    def _update_viewport(self, low:float=None, xoffset:int=None) -> None:
        super().update_idletasks()
        lln:int = max(1, *self._xviewfix.line_lengths)
        w_over_f:float = self._width/lln
        if xoffset is None:
            assert low is not None, "pass in either low or xoffset"
            low:float = max(0.0, min(1-w_over_f, low))
            self._xoffset:int = int(low*lln + 0.5)
        elif low is None:
            self._xoffset = min(max(self._xviewfix.line_lengths)-self._width,
                                max(0, xoffset))
            low:float = max(0.0, min(1-w_over_f, self._xoffset/lln))
        else:
            raise RuntimeError("pass in either low or xoffset")
        high:float = min(1.0, max(0.0, low+w_over_f))

        # Set xview
        lvln:int = max(1, self._get_longest_visible_line_length())
        vis_low:float = str(self._xoffset/lvln)
        super().xview("moveto", str(1.0 if high > 0.998 else vis_low))

        # Get the current textx(0)
        curr_xoffset:int = self.textx(0, real=False)
        self._canvasx:int = min(0, curr_xoffset-self._xoffset)
        self._canvas.moveto("text", max(-self._width, self._canvasx))
        # print(f"{self._xoffset=}, {low=:.2f}, {high=:.2f} {curr_xoffset=}")
        if self._canvasx != 0:
            self._redraw_tags_with_bg(update_idletasks=False)
        if self._xscrollcmd is not None:
            if self._disabled:
                low, high = 0.0, 1.0
            self._xscrollcmd(str(low), str(high))

    def _redraw_tags_with_bg(self, update_idletasks:bool=True, tag:str=None):
        if self._lock_tags_with_bg or self.ignore_tags_with_bg:
            return None
        if update_idletasks:
            super().update_idletasks()
        self._canvas.delete("highlights")

        start:str = super().index(f"@0,0")
        end:str = super().index(f"@0,{self._height-1}")
        start, end = int(start.split(".")[0]), int(end.split(".")[0])
        for i in range(start, end+1):
            tags:list[str] = super().tag_names(f"{i}.0 lineend")
            if tag is not None:
                if tag not in tags:
                    continue
                tags:list[str] = [tag]
            for _tag in tags:
                if _tag in self._tags_with_bg:
                    self._draw_tag_bg(_tag, f"{i}.0 lineend")

    def _draw_tag_bg(self, tag:str, idx:str) -> None:
        if DEBUG_BG_TAG: print(f"Draw {tag=} {idx=}")
        dlineinfo:tuple[int]|None = super().dlineinfo(idx)
        if dlineinfo is None:
            return None # Line not visible
        colour:str = self._tags_with_bg[tag]
        _, y0, _, height, _ = dlineinfo
        coords:tuple[int] = (0, y0, self._width, y0+height)
        self._canvas.create_rectangle(*coords, tags=("highlights"),
                                      fill=colour, outline="")


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
    text._xviewfix.dlineinfo.assume_monospaced()

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

    # Note that at the start, it might have a graphical glitch, not my fault
    #   ~~probably~~ maybe
    # text.tag_config("mytag", background="cyan", fg="white")
    # for i in range(0, 155, 4):
    #     text.tag_add("mytag", f"{i+1}.0", f"{i+3}.0")

    hbar = tk.Scrollbar(root, orient="horizontal", command=text.xview)
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