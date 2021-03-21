from tkinter import messagebox
import pickle
import tkinter as tk

from constants.settings import settings, ChangeSettings
from runnable.runnable import RunnableText
from constants.bettertk import BetterTk
from constants.cpptext import CPPText
from constants.notebook import Notebook


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
TITLEBAR_SIZE = settings.editor.titlebar_size.get()
NOTACTIVETITLE_BG = settings.editor.notactivetitle_bg.get()


class App:
    def __init__(self):
        self.root = BetterTk(titlebar_bg=BG_COLOUR, titlebar_fg=TITLEBAR_COLOUR,
                             titlebar_sep_colour=FG_COLOUR,
                             titlebar_size=TITLEBAR_SIZE,
                             notactivetitle_bg=NOTACTIVETITLE_BG)
        self.root.iconbitmap("logo/logo1.ico")
        self.root.bind("<F1>", self.change_settings)
        self.root.title("Bismuth 184")
        self.root.buttons["X"].config(command=self.close_app)

        self.notebook = Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
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
        self.root.close()

    def open_app(self, state):
        this_state = state.pop("this")
        self.set_state(this_state)
        for key, value in state.items():
            self.add_tab(state=value)

    def get_state(self):
        return {}

    def set_state(self, state):
        if len(state) > 0:
            print("[App] Didn't handle this part of `state`:", state)

    def change_settings(self, event):
        changer = ChangeSettings(self.root)

    def mainloop(self):
        self.root.mainloop()


app = App()
app.mainloop()
