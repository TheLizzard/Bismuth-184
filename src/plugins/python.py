from __future__ import annotations
import tkinter as tk

try:
    from baseplugin import AllPlugin
    # from rules.seeinsertmanager import SeeInsertManager
    from rules.wrapmanager import WrapManager
    from rules.clipboardmanager import ClipboardManager
    from rules.shortcutmanager import RemoveShortcuts
    from rules.selectmanager import SelectManager
    from rules.bracketmanager import BracketManager
    from rules.commentmanager import CommentManager
    from rules.undomanager import UndoManager
    from rules.reparentmanager import WidgetReparenterManager
    from rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from rules.xrawidgets import MenuManager
    from rules.python.colourmanager import ColourManager
    from rules.python.whitespacemanager import WhiteSpaceManager
    from rules.python.saveloadmanager import SaveLoadManager
    from rules.python.runmanager import RunManager
except ImportError:
    from .baseplugin import AllPlugin
    # from .rules.seeinsertmanager import SeeInsertManager
    from .rules.wrapmanager import WrapManager
    from .rules.clipboardmanager import ClipboardManager
    from .rules.shortcutmanager import RemoveShortcuts
    from .rules.selectmanager import SelectManager
    from .rules.bracketmanager import BracketManager
    from .rules.commentmanager import CommentManager
    from .rules.undomanager import UndoManager
    from .rules.reparentmanager import WidgetReparenterManager
    from .rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from .rules.xrawidgets import MenuManager
    from .rules.python.colourmanager import ColourManager
    from .rules.python.whitespacemanager import WhiteSpaceManager
    from .rules.python.saveloadmanager import SaveLoadManager
    from .rules.python.runmanager import RunManager


class PythonPlugin(AllPlugin):
    __slots__ = ()
    DEFAULT_CODE:str = 'import this\n\nprint("Hello world")'

    def __init__(self, text:tk.Text) -> PythonPlugin:
        rules:list[Rule] = [
                             WrapManager,
                             UndoManager,
                             ColourManager,
                             SelectManager,
                             ClipboardManager,
                             WhiteSpaceManager,
                             BracketManager,
                             CommentManager,
                             SaveLoadManager,
                             RunManager,
                             # FindReplaceManager,
                             RemoveShortcuts,
                             # Other widgets:
                             WidgetReparenterManager,
                             BarManager,
                             ScrollbarManager,
                             LineManager,
                             # MenuManager,
                           ]
        super().__init__(text, rules)


if __name__ == "__main__":
    CLOSED:bool = False

    def close() -> None:
        global CLOSED
        insert:str = text.index("insert")
        with open("state.txt", "w") as file:
            file.write(insert)
        CLOSED = True
        root.destroy()

    import sys

    root = tk.Tk()
    text = tk.Text(root, highlightthickness=0, bd=0)
    text.pack(fill="both", expand=True)
    text.focus_set()

    root.protocol("WM_DELETE_WINDOW", close)
    text.bind("<Control-w>", lambda e: close())
    text.config(width=80, height=40)

    plugin = PythonPlugin(text)
    plugin.attach()

    if len(sys.argv) == 1:
        text.insert("end", """
import hello # world

class A: ...

def fuc() -> None:
    print(int for i in "string")


aaaaaaaaa aaaaaaa aaaaaaaaaaa

aaaaa aaaaa aaaaaaaaa aaaaaaa
aaaa aaaaa()aaaaa aaaaaa_aaaa

aaaaaaaaaaaaaaaaaaaaaaaaaaaaa
aaaaaaaaaaaaaabaaaaaaaaaaaaaa
aaaaaaaaaaaaaaaaaaaaaaaaaaaaa

aaaaaaaaaaaaaaaaaaaaaaaaaaaaa
aaaaa()aaaa"aaaa"aaa#aa012aaa

evs.add(f"<Control-{char}>")

aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
\n\n\n\n\n\n\\n\n\n\nfdsgdfgdf
\n\n\n\n\n\\n\n\nhdfhfghgfh
\n\n\n\n\n\n\n\nfdgdfgfd
\n\n\n\n\n\n\n\n\n\n\nbbbbb
""".strip("\n"))
        text.event_generate("<<Clear-Separators>>")
    else:
        plugin.rules[9].file = sys.argv[1]
        plugin.rules[9]._open()

    try:
        with open("state.txt", "r") as file:
            insert_mark:str = file.read()
            text.event_generate("<<Move-Insert>>", data=(insert_mark,))
            text.see("insert -10l")
    except:
        pass

    text.event_generate("<<Explorer-Set-CWD>>", data=("wow",))
    root.mainloop()

    if CLOSED:
        import os
        print("[DEBUG]: calling os._exit()", flush=True)
        os._exit(0)
