from __future__ import annotations
import tkinter as tk

try:
    from betterframe import BetterFrame
    from betterscrollbar import BetterScrollBarHorizontal
except ImportError:
    from .betterframe import BetterFrame
    from .betterscrollbar import BetterScrollBarHorizontal

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


WIDGET_KWARGS:dict = dict(highlightthickness=0, bd=0, takefocus=False)
NOTCH_BG:str = "#444444"


class TabNotch(tk.Canvas):
    __slots__ = "text_id", "text", "page", "rrect_id"
    PADX:int = 7

    def __init__(self, master:TabNotches) -> TabNotch:
        super().__init__(master, **WIDGET_KWARGS, height=1, width=1,
                         bg=NOTCH_BG)
        self.text_id:int = super().create_text((0,0), text="", anchor="nw",
                                               fill="white")
        self.rrect_id:int = None
        self.text:str = None
        super().bind("<Button-1>", lambda e: master.clicked(self))
        super().bind("<Button-2>", lambda e: master.close(self))

    def rename(self, text:str) -> None:
        if self.text == text:
            return None
        self.text:str = text
        super().itemconfig(self.text_id, text=text)
        x1, y1, x2, y2 = super().bbox(self.text_id)
        width:int = x2-x1
        height:int = y2-y1
        super().moveto(self.text_id, self.PADX, height/2)
        super().config(width=width+2*self.PADX, height=2*height)
        if self.rrect_id is not None:
            self.tell_focused()

    def tell_focused(self) -> None:
        if self.rrect_id is not None:
            super().delete(self.rrect_id)
        x1, y1, x2, y2 = super().bbox(self.text_id)
        width:int = x2-x1
        height:int = y2-y1
        points:tuple[int] = (0, 0, width+2*self.PADX, 3*height)
        self.rrect_id:int = super().create_round_rectangle(*points,
                                                           radius=25,
                                                           fill="black")
        super().tag_lower(self.rrect_id)

    def tell_unfocused(self) -> None:
        if self.rrect_id is not None:
            super().delete(self.rrect_id)


class TabNotches(BetterFrame):
    __slots__ = "add_notch", "length", "notebook"

    def __init__(self, notebook:Notebook) -> TabNotches:
        self.notebook:Notebook = notebook
        super().__init__(notebook, bg=NOTCH_BG, hscroll=True, vscroll=False,
                         HScrollBarClass=BetterScrollBarHorizontal,
                         hscrolltop=True, scrollbar_kwargs=dict(width=4))
        self.add_notch:TabNotch = TabNotch(self)
        self.add_notch.grid(row=1, column=1)
        self.add_notch.rename("+")
        self.h_scrollbar.hide:bool = True
        self.length:int = 0
        super().resize(height=self.add_notch.winfo_reqheight())

    def add(self) -> TabNotch:
        self.length += 1
        notch:TabNotch = TabNotch(self)
        notch.grid(row=1, column=self.length)
        self.add_notch.grid(row=1, column=self.length+1)
        return notch

    def clicked(self, notch:TabNotch) -> None:
        if notch == self.add_notch:
            self.notebook.event_generate("<<Tab-Create>>")
        else:
            notch.page.focus()

    def close(self, notch:TabNotch) -> None:
        if notch != self.add_notch:
            notch.page.close()


class NotebookPage:
    __slots__ = "notebook", "frame", "notch"

    def __init__(self, notebook:Notebook, frame:tk.Frame, notch:TabNotch):
        self.notebook:Notebook = notebook
        self.notch:TabNotch = notch
        self.frame:tk.Misc = frame

    def add_frame(self, frame:tk.Frame) -> NotebookPage:
        frame.pack(in_=self.frame, fill="both", expand=True)
        #frame.bind("<Control-Key><Tab>", self.notebook.switch_next_tab)
        frame.bind("<Control-Tab>", self.notebook.switch_next_tab)
        frame.bind("<Control-ISO_Left_Tab>", self.notebook.switch_prev_tab)
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

    def __init__(self, master:tk.Misc) -> Notebook:
        self.pages:list[NotebookPage] = []
        self.curr_page:NotebookPage = None
        self.on_try_close = None

        super().__init__(master, **WIDGET_KWARGS, bg="black")
        self.notches:TabNotches = TabNotches(self)
        self.notches.pack(fill="both")
        self.bottom:tk.Frame = tk.Frame(self, **WIDGET_KWARGS, bg="black")
        self.bottom.pack(fill="both", expand=True)

    def tab_create(self) -> NotebookPage:
        notch:TabNotch = self.notches.add()
        notch.rename("Untitled")
        frame:tk.Frame = tk.Frame(self.bottom, **WIDGET_KWARGS, bg="black")
        page:NotebookPage = NotebookPage(self, frame=frame, notch=notch)
        notch.page:NotebookPage = page
        self.pages.append(page)
        return page

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

    def switch_prev_tab(self, event:tk.Event=None) -> None:
        page:NotebookPage = self._switch_next_prev_tab(strides=-1, default=-1)
        if page == self.curr_page:
            page:NotebookPage = None
        self._tab_switch_to(page)

    def switch_next_tab(self, event:tk.Event=None) -> None:
        page:NotebookPage = self._switch_next_prev_tab(strides=+1, default=0)
        if page == self.curr_page:
            page:NotebookPage = None
        self._tab_switch_to(page)

    def _switch_next_prev_tab(self, strides:int, default:int) -> NotebookPage:
        if self.curr_page is None:
            if len(self.pages) == 0:
                return None
            return self.pages[default]
        else:
            idx:int = self.pages.index(self.curr_page) + strides
            return self.pages[idx%len(self.pages)]

    def tab_destroy(self, page:NotebookPage) -> None:
        if self.on_try_close is not None:
            res:bool = self.on_try_close(page)
            if res:
                return None
        if self.curr_page == page:
            self.switch_prev_tab()
        assert self.curr_page != page, "SanityCheck"
        assert self.curr_page in self.pages+[None], "SanityCheck"
        page._close()
        self.pages.remove(page)


if __name__ == "__main__":
    page_to_text = {}

    def add_tab() -> None:
        t = tk.Text(notebook, bg="black", fg="white", insertbackground="white",
                    takefocus=False, highlightthickness=0, bd=0)
        t.insert("end", len(notebook.pages)+1)
        page = notebook.tab_create()
        page_to_text[page] = t
        page.rename(title=f"Tab number {len(notebook.pages)}")
        page.add_frame(t).focus()

    def selected(e) -> None:
        if notebook.curr_page is None:
            return None
        page_to_text[notebook.curr_page].focus_set()

    def on_try_close(page) -> bool:
        for i, p in enumerate(page_to_text.keys()):
            if p == page:
                if i%2:
                    return True
                else:
                    page_to_text.pop(page)
                    return False

    root = tk.Tk()
    notebook = Notebook(root)
    notebook.pack(fill="both", expand=True)
    notebook.on_try_close = on_try_close

    notebook.bind("<<Tab-Create>>", lambda e: add_tab())
    notebook.bind("<<Tab-Switched>>", selected)

    add_tab()
    add_tab()
    add_tab()
    add_tab()
    add_tab()

    nb = notebook
    nts = nb.notches
