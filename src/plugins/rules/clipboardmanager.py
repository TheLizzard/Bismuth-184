from __future__ import annotations
import tkinter as tk

from bettertk.messagebox import tell as telluser
from .baserule import Rule


class ClipboardManager(Rule):
    __slots__ = "text"
    REQUESTED_LIBRARIES:tuple[str] = "event_generate", "bind", "unbind"
    REQUESTED_LIBRARIES_STRICT:bool = False

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        super().__init__(plugin, text, ("<Control-C>", "<Control-c>",
                                        "<Control-V>", "<Control-v>",
                                        "<Control-X>", "<Control-x>",
                                        "<Control-A>", "<Control-a>"))
        self.text:tk.Text = self.widget

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        return self.plugin.undo_wrapper(self._do, on)

    def _do(self, on:str) -> Break:
        op:str = on[-1]
        start, end = self.plugin.get_selection()
        if op == "a":
            self.plugin.set_selection("1.0", "end -1c")
            self.text.event_generate("<<Move-Insert>>", data=("end -1c",))
            return True
        if op in "cx":
            if start == end: # if no selection
                return False
            self.text.clipboard_clear()
            self.text.clipboard_append(self.text.get(start, end))
            if op == "x":
                self.text.delete(start, end)
            return True
        if op == "v":
            # Get the selected text and the text from the clipboard
            if start == end:
                selected:str = None
            else:
                selected:str = self.text.get(start, end)
            try:
                copied:str = self.text.clipboard_get()
            except tk.TclError:
                msg:str = "Clipboard contents too large"
                telluser(self.text, title="Can't paste", message=msg,
                         center=True, icon="error")
                return True
            # If they are the same, just move the cursor
            if selected == copied:
                self.plugin.remove_selection()
                self.text.event_generate("<<Move-Insert>>", data=(end,))
            # else delete selected and insert the clipboard text
            else:
                with self.plugin.see_end:
                    self.text.delete(start, end)
                    self.text.insert("insert", copied)
            return True
        raise RuntimeError(f"Unhandled {op} in {self.__class__.__name__}")