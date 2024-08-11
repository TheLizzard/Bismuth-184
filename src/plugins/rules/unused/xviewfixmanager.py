from __future__ import annotations
from time import perf_counter
import tkinter as tk

from .baserule import Rule


class DLineInfoWrapper:
    """
    Text.dlineinfo only works if the line is visible:
    > If the display line containing index is not visible on the screen
    > then the return value is an empty list.
    >   From https://www.tcl.tk/man/tcl8.4/TkCmd/text.htm#M81
    This class fixes that by forcing Text.see each line before calling
    dlineinfo
    """
    __slots__ = "text", "xview", "yview", "inside"

    def __init__(self, text:tk.Text) -> DLineInfo:
        self.inside:bool = False
        self.text:tk.Text = text

    def __enter__(self) -> DLineInfo:
        self.xview:str = self.text.xview()[0]
        self.yview:str = self.text.yview()[0]
        self.inside:bool = True
        return self

    def __exit__(self, exc_t:type, exc_val:BaseException, tb:Traceback) -> bool:
        self.text.xview("moveto", self.xview)
        self.text.yview("moveto", self.yview)
        self.inside:bool = False
        return False

    def get_width(self, line:int) -> int:
        assert self.inside, "You can only call this if inside the context"
        self.text.see(f"{line+1}.0")
        dlineinfo:tuple[int]|None = self.text.dlineinfo(f"{line+1}.0")
        return dlineinfo[2]


# Not really any faster than the python code but I already wrote it in tcl
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


# This is a bad solution to https://stackoverflow.com/q/35412972/11106801
#   but it works. It calls dlineinfo on each line to figure out the width
#   of all of the lines which it caches and updates only when necessary
#   It can go through around 4.6k lines (tkinter/__init__.py from cpython)
#   in 1.08 sec
class XViewFixManager(Rule):
    __slots__ = "text", "old_xset", "dirty", "dlineinfo", "width", "height", \
                "line_lengths"
    REQUESTED_LIBRARIES:tuple[str] = "insertdeletemanager", "wrapmanger", \
                                     "scrollbarmanager"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> SeeEnd:
        evs:tuple[str] = (
                           # Any inserts/deletes
                           "<<Before-Insert>>", "<<Before-Delete>>",
                           "<<After-Insert>>", "<<After-Delete>>",
                           # Undo/Redo
                           "<<Undo-Triggered>>", "<<Redo-Triggered>>",
                           # Configure (so that we can get the width+height)
                           "<Configure>",
                         )
        evs = ()
        super().__init__(plugin, text, ons=evs)
        self.dlineinfo:DLineInfoWrapper = DLineInfoWrapper(text)
        self.line_lengths:list[int] = [0]
        self.dirty:set[int] = set()
        self.text:tk.Text = text
        self.height:int = 0
        self.width:int = 0

    def attach(self) -> None:
        self.old_xset = self.text.cget("xscrollcommand")
        super().attach()
        # self._attach()

    def _attach(self) -> None:
        self.text.config(xscrollcommand=self.xset)
        self.text.after(100, self._reset_cache)
        self.text.after(100, self.xset)
        self.text.tk.eval(TCL_CODE)
        self._reset_cache()

    def detach(self) -> None:
        self.text.config(xscrollcommand=self.old_xset)
        super().detach()

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        width = height = 0
        data:tuple = ()
        if on == "configure":
            width, height = event.width, event.height
        elif on in ("<before-insert>", "<before-delete>"):
            data:tuple = event.data["abs"]
        return data, width, height, True

    def do(self, on:str, data:tuple, width:int, height:int) -> Break:
        if on == "configure":
            self.width, self.height = width, height
            return False

        # Undo/Redo stuff
        if on in ("<undo-triggered>", "<redo-triggered>"):
            # Don't know which lines were effected so reset everything
            #   If you code this up, you will get way better performance
            #   but the memory usage might be become a problem
            self._reset_cache()
            return False

        if on == "<before-insert>":
            # data = (idx, text, tags)
            idx, text, _ = data
            if self.text.compare(idx, "==", "end"):
                idx:str = self.text.index("end -1c")
            linestart:int = int(idx.split(".")[0])-1
            self.dirty.add(linestart)
            for i in range(text.count("\n")):
                line:int = linestart+i+1
                self.line_lengths.insert(line, -1)
                self.dirty.add(line)
            return False

        if on == "<before-delete>":
            # pressed backspace
            #   data = ("insert -1c", None)
            # Selected and deleted
            #   data = ("2.5", "6.3")
            idxa, idxb = data
            if idxb is None:
                idxa:str = self.text.index(f"{idxa} +1c")
                linea, chara = idxa.split(".")
                linea:int = int(linea)-1
                if chara == "0":
                    self.dirty.add(linea-1)
                    self.line_lengths.pop(linea)
                else:
                    self.dirty.add(linea)
            else:
                if self.text.compare(idxb, "==", "end"):
                    idxb:str = self.text.index("end -1c")
                low:int = int(idxa.split(".")[0])-1
                high:int = int(idxb.split(".")[0])-1
                self.dirty.add(low)
                for _ in range(low+1, high+1):
                    self.line_lengths.pop(low+1)
            return False

        if on in ("<after-insert>", "<after-delete>"):
            self.text.update_idletasks()
            with self.dlineinfo:
                for line in self.dirty:
                    self.line_lengths[line] = self.dlineinfo.get_width(line)
                self.dirty.clear()
            return False

        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    def _reset_cache(self) -> None:
        start:float = perf_counter()
        self.text.update_idletasks()
        self.line_lengths.clear()
        # Python version of the tcl code at the top
        # with self.dlineinfo:
        #     for line in range(int(self.text.index("end").split(".")[0])-1):
        #         self.line_lengths.append(self.dlineinfo.get_width(line))
        output:tuple = self.text.tk.call("dline_all", self.text)
        print(output)
        self.line_lengths.extend(map(int, output))
        print(f"{perf_counter() - start:.2f} sec taken to reset cache")

    def xset(self, *_) -> None:
        # Get base x offset of the viewport and the max line length
        x_scroll, max_line_width = self.textx(0), max(self.line_lengths)
        if max_line_width == 0:
            print("error max(self.line_lengths)=0")
            return None
        if x_scroll == -1:
            print("error in textx")
            return None
        # Use the 2 values to calculate the new (low,high) values
        #   that we can pass through to the xscrollcommand
        low:float = x_scroll/max_line_width
        high:float = (x_scroll+self.width)/max_line_width
        high:float = min(high, 1.0) # self.width might be > max_line_width
        print(f"sending {low=} {high=}")
        self.text.tk.call(self.old_xset, str(low), str(high))

    def textx(self, x:int) -> int:
        """
        Converts text viewbox x coordinate into the real x coordinate.
        This is probably a value that tcl internally stores but doesn't
        expose so we have to calculate it based on the fractions from
        `Text.xview`
        """
        # Get the current viewport (y-axis)
        top:str = self.text.index("@0,0")
        bottom:str = self.text.index(f"@0,{self.height-1}")
        top, bottom = int(top.split(".")[0]), int(bottom.split(".")[0])
        # Get the max line width out of each of the lines in the viewport
        line_widths:list[int] = self.line_lengths[top-1:bottom]
        if len(line_widths) == 0:
            print("error self.line_lengths[top-1:bottom]=[]", top, bottom,
                  self.line_lengths)
            return -1
        max_line_width:int = max(line_widths)
        # Use the first fraction from `xview()` to calculate the base x offset
        #   of the viewport
        return int(max_line_width*float(self.text.xview()[0]) + x + 0.5)