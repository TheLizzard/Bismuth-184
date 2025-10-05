from __future__ import annotations
import tkinter as tk

try:
    from betterframe import BetterFrame, make_bind_frame
    from betterscrollbar import BetterScrollBarHorizontal
    from bettertk import IS_UNIX
except ImportError:
    from .betterframe import BetterFrame, make_bind_frame
    from .betterscrollbar import BetterScrollBarHorizontal
    from .bettertk import IS_UNIX

def round_rectangle(self:tk.Canvas, x1:int, y1:int, x2:int, y2:int, radius:int,
                    **kwargs:dict) -> int:
    # Taken from https://stackoverflow.com/a/44100075/11106801
    points:tuple[int] = (
                         x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius,
                         y1, x2, y1, x2, y1+radius, x2, y1+radius, x2,
                         y2-radius, x2, y2-radius, x2, y2, x2-radius, y2,
                         x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2,
                         x1, y2-radius, x1, y2-radius, x1, y1+radius, x1,
                         y1+radius, x1, y1
                       )
    return self.create_polygon(points, smooth=True, **kwargs)
tk.Canvas.create_round_rectangle = round_rectangle


WIDGET_KWARGS:dict = dict(bd=0, highlightthickness=0, takefocus=False)
DEFAULT_NOTCH_BG:str = "#444444"
NOT_DRAG_DIST:int = 10
BUTTON1_TK_STATE:int = 256
TAB_NOTCH_OPTIONS:list[str] = [
                                "font", "text", "can_drag", "bg", "fg",
                                "focused_fg", "focused_bg", "min_width",
                                "padx",
                              ]


class TabNotch(tk.Canvas):
    """
    Options:
        text, font, min_width, can_drag, padx,
        bg, background, fg, focused_foreground,
        focused_bg, focused_background, focused_fg, focused_foreground
    """

    __slots__ = "_text_id", "_text", "_rrect_id", "_width", "_min_width", \
                "_focused_bg", "_focused_fg", "_fg", "_can_drag", "_focused", \
                "_padx"

    def __init__(self, notches:TabNotches, **kwargs:dict) -> TabNotch:
        super().__init__(notches, bg=DEFAULT_NOTCH_BG, width=1, height=1,
                         **WIDGET_KWARGS)
        self._text_id:int = super().create_text((0,0), text="", anchor="nw",
                                                fill="white", font="TkTextFont")
        self._focused_bg:str = "black"
        self._focused_fg:str = "white"
        self._min_width:int = 0
        self._can_drag:bool = True
        self._focused:bool = False
        self._rrect_id:int = None
        self._fg:str = "white"
        self._height:int = 0
        self._width:int = 0
        self._text:str = ""
        self._padx:int = 7
        super().bind("<Button-1>", lambda e: notches._clicked(self), add=True)
        super().bind("<Button-2>", lambda e: notches._close(self), add=True)
        self.config(**kwargs)

    # Focus
    def focus(self) -> None:
        if self._focused: return None
        self._focused:bool = True
        self._redraw_focus()
        super().itemconfig(self._text_id, fill=self._focused_fg)

    def unfocus(self) -> None:
        if not self._focused: return None
        self._focused:bool = False
        if self._rrect_id is not None:
            super().delete(self._rrect_id)
        super().itemconfig(self._text_id, fill=self._fg)

    @property
    def focused(self) -> bool:
        return self._focused

    # Override config/configure/cget
    def config(self, **kwargs:dict[str:object]) -> dict[str:object]|None:
        # Return the options
        if not kwargs:
            return {option:self.cget(option) for option in TAB_NOTCH_OPTIONS}
        # Font
        if "font" in kwargs:
            super().itemconfig(self._text_id, font=kwargs.pop("font"))
            self._redraw_text()
        # Background
        if ("bg" in kwargs) or ("background" in kwargs):
            bg:str = kwargs.pop("bg", kwargs.pop("background", None))
            super().config(bg=bg)
        # Focused Background
        if ("focused_bg" in kwargs) or ("focused_background" in kwargs):
            bg:str = kwargs.pop("focused_background",
                                kwargs.pop("focused_bg", None))
            if bg != self._focused_bg:
                self._focused_bg:str = bg
                self._redraw_focus()
        # Foreground
        if ("fg" in kwargs) or ("foreground" in kwargs):
            fg:str = kwargs.pop("fg", kwargs.pop("foreground", None))
            if fg != self._fg:
                self._fg:str = fg
                if not self._focused:
                    super().itemconfig(self._text_id, fill=fg)
        # Focused foreground
        if ("focused_fg" in kwargs) or ("focused_foreground" in kwargs):
            fg:str = kwargs.pop("focused_foreground",
                                kwargs.pop("focused_fg", None))
            if fg != self._focused_fg:
                self._focused_fg:str = fg
                if self._focused:
                    super().itemconfig(self._text_id, fill=fg)
        # Text
        if "text" in kwargs:
            text:str = kwargs.pop("text")
            if self._text != text:
                self._text:str = text
                self._redraw_text()
        # Minimum notch size
        if "min_width" in kwargs:
            min_width:int = kwargs.pop("min_width")
            assert isinstance(min_width, int), "min_width must be an int"
            if self._min_width != min_width:
                self._min_width:int = min_width
                self._redraw_text()
        # Can drag
        if "can_drag" in kwargs:
            self._can_drag:bool = kwargs.pop("can_drag")
            assert isinstance(self._can_drag, bool), "can_drag must be a bool"
        # padx
        if "padx" in kwargs:
            self._padx:bool = kwargs.pop("padx")
            assert isinstance(self._padx, int), "padx must be an int"
            self._redraw_text()
        # Unknown options
        for arg in kwargs:
            raise tk._tkinter.TclError(f'unknown option "{arg}"')

    def cget(self, key:str) -> object:
        if key == "font":
            return super().itemcget(self._text_id, "font")
        if key == "bg":
            return super().cget("bg")
        if key == "focused_bg":
            return self._focused_bg
        if key == "fg":
            return self._fg
        if key == "focused_fg":
            return self._focused_fg
        if key == "text":
            return self._text
        if key == "min_width":
            return self._min_width
        if key == "can_drag":
            return self._can_drag
        if key == "width":
            return self._width
        if key == "height":
            return self._height
        if key == "padx":
            return self._padx
        raise tk._tkinter.TclError(f'unknown option "{key}"')

    # Helpers
    def _rename_text_helper(self) -> None:
        self.itemconfig(self._text_id, text=self._text)
        x1, y1, x2, y2 = super().bbox(self._text_id)
        text_width:int = x2 - x1
        self._height:int = y2 - y1
        self._width:int = max(self._min_width, text_width) + 2*self._padx
        text_x:int = (self._width-text_width)//2
        super().moveto(self._text_id, text_x, self._height/2)
        super().config(width=self._width, height=2*self._height)
        if self._rrect_id is not None:
            self._redraw_focus()

    # Redraw functions
    def _redraw_text(self) -> None:
        self.master._renaming(self, self._rename_text_helper)

    def _redraw_focus(self) -> None:
        if not self.focused: return None
        if self._rrect_id is not None:
            super().delete(self._rrect_id)
        pts:tuple[int] = (0, 0, self._width, 3*self._height)
        id:int = super().create_round_rectangle(*pts, radius=25,
                                                fill=self._focused_bg)
        self._rrect_id:int = id
        super().tag_lower(self._rrect_id)


class TabNotches(BetterFrame):
    __slots__ = "add_notch", "_min_width", "notebook", "notches", \
                "_tmp_notch", "_tmp_notch_info", "_notch_dragging", \
                "dragging", "dragx", "_notches_kwargs"

    def __init__(self, notebook:Notebook, scrolled:bool=True,
                 **kwargs:dict[str:object]) -> TabNotches:
        self._notches_kwargs:dict[str:object] = kwargs
        self.notebook:Notebook = notebook
        super().__init__(notebook, bg=DEFAULT_NOTCH_BG, hscroll=scrolled,
                         HScrollBarClass=BetterScrollBarHorizontal,
                         hscrolltop=True, scrollbar_kwargs={"thickness":4},
                         hide_hscroll=HIDE_SCROLLBAR)
        self.pages:list[NotebookPage|TabNotch] = []
        self.curr_page:NotebookPage = None
        self._page_dragging:bool = None
        self.add_notch:TabNotch = None
        self.dragging:bool = False
        # Create add notch
        self.enable_new_tab()
        # super().config(height=self.add_notch.winfo_reqheight())
        # Temp tab notch
        fg:str = kwargs.get("fg", DEFAULT_NOTCH_BG)
        self._tmp_notch:TabNotch = TabNotch(self, **{**kwargs, "fg":fg})
        # Make bindings
        make_bind_frame(self)
        self.bind("<ButtonPress-1>", self._start_dragging, add=True)
        self.bind_all("<B1-Motion>", self._drag, add=True)
        self.bind_all("<Motion>", self._drag, add=True)
        self.bind_all("<ButtonRelease-1>", self._end_dragging, add=True)

    # Enable/disable add tab notch
    def disable_new_tab(self) -> None:
        if self.add_notch is None: return None
        self.add_notch.destroy()
        self.add_notch:TabNotch = None

    def enable_new_tab(self) -> None:
        if self.add_notch is not None: return None
        kwargs:dict[str:object] = {**self._notches_kwargs, "min_width":0}
        self.add_notch:TabNotch = TabNotch(self, text="+", **kwargs)
        self.add_notch.grid(row=1, column=len(self.pages)+1)

    # Add a new page
    def add(self, page_frame:tk.Frame, notebook:Notebook) -> NotebookPage:
        page:NotebookPage = NotebookPage(notebook=notebook, notches=self,
                                         page_frame=page_frame,
                                         **self._notches_kwargs)
        page.grid(row=1, column=len(self.pages))
        if self.add_notch is not None:
            self.add_notch.grid(row=1, column=len(self.pages)+1)
        self.pages.append(page)
        return page

    # Remove a page
    def remove(self, page:NotebookPage) -> None:
        assert page in self.pages, "InternalError"
        idx:int = self.pages.index(page)
        self.pages.pop(idx)
        for i in range(idx, len(self.pages)):
            self.pages[i].grid(row=1, column=i)

    # See a specific page
    def see(self, page:NotebookPage) -> None:
        assert isinstance(page, NotebookPage), "TypeError"
        assert page in self.pages, "Page not in self.pages?"
        idx:int = self.pages.index(page)
        see_add:bool = idx == len(self.pages)-1
        # Get information
        super().update_idletasks()
        full_width:int = super().winfo_width()
        curr_low, curr_high = super().xview()
        curr_low, curr_high = float(curr_low), float(curr_high)
        # Calculate the minx and maxx of the notch
        minx:int = 0
        for i in range(idx):
            minx += self.pages[i].cget("width")
        maxx:int = minx + self.pages[idx].cget("width")
        if see_add:
            maxx:int = full_width
        # Calculate the target_low and target_high
        target_low, target_high = minx/full_width, maxx/full_width
        if curr_low > target_low:
            super().xview("moveto", str(target_low))
        if curr_high < target_high:
            # Since moveto sets the min and not the max, we have to
            #   calculate the min for maxx as the max
            viewport_width:float = full_width * (curr_high-curr_low)
            target_high_low:float = (maxx-viewport_width) / full_width
            super().xview("moveto", str(target_high_low))

    # Iterate over all of the pages
    def iter_pages(self) -> Iterator[NotebookPage]:
        for page in self.pages:
            yield page

    @property
    def number_of_pages(self) -> int:
        return len(self.pages)

    # Focus methods
    def focus_page(self, page:NotebookPage|None) -> None:
        if page == self.curr_page:
            return None
        if self.curr_page is not None:
            self.curr_page.unfocus()
            self.curr_page.disappear()
        if page:
            page.appear()
            TabNotch.focus(page) # Ewww
        self.curr_page:NotebookPage = page
        self.notebook.event_generate("<<Tab-Switched>>")
        if page:
            self.see(self.curr_page)

    def focus_prev(self) -> None:
        page:NotebookPage = self._switch_next_prev_tab(strides=-1, default=-1)
        if page == self.curr_page:
            page:NotebookPage = None
        self.focus_page(page)

    def focus_next(self) -> None:
        page:NotebookPage = self._switch_next_prev_tab(strides=+1, default=0)
        if page == self.curr_page:
            page:NotebookPage = None
        self.focus_page(page)

    def focus_idx(self, idx:int) -> None:
        self.pages[idx].focus()

    # Destroy tab
    def page_destroy(self, page:NotebookPage) -> None:
        if self.notebook.on_try_close(page):
            return None
        if self.curr_page == page:
            if self.pages[0] == page:
                self.focus_next()
            else:
                self.focus_prev()
        assert self.curr_page != page, "SanityCheck"
        assert self.curr_page in self.pages+[None], "SanityCheck"
        page._close()
        self.pages.remove(page)

    def _switch_next_prev_tab(self, strides:int, default:int) -> NotebookPage:
        if self.curr_page is None:
            if len(self.pages) == 0:
                return None
            return self.pages[default]
        else:
            idx:int = self.pages.index(self.curr_page) + strides
            return self.pages[idx%len(self.pages)]

    def _clicked(self, notch_or_page:TabNotch|NotebookPage) -> None:
        if notch_or_page == self.add_notch:
            self.notebook.event_generate("<<Tab-Create>>")
        else:
            notch_or_page.focus()

    def _close(self, notch_or_page:TabNotch|Notebookpage) -> None:
        if notch_or_page != self.add_notch:
            notch_or_page.close()

    def _start_dragging(self, event:tk.Event) -> None:
        if not isinstance(event.widget, NotebookPage): return None
        self._page_dragging:NotebookPage = event.widget
        if not self._page_dragging.cget("can_drag"):
            self._page_dragging:NotebookPage = None
        self.dragx:int = event.x
        return "break"

    def _end_dragging(self, event:tk.Event=None) -> str:
        if self._page_dragging is None:
            return None
        if self.dragging:
            self._tmp_notch.grid_forget()
            idx:int = self._tmp_notch_info["idx"]
            self._page_dragging.grid(row=1, column=idx)
            self.pages[idx] = self._page_dragging
        self._page_dragging:NotebookPage = None
        self.dragging:bool = False
        return "break"

    def _drag(self, event:tk.Event) -> str:
        if self._page_dragging is None:
            return None
        if not (event.state & BUTTON1_TK_STATE):
            self._end_dragging()
            return None
        if not self.dragging:
            if abs(event.x-self.dragx) < NOT_DRAG_DIST:
                return None
            self.dragging:bool = True
            # Config temp notch
            self._tmp_notch.config(text=self._page_dragging.cget("text"))
            # Save notch info
            idx:int = self.pages.index(self._page_dragging)
            x:int = self._get_start_x(self._page_dragging)
            self._tmp_notch_info:dict[str:int] =  dict(idx=idx, x=x)
            # Put the temp notch in place
            self._tmp_notch.grid(row=1, column=idx)
            # Lift real notch
            tk.Misc.lift(self._page_dragging)
            # Put temp notch in data structures
            self.pages[idx] = self._tmp_notch

        x:int = event.x_root - super().winfo_rootx()
        delta:int = self._calculate_idx_delta(x-self.dragx)
        if delta != 0:
            self._reshiffle(delta)
        self._page_dragging.place(x=x-self.dragx, y=0)
        return "break"

    def _get_start_x(self, page:NotebookPage) -> int:
        total:int = 0
        for p in self.pages:
            if p == page:
                return total
            total += p._width
        raise RuntimeError("InternalError: page not in self.pages?")

    def _calculate_idx_delta(self, notch_start:int) -> int:
        idx:int = self._tmp_notch_info["idx"]
        x:int = self._tmp_notch_info["x"]
        if x < self._page_dragging.winfo_x():
            # dragging =>
            if self._tmp_notch == self.pages[-1]:
                return 0
            next_notch:TabNotch = self.pages[idx+1]
            notch_end:int = notch_start + self._page_dragging._width
            next_notch_start = x + self._tmp_notch.cget("width")
            if notch_end > next_notch_start+next_notch._width/2:
                return +1
            else:
                return 0
        else:
            # dragging <=
            if self._tmp_notch == self.pages[0]:
                return 0
            prev_notch:TabNotch = self.pages[idx-1]
            prev_notch_half = x - prev_notch.cget("width")/2
            if notch_start < prev_notch_half:
                return -1
            else:
                return 0

    def _reshiffle(self, delta:int) -> None:
        idx:int = self._tmp_notch_info["idx"]
        self._tmp_notch_info["idx"] += delta
        self._swap(self.pages, idx, idx+delta)
        self._tmp_notch_info["x"] += self.pages[idx]._width * delta
        for i in (idx, idx+delta):
            self.pages[i].grid(row=1, column=i)

    @staticmethod
    def _swap(array:list, idxa:int, idxb:int):
        array[idxa], array[idxb] = array[idxb], array[idxa]

    def _renaming(self, notch:TabNotch, rename:Callable) -> None:
        curr_high:float = float(super().xview()[1])
        rename()
        if (curr_high > 0.999) and self.pages:
            self.see(self.pages[-1])


CONTROL_T:bool = False
CONTROL_W:bool = False
TAB_CONTROLS:bool = True
CONTROL_NUMBERS_CONTROLS:bool = False
CONTROL_NUMBERS_RESTRICT:bool = False
HIDE_SCROLLBAR:bool = True

class NotebookPage(TabNotch):
    __slots__ = "notebook", "page_frame", "notches"

    def __init__(self, *, notebook:Notebook, page_frame:tk.Frame,
                 notches:TabNotches, **kwargs:dict[str:object]) -> NotebookPage:
        super().__init__(notches, **kwargs)
        self.page_frame:tk.Misc = page_frame
        self.notches:TabNotches = notches
        self.notebook:Notebook = notebook

    def add_frame(self, frame:tk.Misc) -> NotebookPage:
        def call(func:Callable[None]) -> Callable[tk.Event,str]:
            def inner(event:tk.Event) -> str:
                func()
                return "break"
            return inner
        frame.pack(in_=self.page_frame, fill="both", expand=True)
        if TAB_CONTROLS:
            #frame.bind("<Control-Key><Tab>", self.notebook.switch_next_tab)
            frame.bind("<Control-Tab>", call(self.notches.focus_next), add=True)
            if IS_UNIX:
                sequence:str = "<Control-ISO_Left_Tab>"
            else:
                sequence:str = "<Control-Shift-Tab>"
            frame.bind(sequence, call(self.notches.focus_prev), add=True)
        if CONTROL_NUMBERS_CONTROLS:
            def _control_numbers(event:tk.Event) -> str:
                number:str = getattr(event, "keysym", None)
                if not isinstance(number, str): return None
                if number not in set("123456789"): return None
                if CONTROL_NUMBERS_RESTRICT:
                    idx:int = min(len(self.pages), int(number)) - 1
                else:
                    idx:int = int(number) - 1
                if 0 <= idx < self.notches.number_of_pages:
                    self.notches.focus_idx(idx)
                return "break"
            for i in range(1, 10):
                for on in (f"<Control-KeyPress-{i}>", f"<Alt-KeyPress-{i}>"):
                    frame.bind(on, _control_numbers, add=True)
        if CONTROL_T:
            def control_t(event:tk.Event) -> str:
                if event.state&1:
                    print("Control-Shift-t not implemented.")
                    return ""
                self.notebook.event_generate("<<Tab-Create>>")
                return "break"
            frame.bind("<Control-t>", control_t, add=True)
            frame.bind("<Control-T>", control_t, add=True)
        if CONTROL_W:
            def control_w(event:tk.Event) -> str:
                kwargs:dict = dict(state=event.state, x=event.x, y=event.y)
                if (event.state&1) or (self.notches.curr_page is None):
                    self.notebook.event_generate("<<Close-All>>", **kwargs)
                    return ""
                self.notebook.tab_destroy(self.notches.curr_page)
                return "break"
            frame.bind("<Control-w>", control_w, add=True)
            frame.bind("<Control-W>", control_w, add=True)
            frame.bind("<<Close-Tab>>", control_w, add=True)
        return self

    def rename(self, title:str) -> NotebookPage:
        super().config(text=title)
        return self

    def close(self) -> None:
        self.notebook.tab_destroy(self)

    def focus(self) -> NotebookPage:
        self.notebook.tab_focus(self)
        return self

    def disappear(self) -> None:
        self.page_frame.pack_forget()

    def appear(self) -> None:
        self.page_frame.pack(fill="both", expand=True)

    def _close(self) -> None:
        self.page_frame.destroy()
        super().destroy()


class Notebook(tk.Frame):
    __slots__ = "pages", "next_id", "notches", "bottom", "on_try_close"

    def __init__(self, master:tk.Misc, min_tab_notch_size:int=0,
                 font:str="TkTextFont", scrolled:bool=True,
                 **kwargs) -> Notebook:
        self.on_try_close:Callable[NotebookPage,Break] = lambda page: False

        super().__init__(master, **WIDGET_KWARGS, bg="black")
        self.notches:TabNotches = TabNotches(self, min_width=min_tab_notch_size,
                                             font=font, scrolled=scrolled)
        self.notches.pack(fill="both")
        self.bottom:tk.Frame = tk.Frame(self, **WIDGET_KWARGS, bg="black")
        self.bottom.pack(fill="both", expand=True)

    # Enable/Disable the add tab notch
    def disable_new_tab(self) -> None:
        self.notches.disable_new_tab()

    def enable_new_tab(self) -> None:
        self.notches.enable_new_tab()

    # Create a tab
    def tab_create(self) -> NotebookPage:
        frame:tk.Frame = tk.Frame(self.bottom, **WIDGET_KWARGS, bg="black")
        page:NotebookPage = self.notches.add(page_frame=frame, notebook=self)
        return page.rename("Untitled")

    # Iterate over all of the pages
    def iter_pages(self) -> Iterator[NotebookPage]:
        yield from self.notches.iter_pages()

    @property
    def number_of_pages(self) -> int:
        return self.notches.number_of_pages

    # Currently focused page
    @property
    def curr_page(self) -> NotebookPage|None:
        return self.notches.curr_page

    # Focus methods
    def switch_prev_tab(self, _:tk.Event=None) -> str:
        self.notches.focus_prev()
        return "break"

    def switch_next_tab(self, _:tk.Event=None) -> str:
        self.notches.focus_next()
        return "break"

    def tab_focus(self, page:NotebookPage|None) -> None:
        self.notches.focus_page(page)

    # Destroy tab
    def tab_destroy(self, page:NotebookPage) -> None:
        self.notches.page_destroy(page)

    # Scroll notches to see a specific page
    def see(self, page:NotebookPage) -> None:
        self.notches.see(page)


if __name__ == "__main__a":
    def add_tab(title:str) -> None:
        l = tk.Label(notebook, bg="black", fg="white", text=title)
        notebook.tab_create().rename(title).add_frame(l).focus()

    TAB_CONTROLS:bool = True
    CONTROL_NUMBERS_CONTROLS:bool = True

    root = tk.Tk()
    root.geometry("274x59")
    notebook = Notebook(root, 50)
    notebook.pack(fill="both", expand=True)
    notebook.on_try_close = lambda p: False

    add_tab("longgggggggggggggg")
    add_tab("s")
    add_tab("longgggggggggggggg2")

    nb, nts = notebook, notebook.notches
    root.mainloop()


if __name__ == "__main__":
    page_to_text = {}

    def add_tab(_:tk.Event=None) -> NotebookPage:
        """
        The + button is pressed. Feel free to not do anything here.
        """
        t = tk.Text(notebook, bg="black", fg="white", insertbackground="white",
                    takefocus=False, highlightthickness=0, bd=0)
        t.insert("end", notebook.number_of_pages+1)
        page = notebook.tab_create()
        page_to_text[page] = t
        page.rename(title=f"Tab number {notebook.number_of_pages}")
        page.add_frame(t).focus()
        return page

    def selected(_:tk.Event=None) -> None:
        print("Focused a page")
        if notebook.curr_page is None:
            return None
        page_to_text[notebook.curr_page].focus_set()

    def on_try_close(page:NotebookPage) -> Break:
        """
        Return True to stop the tab from being closed.
        """
        print(f"Tried closing a page")
        return list(notebook.iter_pages()).index(page)%2

    def close_all(event:tk.Event) -> None:
        """
        Control-Shift-w was pressed or Control-w and there are no more
        tabs to close. Feel free to do nothing here.
        """
        if event.state&1:
            print("Control-Shift-w")
        else:
            print("Closing notebook as no tabs are open")
        root.destroy()

    # Control-Tab and Control-Shift-Tab
    TAB_CONTROLS:bool = True
    # Control-{number} switches tabs
    CONTROL_NUMBERS_CONTROLS:bool = True
    # What to do with Control-5 if there are only 2 tabs open
    CONTROL_NUMBERS_RESTRICT:bool = False
    # Should Control-t/Control-w
    CONTROL_T:bool = True
    CONTROL_W:bool = True
    # Hide the scrollbar when there aren't a lot of tabs open:
    HIDE_SCROLLBAR:bool = True

    root = tk.Tk()
    notebook = Notebook(root)
    # notebook.disable_new_tab()
    notebook.pack(fill="both", expand=True)
    notebook.on_try_close = on_try_close
    notebook.bind("<<Tab-Switched>>", selected)
    notebook.bind("<<Tab-Create>>", add_tab)
    notebook.bind("<<Close-All>>", close_all)

    for i in range(5):
        page:NotebookPage = add_tab()
        can_drag:bool = (i != 2) # Disable dragging of 3rd tab
        page.config(can_drag=can_drag)

    nb, nts = notebook, notebook.notches
    root.bind_all("<Button-3>", lambda e: print(e.widget._w))
    root.mainloop()