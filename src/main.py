from __future__ import annotations
from tkinter.filedialog import askdirectory
import tkinter as tk
import os

from file_explorer.expanded_explorer import ExpandedExplorer, isfolder
from file_explorer.bindframe import make_bind_frame
from bettertk.notebook import Notebook
from bettertk.betterframe import BetterFrame
from bettertk.betterscrollbar import BetterScrollBarVertical, \
                                     BetterScrollBarHorizontal
from bettertk.messagebox import askyesno, tell as telluser
from bettertk import BetterTk
from plugins import PythonPlugin, VirtualEvents
from settings.settings import curr as settings


class App:
    __slots__ = "root", "explorer", "notebook", "text_to_page", \
                "explorer_frame"

    def __init__(self) -> App:
        self.text_to_page:dict[tk.Text:NotebookPage] = {}
        self.root:BetterTk = BetterTk()
        self.root.title("Bismuth-184")
        self.root.iconphoto(False, "sprites/Bismuth_184.ico")
        self.root.protocol("WM_DELETE_WINDOW", self.root_close)
        self.root.geometry(f"+{settings.window.x}+{settings.window.y}")
        pannedwindow = tk.PanedWindow(self.root, orient="horizontal", bd=0,
                                      height=settings.window.height,
                                      sashwidth=4)
        pannedwindow.pack(fill="both", expand=True)

        self.notebook:Notebook = Notebook(pannedwindow)
        self.notebook.bind("<<Tab-Create>>", lambda _: self.new_tab())
        self.notebook.on_try_close = self.close_tab

        left_frame:tk.Frame = tk.Frame(pannedwindow, bd=0, bg="black",
                                       highlightthickness=0)
        add = tk.Button(left_frame, text="Add Folder", bg="black", fg="white",
                        activebackground="grey", activeforeground="white",
                        highlightthickness=0, takefocus=False,
                        command=self.explorer_add_folder, relief="flat")
        add.grid(row=1, column=1, sticky="news")
        rem = tk.Button(left_frame, text="Remove Folder", bg="black", fg="white",
                        activebackground="grey", activeforeground="white",
                        highlightthickness=0, takefocus=False,
                        command=self.explorer_remove_folder, relief="flat")
        rem.grid(row=1, column=2, sticky="news")
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure((1, 2), weight=1)
        self.explorer_frame = BetterFrame(left_frame, hscroll=True,
                                          vscroll=True, bg="black",
                                     HScrollBarClass=BetterScrollBarHorizontal,
                                     VScrollBarClass=BetterScrollBarVertical,
                                     scroll_speed=1)
        self.explorer_frame.grid(row=2, column=1, columnspan=2, sticky="news")
        if settings.explorer.hide_h_scroll:
            self.explorer_frame.h_scrollbar.hide:bool = True
        if settings.explorer.hide_v_scroll:
            self.explorer_frame.v_scrollbar.hide:bool = True
        # scrollbar_kwargs=dict(width=4),
        VirtualEvents(self.explorer_frame) # Must be before the BindFrame
        make_bind_frame(self.explorer_frame)
        self.explorer:ExpandedExplorer = ExpandedExplorer(self.explorer_frame)
        self.explorer_frame.bind("<<Explorer-Open>>", self.open_tab)

        pannedwindow.add(left_frame, sticky="news",
                         width=settings.explorer.width)
        pannedwindow.add(self.notebook, sticky="news",
                         width=settings.notebook.width)

        self._set_notebook_state(settings.notebook.open)
        self._set_explorer_state(settings.explorer.added,
                                 settings.explorer.expanded)
        for text, page in self.text_to_page.items():
            if text.filepath == settings.window.focused_text:
                page.focus()
                break

    def new_tab(self, filepath:str=None) -> tk.Text:
        text = tk.Text(self.notebook, highlightthickness=0, bd=0)
        text.bind("<Control-W>", self.control_w)
        text.bind("<Control-w>", self.control_w)
        if not filepath:
            text.insert("end", PythonPlugin.DEFAULT_CODE)
        page = self.notebook.tab_create().add_frame(text).focus()
        text.plugin = PythonPlugin(text)
        text.plugin.attach()
        text.focus_set()
        text.filepath:str = None
        text.saved:str = ""
        self.text_to_page[text] = page
        text.bind("<<Save-File>>", self.rename_tab, add=True)
        text.bind("<<Open-File>>", self.rename_tab, add=True)
        text.bind("<<Modified-Change>>", self.rename_tab, add=True)
        text.bind("<<Unsaved-Open>>", self.unsaved_open, add=True)
        if filepath:
            text.edit_modified(False)
            text.event_generate("<<Trigger-Open>>", data=(filepath,))
        else:
            text.edit_modified(True)
            text.event_generate("<<Modified-Change>>")
        return text

    def rename_tab(self, event:tk.Event) -> None:
        filename:str = self.get_filename(event.widget.filepath)
        if event.widget.edit_modified():
            filename:str = f"*{filename}*"
        self.text_to_page[event.widget].rename(filename)

    @staticmethod
    def get_filename(filepath:str) -> str:
        if filepath is None:
            return "Untitled"
        return filepath.split("/")[-1].split("\\")[-1]

    def control_w(self, event:tk.Event) -> str:
        # event.widget is useless here for some reason
        self.notebook.tab_destroy(self.notebook.curr_page)
        return "break"

    def close_tab(self, page:NotebookPage) -> bool:
        return self._close_tab(self.page_to_text(page))

    def _close_tab(self, text:tk.Text) -> bool:
        block:bool = True
        if text.edit_modified():
            title:str = "Close unsaved text?"
            msg:str = "Are you sure you want to\nclose this unsaved page?"
            block = not askyesno(self.root, title=title, message=msg,
                                 center=True, icon="warning",
                                 center_widget=text)
        if not block:
            self.text_to_page.pop(text)
        return block

    def page_to_text(self, page:NotebookPage) -> tk.Text:
        for text, p in self.text_to_page.items():
            if p == page:
                return text
        raise KeyError("InternalError")

    def unsaved_open(self, event:tk.Event) -> str:
        title:str = "Discard changes to this file?"
        msg:str = "You havn't saved this file. Are you sure you\n" \
                  "want to continue and discard the changes?"
        ret:bool = askyesno(self.root, title=title, message=msg, center=True,
                            icon="warning", center_widget=event.widget)
        if ret:
            return ""
        # Return break if you want to cancel the open
        return "break"

    def open_tab(self, _:tk.Event) -> None:
        path:str = self.explorer.selected.item.fullpath
        for text, page in self.text_to_page.items():
            if text.filepath == path:
                page.focus()
                return None
        self.new_tab(path)

    def root_close(self) -> None:
        _, x, y = self.root.geometry().split("+")
        added, expanded = self._get_explorer_state()
        true_explorer_frame:tk.Frame = self.explorer_frame.master_frame
        curr_text:tk.Text = self.page_to_text(self.notebook.curr_page)

        settings.window.update(height=self.root.winfo_height(), x=x, y=y)
        settings.explorer.update(width=true_explorer_frame.winfo_width())
        settings.notebook.update(width=self.notebook.winfo_width())
        settings.notebook.update(open=self._get_notebook_state())
        settings.explorer.update(added=added, expanded=expanded)
        settings.window.update(focused_text=curr_text.filepath)
        settings.save()
        self.root.destroy()

    def _get_notebook_state(self) -> list[tuple]:
        opened:list[tuple] = []
        for text in self.text_to_page:
            file:str = text.filepath
            yview:str = text.yview()[0]
            xview:str = text.xview()[0]
            insert:str = text.index("insert")
            saved:str = text.saved
            modified:str = text.edit_modified()
            if modified:
                data:str = text.get("1.0", "end").removesuffix("\n")
            else:
                data:str = None
            opened.append([file, data, yview, xview, insert, saved, modified])
        return opened

    def _set_notebook_state(self, opened:list[tuple]) -> None:
        files:set[str] = set()
        for file, data, yview, xview, insert, saved, modified in opened:
            if file is not None:
                if file in files:
                    title:str = "Single file in multiple tabs"
                    msg:str = "Please don't open the same file in multiple\n" \
                              "tabs as that can cause problems for this editor"
                    telluser(self.root, title=title, message=msg, center=True,
                             icon="warning")
                files.add(file)
                if not os.path.exists(file):
                    continue
                if not os.path.isfile(file):
                    continue
            text:str = self.new_tab(file)
            if modified:
                text.delete("0.0", "end")
                text.insert("end", data)
                text.edit_modified(True)
                text.edit_reset()
                text.edit_separator()
                text.event_generate("<<Modified-Change>>")
            if modified and (file is not None):
                with open(file, "r") as fd:
                    if saved != fd.read():
                        title:str = "Merge Conflict"
                        msg:str = f"The file {file} has been\nmodified on " \
                                  "you system and there are changes in this " \
                                  "editor.\nThis means that you have a " \
                                  "merge conflict. Good luck resolving it."
                        telluser(self.root, title=title, message=msg,
                                 center=True, icon="warning",
                                 center_widget=text, block=False)
            text.event_generate("<<Move-Insert>>", data=(insert,))
            text.mark_set("insert", insert)
            text.xview("moveto", xview)
            text.yview("moveto", yview)

    def explorer_remove_folder(self) -> None:
        if self.explorer.selected is None:
            return None
        selected:Item = self.explorer.selected.item
        if selected not in self.explorer.root.children:
            return None
        self.explorer.remove(selected)

    def explorer_add_folder(self) -> None:
        path:str = askdirectory(master=self.root)
        if not path:
            return None
        self.explorer.add(path)

    def _get_explorer_state(self) -> tuple[list[str],list[str]]:
        getpath = lambda item: item.fullpath
        added:list[str] = list(map(getpath, self.explorer.root.children))
        expanded:list[str] = []
        for item, _ in self.explorer.root.recurse_children(withself=False):
            if isfolder(item) and item.expanded:
                expanded.append(item.fullpath)
        return added, expanded

    def _set_explorer_state(self, added:list[str], expanded:list[str]) -> None:
        for path in added:
            self.explorer.add(path)
        expanded:set[str] = set(expanded)
        for item, _ in self.explorer.root.recurse_children(withself=False):
            if isfolder(item) and (item.fullpath in expanded):
                self.explorer.expand(item)

    def mainloop(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app:App = App()

    try:
        import sys
        sys.stdin.fileno()
        app.mainloop()
    except:
        pass
