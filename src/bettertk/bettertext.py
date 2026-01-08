from __future__ import annotations
from idlelib.percolator import Percolator
from idlelib.delegator import Delegator
import tkinter as tk


HORIZONTAL_DIRECTION:int = 0b1
DEBUG_INVISIBLE_CHAR:bool = False
DEBUG_ON_XSCROLL_CMD:bool = False
DEBUG_SCROLLBAR:bool = False
DEBUG_VIEWPORT:bool = False
DEBUG_FREEZE:bool = False
DEBUG_SEE:bool = False

"""
0  uses `-lmargin1` on a tag
   maybe turn on `FIX_CURSOR_LPADX` but not performant
1  uses `-padx` on the whole widget
   adds same padding to the right of the widget but
   unnoticeable for padding<5
"""
LEFT_PADX_FIX:int = 1
FIX_CURSOR_LPADX:bool = False


# def print_traceback():
#     import traceback
#     traceback.print_stack()
#     print("="*80)


class DLineInfoWrapper:
    """
    Text.dlineinfo only works if the line is visible:
    > If the display line containing index is not visible on the screen
    > then the return value is an empty list.
    >   From https://www.tcl.tk/man/tcl8.4/TkCmd/text.htm#M81
    This class fixes that by calling `Text.see` on each line before calling
      `dlineinfo`.
    """
    __slots__ = "_text", "_xview", "_yview", "_inside", "_assume_monospaced", \
                "_monospaced_size", "_shown_monospace_err"

    def __init__(self, text:tk.Text) -> DLineInfo:
        self._shown_monospace_err:bool = False
        self._assume_monospaced:bool = False
        self._monospaced_size:int = 0
        self._inside:bool = False
        self._text:tk.Text = text

    def __enter__(self) -> DLineInfo:
        self._inside:bool = True
        if not self._assume_monospaced:
            self._xview:str = self._text.xview()[0]
            self._yview:str = self._text.yview()[0]
        return self

    def __exit__(self, exc_t:type, exc_val:BaseException, tb:Traceback) -> bool:
        self._inside:bool = False
        if not self._assume_monospaced:
            self._text.xview("moveto", self._xview)
            self._text.yview("moveto", self._yview)
        return False

    def get_width(self, line:int) -> int:
        assert self._inside, "You can only call this if inside the context"
        tkline:str = f"{line+1}.0" # lines in tkinter start from 1
        if self._monospaced_size != 0:
            width:int = self._monospaced_get_width(tkline)
            if width != -1: # if there's a tab in the input, fail gracefully
                return width
        if getattr(self._text.see, "__func__", tk.Text.see) == tk.Text.see:
            self._text.see(tkline)
        else:
            self._text.see(tkline, no_xscroll=True)
        dlineinfo:tuple[int] = self._text.dlineinfo(tkline)
        if dlineinfo is None:
            return 0
        width:int = dlineinfo[2]
        if self._assume_monospaced:
            chars:str = self._text.get(tkline, f"{tkline} lineend")
            if chars and ("\t" not in chars): # if tab/s, don't store value
                size:float = width / len(chars)
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
        chars:str = self._text.get(tkline, f"{tkline} lineend")
        if "\t" in chars: # Force fail on tabs
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


GEOMETRY_METHODS:list[str] = [
    "columnconfigure", "forget", "grid", "grid_bbox",
    "grid_columnconfigure", "grid_configure", "grid_forget",
    "grid_info", "grid_location", "grid_propagate", "grid_remove",
    "grid_rowconfigure", "grid_size", "grid_slaves", "info",
    "location", "pack", "pack_configure", "pack_forget", "pack_info",
    "pack_propagate", "pack_slaves", "place", "place_configure",
    "place_forget", "place_info", "place_slaves", "propagate",
    "rowconfigure", "size", "slaves"
]

NOP:Callable = lambda *args: None
BREAK:Callable = lambda *args: "break"

INVISIBLE_CHAR:str = "#" if DEBUG_INVISIBLE_CHAR else "\u200b"
BREAK:object = object()


class BindTkFuncCall(Delegator):
    """
    Examples (on a `tk.Text`):
        percolator.insertfilter(BindTkFuncCall(percolator, "edit undo", ...))
        percolator.insertfilter(BindTkFuncCall(percolator, "edit redo", ...))
        percolator.insertfilter(BindTkFuncCall(percolator, "see", ...))

    on_start return value:
        If `on_start` returns `BREAK`, the widget's function isn't called
        If `on_start` returns non-None, the arguments to the widget's function
        are replaced with the returned tuple
    on_end return value:
        If `on_end` returns anything, it will replace the widget's function
        return value
    func:
        It's a string containing at most 1 space of the tk's widget's command
        that is being bound to

    [Internal Implementation]
    Uses:
        idlelib.redirector@WidgetRedirector
        idlelib.percolator@Percolator
        idlelib.delegator@Delegator
    """
    def __init__(self, perc:Percolator, func:str, *,
                 on_start:Callable[None]=NOP,
                 on_end:Callable[None]=NOP) -> BindTkFuncCall:
        assert isinstance(perc, Percolator), "TypeError"
        assert isinstance(func, str), "TypeError"
        assert func, "func must not be empty"
        super().__init__()
        self._on_start:Callable[None] = on_start
        self._on_end:Callable[None] = on_end
        # Find func/subfunc
        self._funcs:list[str] = func.split(" ")
        base_func:str = self._funcs[0]
        # Redirect `base_func` to `self._call`
        if base_func not in perc.redir._operations:
            call_top:Callable = lambda *a: getattr(perc.top, base_func)(*a)
            orig:Callable = perc.redir.register(base_func, call_top)
            setattr(perc.bottom, base_func, orig)
        setattr(self, base_func, self._call)

    def _call(self, *args:tuple) -> object:
        # Check if `self._funcs` applies
        call:bool = all(a == b for a,b in zip(self._funcs[1:], args))
        # Call on_start
        if call:
            ret_val:object = self._on_start(*args)
            if ret_val is BREAK: return None
            if ret_val is not None:
                assert isinstance(ret_val, tuple), \
                       f"{self._on_start=} should return None, BREAK or a tuple"
                args:tuple = ret_val
        # Call widget's method
        result:object = getattr(self.delegate, self._funcs[0])(*args)
        # Call on_end
        if call:
            on_end_result:object = self._on_end(*args)
            if on_end_result is not None:
                result:object = on_end_result
        # Return result
        return result


class XViewFix(Delegator):
    __slots__ = "line_lengths", "_dlineinfo", "_dirty", "_text"

    def __init__(self, text:tk.Text) -> XViewFix:
        self._dlineinfo:DLineInfoWrapper = DLineInfoWrapper(text)
        self.line_lengths:list[int] = [0]
        self._dirty:set[int] = set()
        self._text:tk.Text = text
        super().__init__()

    def assume_monospaced(self) -> None:
        self._dlineinfo.assume_monospaced()

    def unknown_if_monospaced(self) -> None:
        self._dlineinfo.unknown_if_monospaced()

    def _fix_dirty(self) -> None:
        try:
            with self._dlineinfo:
                for line in self._dirty:
                    length:int = self._dlineinfo.get_width(line=line)
                    self.line_lengths[line] = length
                self._dirty.clear()
        except RuntimeError as err:
            if hasattr(self._text, "report_full_exception"):
                self._text.report_full_exception(err)
            else:
                self._text._report_exception()

    # def lines_dirtied(self, idxa:str, idxb:str) -> None:
    #     linea:int = int(idxa.split(".")[0]) - 1
    #     lineb:int = int(idxb.split(".")[0]) - 1
    #     for line in range(linea, lineb+1):
    #         self._dirty.add(line)

    # On insert/delete (called even from inside control-z)
    def insert(self, index:str, chars:str, tags:tuple[str]|str=None) -> None:
        self.delegate.event_generate("<<XViewFix-Before-Insert>>")
        self._on_before_insert(index, chars)
        if isinstance(tags, str): tags:tuple[str] = (tags,)
        if tags is None: tags:tuple[str] = ()
        self.delegate.insert(index, chars, tuple(tags)+("bettertext_text",))
        self._fix_dirty()
        # `<<XViewFix-After-*>>` events must be fired after `_fix_dirty`
        self.delegate.event_generate("<<XViewFix-After-Insert>>")

    def delete(self, index1:str, index2:str|None=None) -> None:
        self.delegate.event_generate("<<XViewFix-Before-Delete>>")
        self._on_before_delete(index1, index2)
        self.delegate.delete(index1, index2)
        self._fix_dirty()
        # `<<XViewFix-After-*>>` events must be fired after `_fix_dirty`
        self.delegate.event_generate("<<XViewFix-After-Delete>>")

    # Add lines to dirty when the text is modified
    def _on_before_insert(self, idx:str, chars:str) -> None:
        idx:str = self._text.index(idx)
        if self._text.compare(idx, "==", "end"):
            idx:str = self._text.index("end -1c")
        linestart:int = int(idx.split(".")[0]) - 1 # list idxs not text idxs
        self._dirty.add(linestart)
        for line in range(linestart+1, linestart+chars.count("\n")+1):
            self.line_lengths.insert(line, -1)
            self._dirty.add(line)

    def _on_before_delete(self, idxa:str, idxb:str) -> None:
        if idxb is None:
            idxa:str = self._text.index(f"{idxa} +1c")
            if idxa == "": return None
            linea, chara = idxa.split(".")
            linea:int = int(linea)
            if chara == "0":
                self._dirty.add(linea-2)
                self.line_lengths.pop(linea-1)
            else:
                self._dirty.add(linea-1)
        else:
            idxa:str = self._text.index(idxa)
            idxb:str = self._text.index(idxb)
            if not (idxa and idxb): return None
            if self._text.compare(idxb, "==", "end"):
                idxb:str = self._text.index("end -1c")
            low:int = int(idxa.split(".")[0])
            high:int = int(idxb.split(".")[0])
            self._dirty.add(low-1)
            for _ in range(low, high):
                self.line_lengths.pop(low)


assert LEFT_PADX_FIX in (0,1), "Invalid option"
if LEFT_PADX_FIX == 1: FIX_CURSOR_LPADX:bool = False

# On 4.6k lines (cpython's `tkinter/__init__.py`)
#   0.07 sec (assuming monospaced font)
#   0.49 sec (without assuming monospaced font)
class BetterText(tk.Text):
    """
    Description:
        `tk.Text.xview` only reports the fraction of the lines that are
        vertically visible are also horizontally visible. This usually
        isn't what is needed <https://stackoverflow.com/q/35412972/11106801>
        This widget inherits from `tk.Text` and fixes `.xview` so that the
        reported fractions are in terms of all of the lines even the ones
        that aren't visible.
        There is a 0.1 sec slowdown (per 1k lines) if monospaced font
        assumption isn't turned on. This is mostly because there is no
        efficient way of getting the line widths for all of the lines in a
        `tk.Text` widget. Writing a C module that directly interacts with
        the interals of tcl/tk would solve this problem.

    New options:
        padx             The space between the textbox edge and the text.
                           Can be an int or a tuple of 2 ints (in pixels)
        cursor_room      The space left for the cursor at the far left/right.
                           Must be an int (in pixels)
        xscroll_speed    The scroll speed in the horizontal direction
                           Must be an int (in pixels)
        yscroll_speed    The scroll speed in the vvertical direction
                           Must be an int (in pixels)

    Options on __init__ (in pixels):
        width            The width of the widget
                           Must be an int (in pixels)
        height           The height of the widget
                           Must be an int (in pixels)

    Disabled tk.Text options:
        wrap, bd, border, highlightthickness, width, height

    Methods:
        enable() -> None                 Opposite of `disable()`
        disable() -> None                Makes the widget act like a notmal Text
        assume_monospaced() -> None      Assumes monospaced font
        unknown_if_monospaced() -> None  Opposite of `assume_monospaced()`


    [Internal Implementation]
    Attributes:
        _xoffset:int          Must be an int in this range (in pixels):
                                [-self._lpadx, longest_line+self._rpadx]
        _canvasx:int          Always is set to `-_xoffset`
        _width:int            The width of the text box in pixels
        _height:int           The height of the text box in pixels
        _max_range1() -> int  The max value of `_xoffset`
    Explanation:
        We never use the `tk.Text.xview()` and instead we do all of the
        calculations ourselves. To do that we change the `tk.Text`'s `padx`
        option to move the contents to the left (so we can have padding to
        the right/scroll to the right). We also use a `tk.Text` tag called
        "bettertext_text" and it's `lmargin1` option to move the text to
        the right (so we can have padding to the left of the widget).

        We also add a `cursor_room` option that makes moves the text so
        that the cursor is visible even if it's on the edge of the widget

        To do all of this, we re-implemnt all horiontal scrolling from
        scratch by binding to the (tcl/tk) `tk.Text see` command as well
        as overriding the (tkinter) `.see`+`.xview`+`.config` methods.
        Further we have to bind to the (tcl/tk) `tk.Text edit undo` and
        `tk.Text edit redo` commands since they cause a recursion error
        for some reason (still looking into why).

        Moving the text to the right using `lmargin1` has the problem
        of not having any effect on an empty line iff it's the last line.
        This is because `lmargin1` needs at least 1 character after it
        to work. This is a problem because it means that `lpadx` cannot
        be applied to the last line iff it's empty. To fix this, there
        are 2 options (set using `LEFT_PADX_FIX:int`):
        0  We use `lmargin1` and we get access to `FIX_CURSOR_LPADX`
        1  We use `padx` on the widget and pray the user doesn't notice
           that the same padding is also applied to the right side of the
           text widget (fine for small values of `lpadx`)
        Turning on `FIX_CURSOR_LPADX`, fixes the problem described above
        by adding an invisible character to the last line iff it's empty.
        But it creates new problems:
            * Bad performance (~3x slower) (probably because of XViewFix
                calling `.get` too many times - can be fixed by calling
                `get` on the renamed widget command using `.delegator`)
            * Breaks with undo/redo (can be fixed)
            * Text indices from the end (eg. "end-2c") are broken
        For normal use with small padding, just use `LEFT_PADX_FIX:=1`
    """

    def __init__(self, master:tk.Misc=None, **kwargs:dict) -> BetterText:
        # Defaults
        self._xscrollcmd:Callable = lambda *args: None
        self._lpadx:int = 3
        self._rpadx:int = 3
        self._cursor_room:int = 3
        self._xscroll_speed:int = 20
        self._yscroll_speed:int = 35
        # State
        self._disabled:bool = False
        self._canvasx:int = 0
        self._xoffset:int = 0
        self._frozen:bool = False
        # Deal with kwargs
        self._width:int = kwargs.pop("width", 646)
        self._height:int = kwargs.pop("height", 646)
        kwargs:dict = self._fix_kwargs(kwargs, can_update=False)

        # Frame (to allow text to be resized in pixels)
        self._frame = tk.Frame(master, width=self._width, height=self._height,
                               bd=0, highlightthickness=0)
        self._frame.pack_propagate(False)
        # Update `_width` and `_height`
        def on_resize(event:tk.Event) -> None:
            self._width, self._height = event.width, event.height
            self._update_viewport(xoffset=self._xoffset)
        self._frame.bind("<Configure>", on_resize)

        # Text
        super().__init__(self._frame, bd=0, highlightthickness=0, wrap="none",
                         xscrollcommand=self._on_xscroll_cmd, padx=0,
                         **{"pady":0, **kwargs})
        super().pack(fill="both", expand=True)
        # Copy some methods from canvas
        for method in GEOMETRY_METHODS:
            setattr(self, method, getattr(self._frame, method))

        # Add XViewFix/OnUndoCall
        self.percolator = perc = Percolator(self)
        self._xviewfix:XViewFix = XViewFix(self)
        perc.insertfilter(self._xviewfix)
        perc.insertfilter(BindTkFuncCall(perc, "edit undo",
                                         on_start=self._freeze,
                                         on_end=self._unfreeze))
        perc.insertfilter(BindTkFuncCall(perc, "edit redo",
                                         on_start=self._freeze,
                                         on_end=self._unfreeze))
        perc.insertfilter(BindTkFuncCall(perc, "see", on_start=self.see))
        if FIX_CURSOR_LPADX:
            perc.insertfilter(BindTkFuncCall(perc, "mark set insert",
                                             on_start=self._insert_changed))
            perc.insertfilter(BindTkFuncCall(perc, "insert",
                                             on_end=self._text_changed))
            perc.insertfilter(BindTkFuncCall(perc, "delete",
                                             on_end=self._text_changed))

        # Bind scrolling
        super().bind("<MouseWheel>", self._scroll_windows)
        super().bind("<Button-4>", self._scroll_linux)
        super().bind("<Button-5>", self._scroll_linux)

        # Re-parent self so that master is our self.master instead of inner
        self.master:tk.Misc = master

        # On delete/insert
        _refresh_xscrollcmd = lambda e: self._call_xscrollcmd(*self.xview())
        _refresh_xscrollcmd = lambda e: \
                                    self._update_viewport(xoffset=self._xoffset)
        for event in ("<<XViewFix-After-Insert>>", "<<XViewFix-After-Delete>>"):
            super().bind(event, _refresh_xscrollcmd, add=True)

        # First update
        super().after(1, lambda: self.see("1.0"))

        # For debugging:
        if DEBUG_INVISIBLE_CHAR and FIX_CURSOR_LPADX:
            super().tag_config("bettertext_invisible", foreground="white",
                               background="red")

    # kwargs fixer
    def _fix_kwargs(self, kwargs:dict, *, can_update:bool=True) -> dict:
        """
        Intercept changes to wrap and make sure it's always "none"
        Intercept changes to xscrollcommand and keep a reference to the
          function so we can call it later
        Intercept changes to these (since we handle those):
            * padx
            * xscroll_speed
            * yscroll_speed
            * cursor_room
        """
        if not kwargs: return kwargs
        should_update_viewport:bool = False

        def wrap_xscrollcmd(func:Callable|None) -> Callable:
            if not func:
                return lambda *args: None
            def inner(low:str, high:str) -> None:
                try:
                    return func(low, high)
                except tk.TclError:
                    pass
            return inner

        if not self._disabled:
            assert kwargs.pop("wrap", "none") == "none", "wrap must be none"
        assert not kwargs.pop("bd", 0), "border must be 0"
        assert not kwargs.pop("border", 0), "border must be 0"
        assert not kwargs.pop("highlightthickness", 0), \
                       "highlightthickness must be 0"
        assert "height" not in kwargs, "Cannot set width (NotImplemented)"
        assert "width" not in kwargs, "Cannot set width (NotImplemented)"

        # https://stackoverflow.com/q/78802587/11106801
        # Let pady pass
        if "padx" in kwargs:
            padx:tuple[int,int]|int = kwargs.pop("padx")
            if isinstance(padx, int): padx:tuple[int,int] = (padx,padx)
            assert isinstance(padx, tuple|list), \
                       "padx must be int or a tuple of 2 ints"
            assert len(padx) == 2, "padx must be a tuple of exactly 2 ints"
            lpadx, rpadx = padx
            assert isinstance(lpadx, int), "padding must be int"
            assert isinstance(rpadx, int), "padding must be int"
            self._lpadx, self._rpadx = lpadx, rpadx
            should_update_viewport:bool = True
        if "xscroll_speed" in kwargs:
            xscroll_speed:int = kwargs.pop("xscroll_speed")
            assert isinstance(xscroll_speed, int), "xscroll_speed must be int"
            self._xscroll_speed:int = self.xscroll_speed
            should_update_viewport:bool = True
        if "yscroll_speed" in kwargs:
            yscroll_speed:int = kwargs.pop("yscroll_speed")
            assert isinstance(yscroll_speed, int), "yscroll_speed must be int"
            self._yscroll_speed:int = self.yscroll_speed
            should_update_viewport:bool = True
        if "cursor_room" in kwargs:
            cursor_room:int = kwargs.pop("cursor_room")
            assert isinstance(cursor_room, int), "cursor_room must be int"
            self._cursor_room:int = cursor_room
            should_update_viewport:bool = True
        if "xscrollcommand" in kwargs:
            xscrollcmd = kwargs.pop("xscrollcommand")
            assert callable(xscrollcmd), "xscrollcmd must be callable"
            self._xscrollcmd = wrap_xscrollcmd(xscrollcmd)
            should_update_viewport:bool = True

        if should_update_viewport and can_update:
            self._update_viewport(xoffset=self._xoffset)

        # padx, xscroll_speed, yscroll_speed, cursor_room
        return kwargs

    # On undo/redo, we need to freeze the scrolling (otherwise RecursionError)
    def _freeze(self, _:str) -> None:
        if DEBUG_FREEZE: print("freeze")
        self._frozen:bool = True

    def _unfreeze(self, _:str) -> None:
        if DEBUG_FREEZE: print("unfreeze")
        self._frozen:bool = False
        self._update_viewport(xoffset=self._xoffset)
        if DEBUG_FREEZE: print("unfree done")

    # BetterText API
    def enable(self) -> None:
        """
        Enables BetterText so it acts like a fixed tk.Text
        """
        wrap:str = self.cget("wrap")
        assert wrap == "none", "Disable wrap when enabling BetterText"
        self._disabled:bool = False
        if FIX_CURSOR_LPADX: self._text_changed() # Update invisible character
        self._update_viewport(low=0.0) # Update viewport

    def disable(self) -> None:
        """
        Disables BetterText so it acts like a normal tk.Text
        """
        self._disabled:bool = True
        # Reset viewport stuff
        super().config(padx=0)
        if LEFT_PADX_FIX == 0:
            super().tag_config("bettertext_text", lmargin1=0)
        # Remove invisible character
        start, end = self._get_invisible_range()
        if start: super().delete(start, end)

    def assume_monospaced(self) -> None:
        self._xviewfix.assume_monospaced()

    def unknown_if_monospaced(self) -> None:
        self._xviewfix.unknown_if_monospaced()

    # config/configure/cget
    def config(self, **kwargs:dict) -> dict|None:
        """
        Overwrite this method with our own where we can intercept some
          arguments. For more info look at `_fix_kwargs`
        """
        if not kwargs: return super().config()
        new_kwargs:dict = self._fix_kwargs(kwargs)
        if new_kwargs: super().config(**new_kwargs)
    configure = config

    def cget(self, key:str) -> object:
        if key == "xscrollcommand":
            return self._xscrollcmd
        return super().cget(key)

    # Scrolling
    def _get_scroll_speed(self, event:tk.Event) -> int:
        return self._xscroll_speed if event.state & HORIZONTAL_DIRECTION else \
               self._yscroll_speed

    def _scroll_linux(self, event:tk.Event) -> str:
        scroll_speed:int = self._get_scroll_speed(event)
        steps:int = scroll_speed * (1-(event.num == 4)*2)
        return self._scroll_event(steps, event)

    def _scroll_windows(self, event:tk.Event) -> str:
        assert event.delta != 0, "On Windows, `event.delta` should never be 0"
        scroll_speed:int = self._get_scroll_speed(event)
        steps:int = self._round(-event.delta/abs(event.delta)*scroll_speed)
        return self._scroll_event(steps, event)

    def _scroll_event(self, steps:int, event:tk.Event) -> str:
        """
        If we get a scrolling event event:
         -------- --------------------- -----------------------
        |        |     Horizontal      |       Vertical        |
         -------- --------------------- -----------------------
        | Canvas | Send to Text widget | Send to Text widget   |
        | Text   | self._scroll(steps) | Allow to pass through |
         -------- --------------------- -----------------------
        """
        if event.widget is not self: return ""
        if event.state & HORIZONTAL_DIRECTION:
            self._scroll(steps)
        else:
            self.yview_scroll(steps, "pixels")
            self._update_viewport(xoffset=self._xoffset)
        return "break"

    def _scroll(self, steps:int) -> None:
        """
        Calculate the new xoffset and call `update_viewport`.
        """
        if self._disabled: return None
        new_xoffset:int = self._xoffset + steps
        max_xoffset:int = self._max_range1() - self._width
        xoffset:int = min(max_xoffset, max(-self._lpadx, new_xoffset))
        if xoffset != self._xoffset:
            self._update_viewport(xoffset=xoffset)

    def _on_xscroll_cmd(self, low:str, high:str) -> None:
        """
        If the text widget tries to scroll, calculate the new xoffset
          and call `_update_viewport` with it. Note that `_update_viewport`
          will call `xview moveto 0.0` which will trigger this function.
        """
        if self._disabled:
            self._call_xscrollcmd(low, high)
        elif True:
            super().xview("moveto", "0.0")
        elif float(low) > 0:
            super().xview("moveto", "0.0")
            low, high = float(low), float(high)
            vis_line_width:int = self._width / (high-low)
            new_xoffset:int = self._round(low*vis_line_width)
            if self._xoffset < 0: new_xoffset += self._xoffset
            if DEBUG_ON_XSCROLL_CMD:
                print(f"Text tried to scroll {new_xoffset=}")
            self._update_viewport(xoffset=new_xoffset)

    # On insert change, maybe add INVISIBLE_CHAR
    def _insert_changed(self, _:str, __:str, insert:str) -> tuple[str,str,str]:
        assert FIX_CURSOR_LPADX, "SanityCheck"
        if self._disabled: return None
        insert:str = super().index(insert)
        start, _ = self._get_invisible_range()
        if start and super().compare(insert, ">", start):
            insert:str = start
        return ("set", "insert", insert)

    def _text_changed(self, *args:tuple) -> None:
        """
        Add INVISIBLE_CHAR to the last line if it's empty. Read implementation
          details for more info
        """
        assert FIX_CURSOR_LPADX, "SanityCheck"
        if self._disabled: return None
        is_text:bool = bool(self.get("end-1l", "end-1c"))
        start, end = self._get_invisible_range()
        invis:bool = start is not None
        if invis == is_text == False:
            # If there is NO invisible character and there is NO text,
            #   add an invisible character
            super().insert("end-1c", INVISIBLE_CHAR, "bettertext_invisible")
            super().mark_set("insert", "end-2c")
        elif invis == is_text == True:
            # If there IS an invisible character and there IS text,
            #   remove the invisible character
            super().delete(start, end)
            # super().delete("end-2c", "end-1c") # Causes RecursionError

    def _get_invisible_range(self) -> tuple[str,str]:
        assert FIX_CURSOR_LPADX, "SanityCheck"
        ranges:tuple[str,str]|None = super().tag_ranges("bettertext_invisible")
        if not ranges: return (None, None)
        return tuple(map(str, ranges))

    # tk.Text.get changed implementation
    def get(self, index1:str, index2:str=None) -> str:
        """
        Remove the INVISIBLE_CHAR from the last line. Read implementation
          details for more info.
        """
        if self._disabled or (not FIX_CURSOR_LPADX):
            return super().get(index1, index2)
        # Get invisible range
        index2:str = super().index(index2)
        start, end = self._get_invisible_range()
        # If no invisible range, return default
        if start is None: return super().get(index1, index2)
        # If invisible range, return requested text outside of it
        if super().compare(index2, "<=", start):
            return super().get(index1, index2)
        return super().get(index1, start) + super().get(end, index2)

    # Helpers/xview
    def _round(self, x:float) -> int:
        # Round to the closest integer
        # 0.5=>1, -0.5=>0
        return int(x) if x < 0 else int(x + 0.5)

    def _max_range1(self) -> int:
        """
        Gets the maximum value for `_xoffset`
        The return value will always be at least 1
        """
        if not self._xviewfix.line_lengths: return max(1, self._rpadx)
        return max(1, max(self._xviewfix.line_lengths) + self._rpadx)

    # tk.text.xview reimplementation
    def fixed_xview(self) -> tuple[str,str]:
        """
        This acts like tkinter.Text.xview with 0 arguments if the text
          widget was large enough (vertically) to show all of the lines
        """
        # Get base x offset of the viewport and the max line length
        if self._disabled: return super().xview()
        diff_range1:int = self._lpadx + self._max_range1()
        # Use the 2 values to calculate the new (low,high) values
        #   that we can pass through to the xscrollcommand
        low:float = (self._xoffset+self._lpadx) / diff_range1
        low:float = max(low, 0.0)
        high:float = low + self._width/diff_range1
        return str(low), str(min(high, 1.0))

    def xview(self, *args:tuple) -> tuple[str]|None:
        """
        Redo everything inside xview from scratch because that is the main
          issue. This was a pain...
        Note: 'xview scroll XXX units' not allowed because I can't compute
              compute the size of units. It depends on the font and there
              is no good documentation for it
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
                self._scroll(self._round(size))
            elif what == "units":
                raise ValueError("'xview scroll XXX units' not implemented yet")
            elif what == "pages":
                self._scroll(self._round(size*self._width))
            else:
                raise ValueError(f"Unknown unit {what!r} in 'xview scroll'")
            return None
        raise NotImplementedError(f"Implement {args!r}")

    # tk.text.see reimplementation
    def see(self, idx:str, *, no_xscroll:bool=False) -> str:
        """
        This acts like `tkinter.Text.see` with a hidden `no_xscroll`
          parameter only used in `DLineInfoWrapper.get_width`
        """
        if no_xscroll or self._disabled:
            super().see(idx)
            return BREAK

        # Get info from text widget
        idx:str = super().index(idx)
        line, char = idx.split(".")
        ylow, yhigh = map(float, super().yview())
        super().yview_pickplace(f"{line}.0")
        isstart:bool = char == "0"
        isend:bool = super().compare(f"{idx} lineend", "==", idx)

        # Calculate where we are trying to see
        cur_low_see:int = self._xoffset
        cur_mid_see:int = cur_low_see + self._width//2
        cur_high_see:int = cur_low_see + self._width
        if isstart:
            tar_see:int = -self._lpadx
        else:
            tar_see:int = super().count(f"{idx} linestart", idx, f"xpixels")[0]
        if isend:
            tar_see += self._rpadx

        # Set up variables
        direction:int = 0
        diff:int = 0

        # Check if needs scroll left:
        tar_see_if_low:int = tar_see - self._cursor_room
        if cur_low_see > tar_see_if_low:
            diff:int = cur_low_see - tar_see_if_low
            direction:int = -1 # left

        # Check if needs scroll right:
        tar_see_if_high:int = tar_see + self._cursor_room
        if cur_high_see < tar_see_if_high:
            diff:int = tar_see_if_high - cur_high_see
            direction:int = +1 # right

        # Check if we are scrolling far in the vertical direction
        nylow, nyhigh = map(float, super().yview())
        scroll_far:bool = not ((ylow < nylow <= yhigh) or \
                               (ylow < nyhigh <= yhigh))
        if scroll_far:
            direction:int = 2*(tar_see > cur_mid_see) - 1
        # Check if we are scrolling far in the horizontal direction
        scroll_far |= (diff > 1.346*self._width)

        # Make sure diff is positive and shortcur `_update_viewport` call
        assert diff >= 0, "SanityCheck"
        if diff == 0:
            super().xview("moveto", "0.0")
            return BREAK

        # Scrolling far
        if scroll_far:
            diff += self._width//2

        # Update viewport
        new_xoffset:int = self._xoffset + diff*direction
        if DEBUG_SEE: print(f"{diff=} {direction=} {new_xoffset=}")
        self._update_viewport(xoffset=new_xoffset)
        return BREAK

    # Updaing the viewport/scrollbar
    def _update_viewport(self, low:float=None, xoffset:int=None) -> None:
        """
        Scroll horizontally to match either the passed in low or xoffset
        """
        if self._disabled or self._frozen: return None
        max_range1:int = self._max_range1()
        diff_range1:int = self._lpadx + max_range1
        low_high_diff:float = self._width / diff_range1
        max_low:float = 1 - low_high_diff
        if xoffset is None:
            if DEBUG_VIEWPORT: print(end="l")
            assert low is not None, "pass in either low or xoffset not both"
            low:float = max(0.0, min(1.0, max_low, low))
            new_xoffset:int = self._round(low*diff_range1) - self._lpadx
        elif low is None:
            if DEBUG_VIEWPORT: print(end="x")
            assert xoffset is not None, "pass in either low or xoffset not both"
            assert isinstance(xoffset, int), "xoffset must be an int"
            max_xoffset:int = max_range1 - self._width
            new_xoffset = max(-self._lpadx, min(max_xoffset, xoffset))
            low:float = (new_xoffset + self._lpadx) / diff_range1
        else:
            raise RuntimeError("pass in either low or xoffset")

        self._xoffset:int = new_xoffset
        low:float = max(0.0, min(max_low, low))
        high:float = min(1.0, max(0.0, low+low_high_diff))

        super().xview("moveto", "0.0")
        self._set_canvasx(-self._xoffset)
        if DEBUG_VIEWPORT: print(f"{self._xoffset=}, {low=:.4f}, {high=:.4f}")
        self._call_xscrollcmd(str(low), str(high))

    def _set_canvasx(self, canvasx:int) -> None:
        """
        Move the text contents to match the passed in canvasx.
        Note that canvasx is the same as -self._xoffset and this
          function should only be called from `_update_viewport`
        """
        # If canvasx hasn't changed:
        if self._canvasx == canvasx: return None
        self._canvasx:int = canvasx
        if canvasx >= 0:
            # If we are viewing the left side
            if DEBUG_VIEWPORT: print(end="<")
            if LEFT_PADX_FIX == 0:
                super().tag_config("bettertext_text", lmargin1=canvasx)
                super().config(padx=0)
            elif LEFT_PADX_FIX == 1:
                super().config(padx=canvasx)
        else:
            # If we are viewing the right side
            if DEBUG_VIEWPORT: print(end=">")
            if LEFT_PADX_FIX == 0:
                super().tag_config("bettertext_text", lmargin1=0)
            super().config(padx=canvasx)

    def _call_xscrollcmd(self, low:str, high:str) -> None:
        """
        Call the scrollbar attached to this widget
        """
        if DEBUG_SCROLLBAR: print(f"Scrollbar low={low[:4]} high={high[:4]}")
        self.cget("xscrollcommand")(low, high)


if __name__ == "__main__":
    from os.path import dirname, join
    from time import perf_counter

    from betterscrollbar import BetterScrollBarHorizontal

    start:float = perf_counter()
    root:tk.Tk = tk.Tk()
    root.geometry("+0+0")

    text:BetterText = BetterText(root, width=400, height=200, undo=True,
                                 padx=10, cursor_room=3)
    text.mark_set("insert", "1.0")
    text.pack(fill="both", expand=True)
    text.config(font=("DejaVu Sans Mono", 9, "normal", "roman"))
    # text.assume_monospaced()

    filepath:str = tk.__file__
    # filepath:str = join(dirname(dirname(dirname(__file__))), "bad.py")
    with open(filepath, "r") as file:
        t = file.read()
    # t = "\n".join([
    #                 "s"+"a"*78+"e",
    #                 *["a"*50]*40,
    #                 "a"*80,
    # ])
    text.insert("end", t)

    evs:tuple[str] = ("<<XViewFix-Before-Insert>>", "<<XViewFix-After-Insert>>",
                      "<<XViewFix-After-Delete>>", "<Left>", "<Right>", "<Up>",
                      "<Down>", "<KeyRelease-Left>", "<KeyRelease-Right>",
                      "<KeyRelease-Up>", "<KeyRelease-Down>",
                      "<KeyRelease-Home>", "<KeyRelease-End>")
    for ev in evs:
        text.bind(ev, lambda e: text.see("insert"), add=True)

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
