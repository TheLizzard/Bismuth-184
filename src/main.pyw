from constants.bettertk import BetterTk
from runnable.runnable import RunnableText
from constants.cpptext import CPPText
from constants.settings import settings, ChangeSettings


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


class App:
    def __init__(self):
        self.root = BetterTk(titlebar_bg=BG_COLOUR, titlebar_fg=TITLEBAR_COLOUR,
                             titlebar_sep_colour=FG_COLOUR,
                             titlebar_size=TITLEBAR_SIZE)
        self.root.title("C++ Editor by TheLizzard")
        self.text_widget = CPPText(self.root, bg=BG_COLOUR, fg=FG_COLOUR,
                                   font=FONT, height=HEIGHT, width=WIDTH)
        self.text_widget.pack(fill="both", expand=True)
        self.text_widget.insert("end", SAMPLE_CODE)
        self.text_widget_wrapper = RunnableText(self.text_widget)
        self.text_widget.bind("<F1>", self.change_settings)

    def change_settings(self, event):
        changer = ChangeSettings(self.root)

    def mainloop(self):
        self.root.mainloop()


app = App()
app.mainloop()
