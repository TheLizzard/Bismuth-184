from __future__ import annotations
from tkinter.filedialog import askdirectory
import tkinter as tk
import sys
import os
os.chdir(os.path.dirname(__file__))

from file_explorer.expanded_explorer import ExpandedExplorer, isfolder
from bettertk.betterframe import make_bind_frame
from bettertk.betterframe import BetterFrame
from bettertk.betterscrollbar import BetterScrollBarVertical, \
                                     BetterScrollBarHorizontal
from bettertk.messagebox import askyesno, tell as telluser
from bettertk import BetterTk, BetterTkSettings
from bettertk import notebook
from plugins import VirtualEvents
from settings.settings import curr as settings

from plugins import plugins


notebook.CONTROL_T:bool = True
notebook.CONTROL_W:bool = True
notebook.TAB_CONTROLS:bool = True
notebook.CONTROL_NUMBERS_CONTROLS:bool = True
notebook.CONTROL_NUMBERS_RESTRICT:bool = False
notebook.HIDE_SCROLLBAR:bool = False


class App:
    __slots__ = "root", "explorer", "notebook", "text_to_page", \
                "explorer_frame"

    def __init__(self, message_queue:MsgQueue) -> App:
        self.text_to_page:dict[tk.Text:notebook.NotebookPage] = {}
        window_settings:BetterTkSettings = BetterTkSettings()
        window_settings.config(use_border=False)
        self.root:BetterTk = BetterTk(settings=window_settings,
                                      className="Bismuth-184")
        self.root.title("Bismuth-184")
        self.root.iconphoto(True, "sprites/Bismuth_184.ico")
        self.root.protocol("WM_DELETE_WINDOW", self.root_close)
        self.root.geometry(f"+{settings.window.x}+{settings.window.y}")
        self.root.after(100, self._check_msg_queue, message_queue)
        pannedwindow = tk.PanedWindow(self.root, orient="horizontal", bd=0,
                                      height=settings.window.height,
                                      sashwidth=4, bg="grey")
        pannedwindow.pack(fill="both", expand=True)

        self.notebook:notebook.Notebook = notebook.Notebook(pannedwindow, 0)
        self.notebook.bind("<<Tab-Create>>", lambda _: self.new_tab())
        self.notebook.bind("<<Tab-Switched>>", self.change_selected_tab)
        self.notebook.bind("<<Close-All>>", self.root_close)
        self.notebook.on_try_close = self.close_tab

        left_frame:tk.Frame = tk.Frame(pannedwindow, bd=0, bg="black",
                                       highlightthickness=0)
        add = tk.Button(left_frame, text="Add Folder", bg="black", fg="white",
                        activebackground="grey", activeforeground="white",
                        highlightthickness=0, takefocus=False, width=15,
                        command=self.explorer_add_folder, relief="flat")
        add.grid(row=1, column=1, sticky="news")
        sep = tk.Canvas(left_frame, bg="grey", bd=0, highlightthickness=0,
                        width=1, height=1)
        sep.grid(row=1, column=2, sticky="news")
        sep = tk.Canvas(left_frame, bg="grey", bd=0, highlightthickness=0,
                        width=1, height=1)
        sep.grid(row=2, column=1, columnspan=3, sticky="news")
        rem = tk.Button(left_frame, text="Remove Folder", bg="black", fg="white",
                        activebackground="grey", activeforeground="white",
                        highlightthickness=0, takefocus=False, width=15,
                        command=self.explorer_remove_folder, relief="flat")
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
        self.explorer:ExpandedExplorer = ExpandedExplorer(self.explorer_frame)
        self.explorer_frame.bind("<<Explorer-Open>>", self.open_tab_explorer)

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

    def page_to_text(self, page:notebook.NotebookPage) -> tk.Text:
        if page is None:
            return None
        for text, p in self.text_to_page.items():
            if p == page:
                return text
        raise KeyError("InternalError")

    # Tab management
    def new_tab(self, filepath:str=None) -> tk.Text:
        text = tk.Text(self.notebook, highlightthickness=0, bd=0)
        text.filesystem_data:str = ""
        text.save_module:bool = True
        text.filepath:str = filepath
        page = self.notebook.tab_create().add_frame(text)
        self.text_to_page[text] = page
        page.focus()
        self.plugin_manage(text)
        text.focus_set()
        text.bind("<<Request-Save>>", self.request_save, add=True)
        text.bind("<<Request-Open>>", self.request_open, add=True)
        text.bind("<<Modified-Change>>", self.rename_tab, add=True)
        if filepath:
            text.edit_modified(False)
            text.filepath:str = filepath
            text.event_generate("<<Trigger-Open>>")
            if text.get("0.0", "end -1c") != "":
                return text
        text.insert("end", text.plugin.DEFAULT_CODE)
        text.edit_modified(False)
        text.event_generate("<<Modified-Change>>")
        return text

    def plugin_manage(self, text:tk.Text) -> None:
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
                Plugin(text).attach()
                break

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
        text:tk.Text = self.page_to_text(page)
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
            raise RuntimeError("Unknown type for {path!r}")

    # Save close
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

        _, x, y = self.root.geometry().split("+")
        added, expanded = self._get_explorer_state()
        true_explorer_frame:tk.Frame = self.explorer_frame.master_frame
        curr_text:tk.Text = self.page_to_text(self.notebook.curr_page)
        curr_text_path:str = None if curr_text is None else curr_text.filepath

        settings.window.update(height=self.root.winfo_height(), x=x, y=y)
        settings.explorer.update(width=true_explorer_frame.winfo_width())
        settings.notebook.update(width=self.notebook.winfo_width())
        settings.notebook.update(open=self._get_notebook_state())
        settings.explorer.update(added=added, expanded=expanded)
        settings.window.update(focused_text=curr_text_path)
        settings.save()
        self.root.destroy()
        return "break"

    def _get_notebook_state(self) -> list[tuple]:
        opened:list[tuple] = []
        for page in self.notebook.iter_pages():
            text:tk.Text = self.page_to_text(page)
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
            text:tk.Text = self.new_tab(file)
            if modified:
                text.filesystem_data:str = saved
                text.delete("0.0", "end")
                text.insert("end", data)
                text.edit_modified(True)
                text.edit_reset()
                text.edit_separator()
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
        return added, expanded

    def _set_explorer_state(self, added:list[str], expanded:list[str]) -> None:
        for path in added:
            self.explorer.add(path)
        expanded:set[str] = set(expanded)
        while expanded:
            changed:bool = False
            for item, _ in self.explorer.root.recurse_children(withself=False):
                if isfolder(item) and (item.fullpath in expanded):
                    expanded.remove(item.fullpath)
                    self.explorer.expand(item)
                    changed:bool = True
            if not changed:
                break

    # The mainloop function
    def mainloop(self) -> None:
        self.root.mainloop()

    # IPC Messages
    def _check_msg_queue(self, message_queue:MsgQueue) -> None:
        try:
            while message_queue:
                command, *args = message_queue.pop(0)
                if command == "focus":
                    assert len(args) == 0, "There should be no args"
                    self.root.attributes("-topmost", True)
                    self.root.attributes("-topmost", False)
                    self.root.focus_force()
                elif command == "open":
                    assert len(args) == 1, "There should only be 1 arg"
                    self.open(args[0])
                else:
                    raise RuntimeError("Unknown {command=!r}")
        finally:
            self.root.after(200, self._check_msg_queue, message_queue)


if __name__ == "__main__":
    from runner.runner import RunManager

    def start(message_queue=None, onclose=None) -> tuple[App,OnClose]:
        if message_queue is None:
            message_queue:MsgQueue = []
        if onclose is None:
            onclose:OnClose = lambda: None
        return App(message_queue), onclose

    def init(app:App, onclose:OnClose) -> tuple[App,OnClose]:
        app.init()
        for path in sys.argv[1:]:
            app.open(path)
        return app, onclose

    def run(app:App, onclose:Onclose) -> None:
        try:
            app.mainloop()
        except KeyboardInterrupt:
            return None
        finally:
            onclose()

    def force_singleton() -> MsgQueue:
        return None
        from runner.singleton import singleton

        is_main, writer_or_buffer, onclose = singleton()
        if is_main:
            # Return a queue of the messages
            return writer_or_buffer, onclose
        else:
            # Send args to main, tell it to focus, and kill self
            try:
                writer_or_buffer(("focus",))
                for arg in sys.argv[1:]:
                    writer_or_buffer(("open", arg))
            finally:
                onclose()
            raise SystemExit()

    manager:RunManager = RunManager()
    manager.register(force_singleton)
    manager.register(start, exit_on_error=True)
    manager.register(init)
    manager.register(run)
    try:
        manager.exec()
    except SystemExit:
        pass