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
NOTCH_BG:str = "#444444"
NOT_DRAG_DIST:int = 10
BUTTON1_TK_STATE:int = 256


class TabNotch(tk.Canvas):
    __slots__ = "text_id", "text", "page", "rrect_id", "width", "min_size", \
                "can_drag"
    PADX:int = 7

    def __init__(self, master:TabNotches, min_size:int=0,
                 font:str="TkTextFont") -> TabNotch:
        super().__init__(master, **WIDGET_KWARGS, bg=NOTCH_BG)
        self.text_id:int = super().create_text((0,0), text="", anchor="nw",
                                               fill="white", font=font)
        self.min_size:int = min_size
        self.can_drag:bool = True
        self.focused:bool = False
        self.rrect_id:int = None
        self.width:int = 0
        self.text:str = None
        super().bind("<Button-1>", lambda e: master._clicked(self), add=True)
        super().bind("<Button-2>", lambda e: master._close(self), add=True)

    def rename(self, text:str) -> None:
        if self.text == text:
            return None
        self.master._renaming(self, lambda: self._rename(text))

    def _rename(self, text:str) -> None:
        self.text:str = text
        super().itemconfig(self.text_id, text=text)
        x1, y1, x2, y2 = super().bbox(self.text_id)
        text_width:int = x2-x1
        width:int = max(self.min_size, text_width)
        height:int = y2-y1
        text_x:int = self.PADX + (width-text_width)//2
        super().moveto(self.text_id, text_x, height/2)
        super().config(width=width+2*self.PADX, height=2*height)
        self.width:int = width+2*self.PADX
        if self.rrect_id is not None:
            self.tell_focused(force_redraw=True)

    def tell_focused(self, *, force_redraw:bool=False) -> None:
        if self.focused and (not force_redraw):
            return None
        if self.rrect_id is not None:
            super().delete(self.rrect_id)
        x1, y1, x2, y2 = super().bbox(self.text_id)
        width:int = max(self.min_size, x2-x1)
        height:int = y2-y1
        points:tuple[int] = (0, 0, width+2*self.PADX, 3*height)
        self.rrect_id:int = super().create_round_rectangle(*points,
                                                           radius=25,
                                                           fill="black")
        super().tag_lower(self.rrect_id)
        self.focused:bool = True

    def tell_unfocused(self) -> None:
        if self.rrect_id is not None:
            super().delete(self.rrect_id)
            self.focused:bool = False


class TabNotches(BetterFrame):
    __slots__ = "add_notch", "min_size", "notebook", "notches", "tmp_notch", \
                "notch_dragging", "dragging", "dragx", "on_reshuffle", "font"

    def __init__(self, notebook:Notebook, min_size:int=0,
                 font:str="TkTextFont") -> TabNotches:
        self.font:str|Font = font
        self.on_reshuffle:Function[None] = lambda: None
        self.notebook:Notebook = notebook
        super().__init__(notebook, bg=NOTCH_BG, hscroll=True, vscroll=False,
                         HScrollBarClass=BetterScrollBarHorizontal,
                         hscrolltop=True, scrollbar_kwargs={"thickness":4})
        self.h_scrollbar.hide:bool = HIDE_SCROLLBAR
        self.notches:list[TabNotch] = []
        self.notch_dragging:bool = None
        self.add_notch:TabNotch = None
        self.min_size:int = min_size
        self.dragging:bool = False
        self.enable_new_tab()
        height:int = self.add_notch.winfo_reqheight()
        if hasattr(self, "resize"):
            # Unimplemented - depricated
            super().resize(height=height)
        else:
            super().config(height=height)
        self.tmp_notch:tk.Frame = tk.Frame(self, bg=NOTCH_BG, height=height,
                                           highlightthickness=0, bd=0)
        make_bind_frame(self)
        self.bind("<ButtonPress-1>", self._start_dragging, add=True)
        self.bind_all("<B1-Motion>", self._drag, add=True)
        self.bind_all("<Motion>", self._drag, add=True)
        self.bind_all("<ButtonRelease-1>", self._end_dragging, add=True)

    def disable_new_tab(self) -> None:
        if self.add_notch is None: return None
        self.add_notch.destroy()
        self.add_notch:TabNotch = None

    def enable_new_tab(self) -> None:
        if self.add_notch is not None: return None
        self.add_notch:TabNotch = TabNotch(self, font=self.font)
        self.add_notch.grid(row=1, column=len(self.notches)+1)
        self.add_notch.rename("+")

    def add(self) -> TabNotch:
        notch:TabNotch = TabNotch(self, min_size=self.min_size, font=self.font)
        notch.grid(row=1, column=len(self.notches))
        if self.add_notch is not None:
            self.add_notch.grid(row=1, column=len(self.notches)+1)
        self.notches.append(notch)
        return notch

    def _clicked(self, notch:TabNotch) -> None:
        if notch == self.add_notch:
            self.notebook.event_generate("<<Tab-Create>>")
        else:
            notch.page.focus()

    def _close(self, notch:TabNotch) -> None:
        if notch != self.add_notch:
            notch.page.close()

    def remove(self, notch:TabNotch) -> None:
        assert notch in self.notches, "InternalError"
        idx:int = self.notches.index(notch)
        self.notches.pop(idx)
        for i in range(idx, len(self.notches)):
            self.notches[i].grid(row=1, column=i)

    def _start_dragging(self, event:tk.Event) -> None:
        if not isinstance(event.widget, TabNotch):
            return None
        if event.widget == self.add_notch:
            return None
        self.notch_dragging:TabNotch = event.widget
        if not self.notch_dragging.can_drag:
            self.notch_dragging:TabNotch = None
        self.dragx:int = event.x
        return "break"

    def _end_dragging(self, event:tk.Event=None) -> str:
        if self.notch_dragging is None:
            return None
        if self.dragging:
            self.tmp_notch.grid_forget()
            self.notch_dragging.grid(row=1, column=self.tmp_notch.idx)
            self.notches[self.tmp_notch.idx] = self.notch_dragging
        self.notch_dragging:TabNotch = None
        self.dragging:bool = False
        return "break"

    def _drag(self, event:tk.Event) -> str:
        if self.notch_dragging is None:
            return None
        if not (event.state & BUTTON1_TK_STATE):
            self._end_dragging()
            return None
        if not self.dragging:
            if abs(event.x-self.dragx) < NOT_DRAG_DIST:
                return None
            self.dragging:bool = True
            self.tmp_notch.x:int = self._get_start_x(self.notch_dragging)
            width:int = self.notch_dragging.winfo_width()
            self.tmp_notch.width=width
            self.tmp_notch.config(width=width)
            idx:int = self.notches.index(self.notch_dragging)
            self.tmp_notch.page = self.notch_dragging.page
            self.tmp_notch.grid(row=1, column=idx)
            self.tmp_notch.idx:int = idx
            tk.Misc.lift(self.notch_dragging)
            self.notches[idx] = self.tmp_notch

        x:int = event.x_root - super().winfo_rootx()
        delta:int = self._calculate_idx_delta(x-self.dragx)
        if delta != 0:
            self._reshiffle(delta)
        self.notch_dragging.place(x=x-self.dragx, y=0)
        return "break"

    def _get_start_x(self, notch:TabNotch) -> int:
        total:int = 0
        for n in self.notches:
            if n == notch:
                return total
            total += n.width
        raise RuntimeError("InternalError: Notch not in self.notches???")

    def _calculate_idx_delta(self, notch_start:int) -> int:
        if self.tmp_notch.winfo_x() < self.notch_dragging.winfo_x():
            # dragging =>
            if self.tmp_notch == self.notches[-1]:
                return 0
            next_notch:TabNotch = self.notches[self.tmp_notch.idx+1]
            notch_end:int = notch_start + self.notch_dragging.width
            next_notch_start:int = self.tmp_notch.x + self.tmp_notch.width
            if notch_end > next_notch_start+next_notch.width/2:
                return +1
            else:
                return 0
        else:
            # dragging <=
            if self.tmp_notch == self.notches[0]:
                return 0
            prev_notch:TabNotch = self.notches[self.tmp_notch.idx-1]
            prev_notch_half:int = self.tmp_notch.x - prev_notch.width/2
            if notch_start < prev_notch_half:
                return -1
            else:
                return 0

    def _reshiffle(self, delta:int) -> None:
        idx:int = self.tmp_notch.idx
        self.tmp_notch.idx += delta
        self._swap(self.notches, idx, idx+delta)
        self.tmp_notch.x += self.notches[idx].width * delta
        for i in (idx, idx+delta):
            self.notches[i].grid(row=1, column=i)
        self.on_reshuffle(idx, idx+delta)

    @staticmethod
    def _swap(array:list, idxa:int, idxb:int):
        array[idxa], array[idxb] = array[idxb], array[idxa]

    def see(self, idx:int) -> None:
        assert isinstance(idx, int), "TypeError"
        # If idx == len(self.notches): see(add_button_notch)
        assert 0 <= idx <= len(self.notches), "ValueError"
        # Get information
        super().update_idletasks()
        full_width:int = super().winfo_width()
        curr_low, curr_high = super().xview()
        curr_low, curr_high = float(curr_low), float(curr_high)
        # Calculate the minx and maxx of the notch
        minx:int = 0
        for i in range(idx):
            minx += self.notches[i].width
        if idx == len(self.notches):
            maxx:int = full_width
        else:
            maxx:int = minx + self.notches[idx].width
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

    def _renaming(self, notch:TabNotch, rename:Callable) -> None:
        curr_high:float = float(super().xview()[1])
        rename()
        if curr_high > 0.999:
            self.see(len(self.notches))


CONTROL_T:bool = False
CONTROL_W:bool = False
TAB_CONTROLS:bool = True
CONTROL_NUMBERS_CONTROLS:bool = False
CONTROL_NUMBERS_RESTRICT:bool = False
HIDE_SCROLLBAR:bool = True

class NotebookPage:
    __slots__ = "notebook", "frame", "notch"

    def __init__(self, notebook:Notebook, frame:tk.Frame, notch:TabNotch):
        self.notebook:Notebook = notebook
        self.notch:TabNotch = notch
        self.frame:tk.Misc = frame

    def add_frame(self, frame:tk.Misc) -> NotebookPage:
        frame.pack(in_=self.frame, fill="both", expand=True)
        if TAB_CONTROLS:
            #frame.bind("<Control-Key><Tab>", self.notebook.switch_next_tab)
            frame.bind("<Control-Tab>", self.notebook.switch_next_tab, add=True)
            if IS_UNIX:
                sequence:str = "<Control-ISO_Left_Tab>"
            else:
                sequence:str = "<Control-Shift-Tab>"
            frame.bind(sequence, self.notebook.switch_prev_tab, add=True)
        if CONTROL_NUMBERS_CONTROLS:
            for i in range(1, 10):
                for on in (f"<Control-KeyPress-{i}>", f"<Alt-KeyPress-{i}>"):
                    frame.bind(on, self.notebook.control_numbers, add=True)
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
                if (event.state&1) or (self.notebook.curr_page is None):
                    self.notebook.event_generate("<<Close-All>>", **kwargs)
                    return ""
                self.notebook.tab_destroy(self.notebook.curr_page)
                return "break"
            frame.bind("<Control-w>", control_w, add=True)
            frame.bind("<Control-W>", control_w, add=True)
            frame.bind("<<Close-Tab>>", control_w, add=True)
        return self

    def rename(self, title:str) -> NotebookPage:
        self.notch.rename(title)
        return self

    def close(self) -> None:
        self.notebook.tab_destroy(self)

    def _close(self) -> None:
        self.notch.destroy()
        self.frame.destroy()

    def focus(self) -> NotebookPage:
        self.notebook._tab_switch_to(self)
        return self


class Notebook(tk.Frame):
    __slots__ = "pages", "next_id", "curr_page", "notches", "bottom", \
                "on_try_close"

    def __init__(self, master:tk.Misc, min_tab_notch_size:int=0,
                 font:str="TkTextFont") -> Notebook:
        self.pages:list[NotebookPage] = []
        self.curr_page:NotebookPage = None
        self.on_try_close:Function[NotebookPage,Break] = lambda page: False

        super().__init__(master, **WIDGET_KWARGS, bg="black")
        self.notches:TabNotches = TabNotches(self, min_tab_notch_size,
                                             font=font)
        self.notches.pack(fill="both")
        self.notches.on_reshuffle = self.update_pages_list
        self.bottom:tk.Frame = tk.Frame(self, **WIDGET_KWARGS, bg="black")
        self.bottom.pack(fill="both", expand=True)

    def disable_new_tab(self) -> None:
        self.notches.disable_new_tab()

    def enable_new_tab(self) -> None:
        self.notches.enable_new_tab()

    def tab_create(self) -> NotebookPage:
        notch:TabNotch = self.notches.add()
        notch.rename("Untitled")
        frame:tk.Frame = tk.Frame(self.bottom, **WIDGET_KWARGS, bg="black")
        page:NotebookPage = NotebookPage(self, frame=frame, notch=notch)
        notch.page:NotebookPage = page
        self.pages.append(page)
        return page

    def iter_pages(self) -> Iterator[NotebookPage]:
        for notch in self.notches.notches:
            yield notch.page

    def _tab_switch_to(self, page:NotebookPage) -> None:
        if page == self.curr_page:
            return None
        if self.curr_page is not None:
            self.curr_page.notch.tell_unfocused()
            self.curr_page.frame.pack_forget()
        if page is not None:
            page.frame.pack(fill="both", expand=True)
            page.notch.tell_focused()
        self.curr_page:NotebookPage = page
        super().event_generate("<<Tab-Switched>>")
        self.see(self.curr_page)

    def switch_prev_tab(self, event:tk.Event=None) -> str:
        page:NotebookPage = self._switch_next_prev_tab(strides=-1, default=-1)
        if page == self.curr_page:
            page:NotebookPage = None
        self._tab_switch_to(page)
        return "break"

    def switch_next_tab(self, event:tk.Event=None) -> str:
        page:NotebookPage = self._switch_next_prev_tab(strides=+1, default=0)
        if page == self.curr_page:
            page:NotebookPage = None
        self._tab_switch_to(page)
        return "break"

    def _switch_next_prev_tab(self, strides:int, default:int) -> NotebookPage:
        if self.curr_page is None:
            if len(self.pages) == 0:
                return None
            return self.pages[default]
        else:
            idx:int = self.pages.index(self.curr_page) + strides
            return self.pages[idx%len(self.pages)]

    def tab_destroy(self, page:NotebookPage) -> None:
        if self.on_try_close(page):
            return None
        if self.curr_page == page:
            if self.pages[0] == page:
                self.switch_next_tab()
            else:
                self.switch_prev_tab()
        assert self.curr_page != page, "SanityCheck"
        assert self.curr_page in self.pages+[None], "SanityCheck"
        page._close()
        self.pages.remove(page)
        self.notches.remove(page.notch)

    def update_pages_list(self, idxa:int, idxb:int) -> None:
        # TabNotches._reshuffle shuffled the pages so now we have to
        #  update self.pages
        self.notches._swap(self.pages, idxa, idxb)

    def control_numbers(self, event:tk.Event) -> str:
        number:str = getattr(event, "keysym", None)
        if not isinstance(number, str):
            return None
        if number not in set("123456789"):
            return None
        if CONTROL_NUMBERS_RESTRICT:
            idx:int = min(len(self.pages), int(number)) - 1
        else:
            idx:int = int(number) - 1
        if not (0 <= idx < len(self.pages)):
            return None
        self.pages[idx].focus()
        return "break"

    def see(self, page:NotebookPage) -> None:
        assert page in self.pages, "Page not in self.pages?"
        idx:int = self.pages.index(page)
        see_add:bool = idx == len(self.pages)-1
        self.notches.see(idx+see_add)


if __name__ == "__main__":
    def add_tab(title:str) -> None:
        l = tk.Label(notebook, bg="black", fg="white", text=title)
        notebook.tab_create().rename(title=title).add_frame(l).focus()

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
        t.insert("end", len(notebook.pages)+1)
        page = notebook.tab_create()
        page_to_text[page] = t
        page.rename(title=f"Tab number {len(notebook.pages)}")
        page.add_frame(t).focus()
        return page

    def selected(_:tk.Event=None) -> None:
        """
        Do what you will.
        """
        if notebook.curr_page is None:
            return None
        page_to_text[notebook.curr_page].focus_set()

    def on_try_close(page:NotebookPage) -> Break:
        """
        Return True to stop the tab from being closed.
        """
        return notebook.pages.index(page)%2

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
        page.notch.can_drag:bool = i == 2 # Disable dragging of 3rd tab

    nb, nts = notebook, notebook.notches
    root.bind_all("<Button-3>", lambda e: print(e.widget._w))
    root.mainloop()