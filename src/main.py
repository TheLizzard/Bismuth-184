from __future__ import annotations
from tkinter.filedialog import askdirectory
from time import sleep, perf_counter
from tkinter import font
import tkinter as tk
import sys
import os
os.chdir(os.path.dirname(__file__))

DEBUG_TIME:bool = False
if DEBUG_TIME: from bettertk.messagebox import debug
if DEBUG_TIME: timer:list[float] = [perf_counter()]

from file_explorer.expanded_explorer import ExpandedExplorer, isfolder
from bettertk.betterframe import make_bind_frame
from bettertk.betterframe import BetterFrame
from bettertk.betterscrollbar import BetterScrollBarVertical, \
                                     BetterScrollBarHorizontal
from bettertk.messagebox import askyesno, tell as telluser
from bettertk import BetterTk, BetterTkSettings
from bettertk.bettertext import BetterText
from bettertk import notebook
from plugins import VirtualEvents
from settings.settings import curr as settings

from bettertk.terminaltk.ipc import IPC, Event, SIGUSR1, close_all_ipcs
from plugins import plugins


notebook.CONTROL_T:bool = True
notebook.CONTROL_W:bool = True
notebook.TAB_CONTROLS:bool = True
notebook.CONTROL_NUMBERS_CONTROLS:bool = True
notebook.CONTROL_NUMBERS_RESTRICT:bool = False
notebook.HIDE_SCROLLBAR:bool = False

TextClass = BetterText
# TextClass = tk.Text


class App:
    __slots__ = "root", "explorer", "notebook", "text_to_page", \
                "explorer_frame", "expand_later"

    def __init__(self, ipc:IPC) -> App:
        self.expand_later:set[str] = set()
        self.text_to_page:dict[BetterText:notebook.NotebookPage] = {}
        window_settings:BetterTkSettings = BetterTkSettings()
        window_settings.config(use_border=False)
        self.root:BetterTk = BetterTk(settings=window_settings,
                                      className="Bismuth-184")
        self.root.title("Bismuth-184")
        self.root.iconphoto(False, "sprites/Bismuth_184.ico")
        self.root.protocol("WM_DELETE_WINDOW", self.root_close)
        self.root.geometry(f"+{settings.window.x}+{settings.window.y}")
        if ipc:
            ipc.bind("focus", lambda e: self.focus_force(), threaded=False)
            ipc.bind("open", lambda e: self.open(e.data), threaded=False)
            self.root.after(100, self._check_ipc_queue, ipc)
        pannedwindow = tk.PanedWindow(self.root, orient="horizontal", bd=0,
                                      height=settings.window.height,
                                      sashwidth=4, bg="grey")
        pannedwindow.pack(fill="both", expand=True)

        self.notebook = notebook.Notebook(pannedwindow, 0,
                                          font=settings.window.font)
        self.notebook.bind("<<Tab-Create>>", lambda _: self.new_tab())
        self.notebook.bind("<<Tab-Switched>>", self.change_selected_tab)
        self.notebook.bind("<<Close-All>>", self.root_close)
        self.notebook.on_try_close = self.close_tab

        left_frame:tk.Frame = tk.Frame(pannedwindow, bd=0, bg="black",
                                       highlightthickness=0)
        left_frame.grid_columnconfigure((1,3), uniform=1)
        add = tk.Button(left_frame, text="Add Folder", bg="black", fg="white",
                        activebackground="grey", activeforeground="white",
                        highlightthickness=0, takefocus=False, relief="flat",
                        command=self.explorer_add_folder,
                        font=settings.window.font)
        add.grid(row=1, column=1, sticky="news")
        sep = tk.Canvas(left_frame, bg="grey", bd=0, highlightthickness=0,
                        width=1, height=1)
        sep.grid(row=1, column=2, sticky="news")
        sep = tk.Canvas(left_frame, bg="grey", bd=0, highlightthickness=0,
                        width=1, height=1)
        sep.grid(row=2, column=1, columnspan=3, sticky="news")
        rem = tk.Button(left_frame, text="Remove Folder", bg="black",
                        activebackground="grey", activeforeground="white",
                        highlightthickness=0, takefocus=False, fg="white",
                        command=self.explorer_remove_folder, relief="flat",
                        font=settings.window.font)
        rem.grid(row=1, column=3, sticky="news")
        left_frame.grid_rowconfigure(3, weight=1)
        left_frame.grid_columnconfigure((1, 3), weight=1)
        self.explorer_frame = BetterFrame(left_frame, hscroll=True,
                                          vscroll=True, bg="black",
                                     HScrollBarClass=BetterScrollBarHorizontal,
                                     VScrollBarClass=BetterScrollBarVertical,
                                     scroll_speed=1)
        self.explorer_frame.grid(row=3, column=1, columnspan=3, sticky="news")
        if settings.explorer.hide_h_scroll:
            self.explorer_frame.h_scrollbar.hide:bool = True
        if settings.explorer.hide_v_scroll:
            self.explorer_frame.v_scrollbar.hide:bool = True
        VirtualEvents(self.explorer_frame) # Must be before the BindFrame
        make_bind_frame(self.explorer_frame)
        self.explorer = ExpandedExplorer(self.explorer_frame,
                                         font=settings.explorer.font,
                                         monofont=settings.explorer.monofont)
        self.explorer_frame.bind("<<Explorer-Open>>", self.open_tab_explorer)
        self.explorer_frame.bind("<<Explorer-Expanded>>",
                                 lambda e: self._explorer_expand())

        pannedwindow.add(left_frame, sticky="news",
                         width=settings.explorer.width)
        pannedwindow.add(self.notebook, sticky="news",
                         width=settings.notebook.width)

    def init(self) -> None:
        self._set_notebook_state(settings.notebook.open)
        self._set_explorer_state(settings.explorer.added,
                                 settings.explorer.expanded)
        for text, page in self.text_to_page.items():
            if text.filepath == settings.window.focused_text:
                page.focus()
                break

    # Helpers
    @staticmethod
    def get_filename(filepath:str) -> str:
        if filepath is None:
            return "Untitled"
        return filepath.split("/")[-1].split("\\")[-1]

    def page_to_text(self, page:notebook.NotebookPage) -> BetterText:
        if page is None:
            return None
        for text, p in self.text_to_page.items():
            if p == page:
                return text
        raise KeyError("InternalError")

    # Tab management
    def new_tab(self, filepath:str=None) -> BetterText:
        page:NotebookPage = self.notebook.tab_create()
        text:BetterText = TextClass(page.frame, highlightthickness=0, bd=0,
                                    font=settings.editor.font)
        if isinstance(text, BetterText):
            text._xviewfix.dlineinfo.assume_monospaced()
            text.ignore_tags_with_bg:bool = True
        page.add_frame(text)
        text.filesystem_data:str = ""
        text.save_module:bool = True
        text.filepath:str = filepath
        self.text_to_page[text] = page
        page.focus()
        self.plugin_manage(text)
        text.focus_set()
        text.bind("<<Request-Save>>", self.request_save, add=True)
        text.bind("<<Request-Open>>", self.request_open, add=True)
        text.bind("<<Modified-Change>>", self.rename_tab, add=True)
        if filepath:
            text.filepath:str = filepath
            text.event_generate("<<Trigger-Open>>")
        else:
            text.insert("end", text.plugin.DEFAULT_CODE)
            text.event_generate("<<Clear-Separators>>")
            text.edit_modified(False)
            text.event_generate("<<Modified-Change>>")
        return text

    def plugin_manage(self, text:BetterText) -> None:
        old:Plugin = getattr(text, "plugin", None)
        for Plugin in plugins:
            if Plugin.can_handle(text.filepath):
                # If same plugin, nop
                if old.__class__ == Plugin:
                    return None
                # Detach the old
                if old is not None:
                    old.detach()
                # Attach the new
                Plugin(self.text_to_page[text].frame, text).attach()
                return None

    def change_selected_tab(self, event:tk.Event=None) -> None:
        if self.notebook.curr_page is None:
            return None
        self.page_to_text(self.notebook.curr_page).focus_set()

    def rename_tab(self, event:tk.Event) -> None:
        filename:str = self.get_filename(event.widget.filepath)
        if event.widget.edit_modified():
            filename:str = f"*{filename}*"
        self.text_to_page[event.widget].rename(filename)

    def close_tab(self, page:NotebookPage) -> bool:
        text:BetterText = self.page_to_text(page)
        if text.edit_modified():
            title:str = "Close unsaved text?"
            msg:str = "Are you sure you want to\nclose this unsaved page?"
            allow = askyesno(self.root, title=title, message=msg, center=True,
                             icon="warning", center_widget=text)
            if not allow:
                return True
        plugin:Plugin = getattr(text, "plugin", None)
        if plugin is not None:
            text.plugin.destroy()
        self.text_to_page.pop(text)
        text.destroy()
        return False

    def open_tab_explorer(self, _:tk.Event) -> None:
        path:str = self.explorer.selected.item.fullpath
        self.open_tab(path)

    def open_tab(self, path:str) -> None:
        for text, page in self.text_to_page.items():
            if text.filepath == path:
                page.focus()
                return None
        self.new_tab(path)

    def open(self, path:str) -> None:
        """
        Open a file/folder with this editor
        """
        if os.path.isfile(path):
            self.open_tab(path)
        elif os.path.isdir(path):
            self.explorer.add(path, expand=True)
        else:
            raise RuntimeError(f"Unknown type for {path!r}")

    # Save/Close
    def request_save(self, event:tk.Event) -> None:
        # Read existing if possible
        if event.widget.filepath is None:
            filesystem_data:bytes = None
        elif not os.path.exists(event.widget.filepath):
            filesystem_data:bytes = None
        else:
            with open(event.widget.filepath, "br") as file:
                filesystem_data:bytes = file.read().replace(b"\r\n", b"\n")
                filesystem_data:bytes = filesystem_data.removesuffix(b"\n")
        # Get the current data in the editor
        data:bytes = event.widget.filesystem_data.encode("utf-8") \
                                                 .removesuffix(b"\n")
        # Compare and ask if we can replace data
        if (filesystem_data is not None) and (data != filesystem_data):
            title:str = "Merge conflict"
            msg:str = "The file has been modified on the filesystem.\n" \
                      "Are you sure you want to save it?"
            allow:bool = askyesno(self.root, title=title, icon="warning",
                                  message=msg, center=True,
                                  center_widget=event.widget)
            if not allow:
                return None
        # Actual save
        event.widget.event_generate("<<Trigger-Save>>")
        self.plugin_manage(event.widget)

    def request_open(self, event:tk.Event) -> None:
        if event.widget.edit_modified():
            title:str = "Discard changes to this file?"
            msg:str = "You haven't saved this file. Are you sure you\n" \
                      "want to continue and discard the changes?"
            ret:bool = askyesno(self.root, title=title, icon="warning",
                                message=msg, center=True,
                                center_widget=event.widget)
            if not ret:
                return None
        event.widget.event_generate("<<Trigger-Open>>")
        self.plugin_manage(event.widget)

    # Handle the get/set state
    def root_close(self, event:tk.Event=None) -> str:
        # Unmaximise window to get its width, height, x, y
        self.root.notmaximised(wait=True)
        self.root.update_idletasks()

        added, expanded = self._get_explorer_state()
        true_explorer_frame:tk.Frame = self.explorer_frame.master_frame
        curr_text:BetterText = self.page_to_text(self.notebook.curr_page)
        curr_text_path:str = None if curr_text is None else curr_text.filepath
        # Update settings.explorer
        settings.explorer.width = true_explorer_frame.winfo_width()
        # Update settings.notebook
        settings.notebook.width = self.notebook.winfo_width()
        settings.notebook.open = self._get_notebook_state()
        # Update settings.explorer
        settings.explorer.expanded = expanded
        settings.explorer.added = added
        # Update settings.window
        size, x, y = self.root.geometry().split("+")
        width, height = size.split("x")
        settings.window.x, settings.window.y = int(x), int(y)
        settings.window.height = self.root.winfo_height()
        settings.window.focused_text = curr_text_path
        # Save settings
        settings.save()

        # Destroy+cleanup plugins
        for text in self.text_to_page:
            plugin:Plugin = getattr(text, "plugin", None)
            if plugin:
                plugin.destroy()

        self.root.destroy()
        return "break"

    def _get_notebook_state(self) -> list[tuple]:
        opened:list[tuple] = []
        for page in self.notebook.iter_pages():
            text:BetterText = self.page_to_text(page)
            file:str = text.filepath
            xview:str = text.xview()[0]
            yview:str = text.yview()[0]
            insert:str = text.index("insert")
            saved:str = text.filesystem_data
            modified:str = text.edit_modified()
            if modified:
                data:str = text.get("1.0", "end").removesuffix("\n")
            else:
                data:str = None
            opened.append([file, data, xview, yview, insert, saved, modified])
        return opened

    def _set_notebook_state(self, opened:list[tuple]) -> None:
        files:set[str] = set()
        for file, data, xview, yview, insert, saved, modified in opened:
            if file in files:
                title:str = "Single file in multiple tabs"
                msg:str = "Please don't open the same file in multiple\n" \
                          "tabs as that can cause problems for this editor"
                telluser(self.root, title=title, message=msg, center=True,
                         icon="warning")
            elif file is not None:
                files.add(file)
            text:BetterText = self.new_tab(file)
            if modified:
                text.filesystem_data:str = saved
                text.delete("0.0", "end")
                text.insert("end", data)
                text.edit_modified(True)
                text.event_generate("<<Clear-Separators>>")
                text.event_generate("<<Modified-Change>>")
            text.event_generate("<<Move-Insert>>", data=(insert,))
            text.mark_set("insert", insert)
            text.xview("moveto", xview)
            text.yview("moveto", yview)
            # Validity check:
            if (file is not None) and modified:
                problem:bool = True
                if os.access(file, os.R_OK):
                    with open(file, "rb") as fd:
                        filedata:bytes = fd.read().replace(b"\r\n", b"\n")
                        filedata:bytes = filedata.removesuffix(b"\n")
                        problem:bool = saved.encode("utf-8") != filedata
                if problem:
                    title:str = "Merge Conflict"
                    msg:str = f"The file {file} has been\nmodified on " \
                              "you system and there are changes in this " \
                              "editor.\nThis means that you have a " \
                              "merge conflict."
                    telluser(self.root, title=title, message=msg,
                             center=True, icon="warning",
                             center_widget=text, block=False)

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
        self.explorer.add(path, expand=True)

    def _get_explorer_state(self) -> tuple[list[str],list[str]]:
        getpath = lambda item: item.fullpath
        added:list[str] = list(map(getpath, self.explorer.root.children))
        expanded:list[str] = []
        for item, _ in self.explorer.root.recurse_children(withself=False):
            if isfolder(item) and item.expanded:
                expanded.append(item.fullpath)
        expanded.extend(p for p in self.expand_later if os.path.isdir(p))
        return added, expanded

    def _set_explorer_state(self, added:list[str], expanded:list[str]) -> None:
        for path in added:
            self.explorer.add(path)
        self._explorer_expand(expanded)

    def _explorer_expand(self, expanded:list[str]=None) -> None:
        if expanded is not None:
            self.expand_later.update(set(expanded))
        changed:bool = True
        while self.expand_later and changed:
            changed:bool = False
            for item, _ in self.explorer.root.recurse_children(withself=False):
                if isfolder(item) and (item.fullpath in self.expand_later):
                    self.expand_later.remove(item.fullpath)
                    self.explorer.expand(item)
                    changed:bool = True

    # The mainloop function
    def mainloop(self) -> None:
        self.root.mainloop()

    # IPC Messages
    def _check_ipc_queue(self, ipc:IPC) -> None:
        try:
            ipc.call_queued_events()
        finally:
            self.root.after(200, self._check_ipc_queue, ipc)

    def focus_force(self) -> None:
        # Bring to top
        self.root.attributes("-topmost", True)
        self.root.attributes("-topmost", False)
        # Focus the root
        self.root.focus_force()
        # Focus the correct text box
        for text, page in self.text_to_page.items():
            if page == self.notebook.curr_page:
                text.focus_set()
                return None


if __name__ == "__main__":
    from err_handler import RunManager

    def start(ipc:IPC=None) -> tuple[App,IPC]:
        if DEBUG_TIME: debug(f"Imports: {perf_counter()-timer[0]:.2f}")
        if DEBUG_TIME: timer[0] = perf_counter()
        return App(ipc)

    def init(app:App) -> tuple[App,IPC]:
        if DEBUG_TIME: debug(f"App create: {perf_counter()-timer[0]:.2f}")
        if DEBUG_TIME: timer[0] = perf_counter()
        app.init()
        for path in sys.argv[1:]:
            app.open(path)
        return app

    def run(app:App) -> None:
        if DEBUG_TIME: debug(f"App init: {perf_counter()-timer[0]:.2f}")
        if DEBUG_TIME: timer[0] = perf_counter()
        for i in range(100):
            app.root.update()
        if DEBUG_TIME: debug(f"App 100 updates: {perf_counter()-timer[0]:.2f}")
        if DEBUG_TIME: timer[0] = perf_counter()
        try:
            app.mainloop()
        except KeyboardInterrupt:
            return None

    def force_singleton() -> MsgQueue:
        return None # For debugging
        with IPC.master_lock_file("bismuth-184", "startup.lock"):
            ipc:IPC = IPC("bismuth-184", sig=SIGUSR1)
            # If this process is the first one:
            if len(ipc.find_where("others")) == 0:
                return ipc
            # Otherwise send events to first process (hope it isn't misbehaving)
            else:
                ipc.event_generate("focus", where="others")
                for arg in sys.argv[1:]:
                    ipc.event_generate("open", where="others", data=arg)
                raise SystemExit()

    manager:RunManager = RunManager()
    manager.register(force_singleton)
    manager.register(start, exit_on_error=True)
    manager.register(init)
    manager.register(run)
    manager.exec()
    with manager.error_chatcher():
        close_all_ipcs()