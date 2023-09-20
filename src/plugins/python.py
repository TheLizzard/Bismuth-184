from __future__ import annotations
import tkinter as tk

try:
    from virtualevents import VirtualEvents
    from baseplugin import BasePlugin
    # from rules.seeendmanager import SeeEndManager
    from rules.colourmanager import ColourManager
    from rules.wrapmanager import WrapManager
    from rules.whitespacemanager import WhiteSpaceManager
    from rules.clipboardmanager import ClipboardManager
    from rules.shortcutmanager import RemoveShortcuts
    from rules.selectmanager import SelectManager
    from rules.bracketmanager import BracketManager
    from rules.commentmanager import CommentManager
    from rules.saverunmanager import SaveLoadRunManager
    from rules.undomanager import UndoManager
    from rules.reparentmanager import WidgetReparenterManager
    from rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from rules.xrawidgets import MenuManager
except ImportError:
    from .virtualevents import VirtualEvents
    from .baseplugin import BasePlugin
    # from .rules.seeendmanager import SeeEndManager
    from .rules.colourmanager import ColourManager
    from .rules.wrapmanager import WrapManager
    from .rules.whitespacemanager import WhiteSpaceManager
    from .rules.clipboardmanager import ClipboardManager
    from .rules.shortcutmanager import RemoveShortcuts
    from .rules.selectmanager import SelectManager
    from .rules.bracketmanager import BracketManager
    from .rules.commentmanager import CommentManager
    from .rules.saverunmanager import SaveLoadRunManager
    from .rules.undomanager import UndoManager
    from .rules.reparentmanager import WidgetReparenterManager
    from .rules.xrawidgets import BarManager, LineManager, ScrollbarManager
    # from .rules.xrawidgets import MenuManager

# don't change order, mod2 might mean "key press"
ALL_MODIFIERS = ("shift", "caps", "control",
                 "alt", "mod2", "mod3", "mod4", "alt_gr",
                 "button1", "button2", "button3", "button4", "button5")

SEL_TAG:str = "selected" # used in SelectManager


class PythonPlugin(BasePlugin):
    __slots__ = "text", "virtual_events"
    DEFAULT_CODE:str = 'import this\n\nprint("Hello world")'

    def __init__(self, text:tk.Text) -> PythonPlugin:
        self.virtual_events:VirtualEvents = VirtualEvents(text)
        self.text:tk.Text = text
        super().__init__(text)
        super().add_rules([
                            WrapManager,
                            UndoManager,
                            ColourManager,
                            SelectManager,
                            ClipboardManager,
                            WhiteSpaceManager,
                            BracketManager,
                            CommentManager,
                            SaveLoadRunManager,
                            # FindReplaceManager,
                            RemoveShortcuts,
                            # Other widgets:
                            WidgetReparenterManager,
                            BarManager,
                            ScrollbarManager,
                            LineManager,
                            # MenuManager,
                          ])

    def attach(self) -> None:
        self.virtual_events.paused:bool = False
        super().attach()

    def detach(self) -> None:
        self.virtual_events.paused:bool = True
        super().detach()

    def is_inside(self, tag:str, idx:str) -> bool:
        return tag in self.text.tag_names(f"{idx} -1c")

    def get_virline(self, end:str) -> str:
        """
        This function only removes the comment at the end
           of the line and the trailing spaces
        """
        current:str = self.text.index(end)
        linenumber:int = int(float(current))
        while (linenumber == int(float(current))) and (current != "1.0"):
            is_comment:bool = self.is_inside("comment", current)
            is_space:bool = self.text.get(f"{current} -1c", current) in " \t"
            if not (is_comment or is_space):
                return self.text.get(f"{current} linestart", current)
            current:str = self.text.index(f"{current} -1c")
        return ""

    def order_idxs(self, idxa:str, idxb:str) -> tuple[str,str]:
        """
        Order the 2 text idxs passed (smaller, larger)
        """
        if self.text.compare(idxa, "<", idxb):
            return (idxa, idxb)
        else:
            return (idxb, idxa)

    def get_selection(self) -> tuple[str,str]:
        """
        Get the selection idxs. Guaranteed to be pure and ordered.
        If no selection exists, returns (index("insert"), index("insert"))
        """
        tag_ranges:tuple[str,str] = self.text.tag_ranges(SEL_TAG)
        if len(tag_ranges) == 0:
            insert:str = self.text.index("insert")
            return insert, insert
        else:
            start, end, *others = tag_ranges
            assert len(others) == 0, "InternalError"
            return str(start), str(end)

    def set_selection(self, start:str, end:str) -> None:
        """
        Set the selection idxs. Must be ordered.
        """
        self.remove_selection()
        if start != end:
            self.text.tag_add(SEL_TAG, start, end)

    def remove_selection(self) -> None:
        """
        Removes the selection.
        """
        self.text.tag_remove(SEL_TAG, "1.0", "end")

    def delete_selection(self) -> Success:
        """
        Deletes the text inside the selection.
        """
        start, end = self.get_selection()
        if start != end:
            self.text.event_generate("<<Add-Separator>>")
            self.text.delete(start, end)
            self.text.event_generate("<<Add-Separator>>")
            return True
        return False

    def has_modifier(self, raw_modifiers:int, modifier:str) -> bool:
        """
        Don't use this if possible. It's a very slow method.
        """
        return raw_modifiers & (1 << ALL_MODIFIERS.index(modifier))

    def undo_wrapper(self, func:Function, *args):
        self.text.event_generate("<<Add-Separator>>")
        self.text.event_generate("<<Pause-Separator>>")
        return_val = func(*args)
        self.text.event_generate("<<Unpause-Separator>>")
        self.text.event_generate("<<Add-Separator>>", data=(True,))
        return return_val

    def virual_event_wrapper(self, func:Function, *args):
        if self.virtual_events.paused:
            return func(*args)
        else:
            self.virtual_events.paused:bool = True
            return_val = func(*args)
            self.virtual_events.paused:bool = False
            return return_val

    def double_wrapper(self, func:Function, *args):
        def wrapper():
            return self.virual_event_wrapper(func, *args)
        return self.undo_wrapper(wrapper)


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
