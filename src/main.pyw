# Add "C:\MinGW\bin" to path

from tkinter.filedialog import askdirectory
from tkinter import messagebox
import tkinter as tk
import pickle

from constants.settings import settings, ChangeSettings
from runnable.runnable import RunnableText
from constants.bettertk import BetterTk, BetterTkSettings
from constants.cpptext import CPPText
from constants.notebook import Notebook
from file_explorer.file_explorer import FileExplorer


SAMPLE_CODE = """
#include <iostream>

using namespace std;

int main(){
    cout << "Hello World\\n";
    return 0; // this is a comment
}
"""[1:-1]


FONT = settings.editor.font.get()
HEIGHT = settings.editor.height.get()
WIDTH = settings.editor.width.get()
BG_COLOUR = settings.editor.bg.get()
FG_COLOUR = settings.editor.fg.get()
TITLEBAR_COLOUR = settings.editor.titlebar_colour.get()
INACTIVETITLE_BG = settings.editor.inactivetitle_bg.get()


class App:
    def __init__(self):
        settings = BetterTkSettings(theme="dark")
        settings.config(active_titlebar_bg=BG_COLOUR, bg=BG_COLOUR,
                        active_titlebar_fg=TITLEBAR_COLOUR,
                        separator_colour=FG_COLOUR,
                        inactive_titlebar_bg=INACTIVETITLE_BG)
        self.root = BetterTk(settings=settings)
        self.root.iconbitmap("logo/logo1.ico")
        self.root.bind_all("<F1>", self.change_settings)
        self.root.title("Bismuth 184")
        self.root.close_button.config(command=self.close_app)

        pannedwindow = tk.PanedWindow(self.root, sashwidth=4,
                                      orient="horizontal")
        pannedwindow.pack(fill="both", expand=True)

        self.explorer_window = tk.Frame(pannedwindow, bd=0,
                                        highlightthickness=0)
        # self.explorer_window.pack(fill="both", expand=True, side="left")

        self.explorer = FileExplorer(self.explorer_window, width=200)
        self.explorer.pack(fill="both", expand=True, side="bottom")
        self.explorer.bind("<<FileOpened>>", self.open_file_explorer)

        self.explorer_buttons_frame = tk.Frame(self.explorer_window, bd=0,
                                               highlightthickness=0)
        self.explorer_buttons_frame.pack(fill="x", side="top")
        self.populate_explorer_buttons()

        self.notebook = Notebook(pannedwindow)
        pannedwindow.add(self.explorer_window, sticky="news")
        pannedwindow.add(self.notebook, sticky="news", width=780, height=690)
        # self.notebook.pack(fill="both", expand=True, side="right")
        self.tabs = {}

        self.notebook._delete_tab = self.close_tab
        self.notebook._plus_pressed = self.add_tab
        self.notebook._set_active = self.set_active_tab

        try:
            with open("state.state", "rb") as file:
                state = pickle.loads(file.read())
            self.open_app(state)
        except FileNotFoundError:
            self.add_tab()

    def open_file_explorer(self, event):
        idx = self.explorer.shown_files_dict[self.explorer.selected_file][0]
        full_path = self.explorer.idx_to_full_path[idx]
        idx = self.add_tab()
        wrapper = self.tabs[idx][1]
        wrapper._open(full_path)
        wrapper.text.update_idletasks()
        wrapper.text.after(500, wrapper.text.see_insert)

    def add_folder_explorer(self):
        full_path = askdirectory()
        # Check if user canceled
        if len(full_path) > 0:
            *parent, folder = full_path.split("/")
            parent = "\\".join(parent)
            self.explorer.add_dir(parent, folder)

    def remove_folder_explorer(self):
        self.explorer.remove_selected()

    def populate_explorer_buttons(self):
        b1 = tk.Button(self.explorer_buttons_frame, bg=BG_COLOUR, fg=FG_COLOUR,
                       command=self.add_folder_explorer, text="Add folder")
        b2 = tk.Button(self.explorer_buttons_frame, bg=BG_COLOUR,
                       fg=FG_COLOUR, command=self.remove_folder_explorer,
                       text="Remove folder")
        b1.pack(fill="x", expand=True, side="left")
        b2.pack(fill="x", expand=True, side="left")

    def set_active_tab(self, idx):
        try:
            self.tabs[idx][0].focus()
            self.notebook.set_active(idx)
        except KeyError:
            pass

    def ask_close_tab(self, idx, event=None):
        text_widget, text_widget_wrapper = self.tabs[idx]
        if not text_widget_wrapper.is_saved():
            filename = text_widget_wrapper.file_name
            msg = "Do you want to save the file \"%s\"?" % filename
            result = messagebox.askyesnocancel("Exit", msg, default="yes")
            if result is None:
                return "break"
            elif result:
                text_widget_wrapper.save()

    def close_tab(self, idx=None, event=None):
        if idx is None:
            idx = self.notebook.current_tab
        if self.ask_close_tab(idx) == "break":
            return "break"
        else:
            self.notebook.delete_tab(idx, event)
            del self.tabs[idx]

    def add_tab(self, state=None):
        frame = tk.Frame(self.notebook, bd=0, highlightthickness=0)
        idx = self.notebook.add(frame, text="Untitled")
        text_widget = CPPText(frame, bg=BG_COLOUR, fg=FG_COLOUR,
                              font=FONT, height=HEIGHT, width=WIDTH)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("end", SAMPLE_CODE)
        text_widget_wrapper = RunnableText(text_widget, idx,
                                           self.change_tab_text,
                                           self.ask_close_tab)
        self.tabs.update({idx: (text_widget, text_widget_wrapper)})
        if state is not None:
            text_widget_wrapper.set_state(state)
        self.notebook._set_active(self.notebook.next_idx - 1)
        return idx

    def change_tab_text(self, idx, name):
        self.notebook.rename(idx, name)

    def close_app(self):
        # Save the state
        state = {"this": self.get_state()}
        for idx, (text_widget, text_widget_wrapper) in self.tabs.items():
            state.update({"tab %i" % idx: text_widget_wrapper.get_state()})
        with open("state.state", "wb") as file:
            file.write(pickle.dumps(state))

        # Close the notebook and root
        self.notebook.destroy()
        self.root.destroy()

    def open_app(self, state):
        this_state = state.pop("this")
        self.set_state(this_state)
        for key, value in state.items():
            self.add_tab(state=value)

    def get_state(self):
        return {"explorer": self.explorer.caller_added_folders}

    def set_state(self, state):
        caller_added_folders = state.pop("explorer")
        for args in caller_added_folders:
            try:
                self.explorer.add_dir(*args[:-1])
            except:
                pass
        if len(state) > 0:
            print("[App] Didn't handle this part of `state`:", state)

    def change_settings(self, event):
        changer = ChangeSettings(self.root)

    def mainloop(self):
        self.root.mainloop()


app = App()
app.mainloop()
