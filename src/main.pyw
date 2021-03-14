from tkinter import messagebox

from constants.settings import settings, ChangeSettings
from runnable.runnable import RunnableText
from constants.bettertk import BetterTk
from constants.cpptext import CPPText

# <ttk.Notebook>.enable_traversal()


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
        self.change_title("Untitled")
        self.root.buttons["X"].config(command=self.ask_close)
        self.text_widget = CPPText(self.root, bg=BG_COLOUR, fg=FG_COLOUR,
                                   font=FONT, height=HEIGHT, width=WIDTH)
        self.text_widget.pack(fill="both", expand=True)
        self.text_widget.insert("end", SAMPLE_CODE)
        self.text_widget_wrapper = RunnableText(self.text_widget,
                                                self.change_title,
                                                self.ask_close_file)
        self.text_widget.bind("<F1>", self.change_settings)

    def ask_close_file(self):
        if not self.text_widget_wrapper.is_saved():
            msg = "Do you want to save the file?"
            result = messagebox.askyesnocancel("Exit", msg, default="yes")
            if result is None:
                return "break"
            elif result:
                self.text_widget_wrapper.save()
            else:
                return None

    def ask_close(self):
        if self.ask_close_file() == "break":
            return "break"
        self.text_widget_wrapper.close()
        self.root.close()

    def change_settings(self, event):
        changer = ChangeSettings(self.root)

    def mainloop(self):
        self.root.mainloop()

    def change_title(self, filename):
        #if not self.text_widget_wrapper.is_saved():
        #    filename = "*" + filename + "*"
        title = "C++ Editor by TheLizzard - %s" % filename
        self.root.title(title)


app = App()
app.mainloop()
