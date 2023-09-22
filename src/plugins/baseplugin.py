from __future__ import annotations
import tkinter as tk

try:
    from virtualevents import VirtualEvents
except ImportError:
    from .virtualevents import VirtualEvents

WARNINGS:bool = True


class BasePlugin:
    __slots__ = "rules", "widget"

    def __init__(self, widget:tk.Misc) -> BasePlugin:
        self.widget:tk.Misc = widget
        self.rules:list[Rule] = []

    def attach(self) -> None:
        for rule in self.rules:
            Rule:type[rule] = rule.__class__
            libraries:tuple[str]|str = rule.__class__.REQUESTED_LIBRARIES
            if isinstance(libraries, str):
                libraries:tuple[str] = (libraries,)
            for lib in libraries:
                self.request_library(lib, Rule.__name__,
                                     strict=Rule.REQUESTED_LIBRARIES_STRICT)
            rule.attach()

    def detach(self) -> None:
        for rule in self.rules:
            rule.detach()

    def add(self, Rule:type[Rule]) -> None:
        self.rules.append(Rule(self, self.widget))

    def add_rules(self, rules:Iterable[type[Rule]]) -> None:
        for Rule in rules:
            self.add(Rule)

    def is_library_loaded(self, method_name:str) -> bool:
        """
        Returns a boolean that describes if a `tk.<widget>` attribute has been
          changed by something. If instead the attribute is a boolean instead
          of a Function, the boolean will be returned instead.
        """
        method = getattr(self.widget, method_name, None)
        if isinstance(method, bool):
            return method
        function = getattr(self.widget.__class__, method_name, None)
        return getattr(method, "__func__", function) is not function

    def request_library(self, method:str, requester:str, strict:bool=False):
        if not self.is_library_loaded(method):
            msg:str = f"{requester} requested the library {method!r} " \
                      f"but it's not loaded."
            if strict:
                raise RuntimeError(msg)
            elif WARNINGS:
                print(f"[WARNING] {msg} {requester} might malfunction.")


# Don't change order, mod2 might mean "key press"
ALL_MODIFIERS = ("shift", "caps", "control",
                 "alt", "mod2", "mod3", "mod4", "alt_gr",
                 "button1", "button2", "button3", "button4", "button5")

SEL_TAG:str = "selected" # used in SelectManager


class AllPlugin(BasePlugin):
    __slots__ = "text", "virtual_events"
    DEFAULT_CODE:str = ""

    def __init__(self, text:tk.Text, rules:list[Rule]) -> PythonPlugin:
        self.virtual_events:VirtualEvents = VirtualEvents(text)
        self.text:tk.Text = text
        super().__init__(text)
        super().add_rules(rules)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        return False

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
        self.text.event_generate("<<Modified-Change>>")
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