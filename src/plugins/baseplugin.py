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
        has_plugin:bool = getattr(self.widget, "plugin", None) is None
        assert has_plugin, "already has a plugin"
        self.widget.plugin:BasePlugin = self
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
        if self.widget.plugin == self:
            self.widget.plugin:BasePlugin = None
        for rule in self.rules:
            rule.detach()

    def destroy(self) -> None:
        if self.widget.plugin == self:
            self.widget.plugin:BasePlugin = None
        for rule in self.rules:
            rule.destroy()
        self.rules.clear()
        self.widget:tk.Misc = None

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
        # If something goes wrong with the library system, change
        #   `getattr(method, "__func__", method) is not function` back to
        #   `getattr(method, "__func__", function) is not function`
        #   and then fix XViewFixManager
        return getattr(method, "__func__", method) is not function

    def request_library(self, method:str, requester:str, strict:bool=False):
        if not self.is_library_loaded(method):
            msg:str = f"{requester} requested the library {method!r} " \
                      f"but it's not loaded."
            if strict:
                raise RuntimeError(msg)
            elif WARNINGS:
                print(f"[WARNING] {msg} {requester} might malfunction.")


# Don't change order; mod2 might mean "key press"
ALL_MODIFIERS = ("shift", "caps", "control",
                 "alt", "mod2", "mod3", "mod4", "alt_gr",
                 "button1", "button2", "button3", "button4", "button5")


class SeeEndContext:
    __slots__ = "text", "see_end", "see_x_char"

    def __init__(self, text:tk.Text) -> SeeEndContext:
        self.see_x_char:str = text.index("insert").split(".")[1]
        self.see_end:bool = (text.yview()[1] == 1)
        self.text:tk.Text = text

    def __enter__(self) -> SeeEndContext:
        return self

    def __exit__(self, exc_t:type, exc_val:BaseException, tb:Traceback) -> bool:
        if self.see_end:
            idx:str = f"end -1l +{self.see_x_char}c"
            self.text.after(1, self.text.see, idx)
        return False


class AllPlugin(BasePlugin):
    __slots__ = "text", "virtual_events"
    DEFAULT_CODE:str = ""
    SEL_TAG:str = "selected" # used in SelectManager

    def __init__(self, text:tk.Text, rules:list[Rule]) -> PythonPlugin:
        self.virtual_events:VirtualEvents = VirtualEvents(text)
        self.text:tk.Text = text
        super().__init__(text)
        super().add_rules(rules)

    @property
    def see_end(self) -> SeeEndContext:
        return SeeEndContext(self.text)

    @classmethod
    def can_handle(Cls:type, filepath:str|None) -> bool:
        return False

    def attach(self) -> None:
        self.virtual_events.paused:bool = False
        super().attach()
        self.text.tag_raise(self.text.plugin.SEL_TAG)

    def detach(self) -> None:
        self.virtual_events.paused:bool = True
        super().detach()

    def left_has_tag(self, tag:str, idx:str) -> bool:
        return tag in self.text.tag_names(f"{idx} -1c")
    # is_inside = left_has_tag # Depricated

    def right_has_tag(self, tag:str, idx:str) -> bool:
        return tag in self.text.tag_names(idx)

    def get_virline(self, end:str) -> str:
        """
        This function only removes the comment at the end
           of the line and the trailing spaces
        """
        current:str = self.text.index(end)
        linenumber:int = int(float(current))
        while (linenumber == int(float(current))) and (current != "1.0"):
            is_comment:bool = self.left_has_tag("comment", current)
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
        tag_ranges:tuple[str,str] = self.text.tag_ranges(self.SEL_TAG)
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
            self.text.tag_add(self.SEL_TAG, start, end)

    def remove_selection(self) -> None:
        """
        Removes the selection.
        """
        self.text.tag_remove(self.SEL_TAG, "1.0", "end")

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

    def find_bracket_match(self, open:str, close:str, end:str="insert"):
        # If we are in a comment or a string, stay in the comment/string
        is_comment:bool = self.left_has_tag("comment", end)
        is_string:bool = self.right_has_tag("string", end)
        if is_string or is_comment:
            if is_string:
                tag:str = "string"
            elif is_comment:
                tag:str = "comment"
            start, _ = self.text.tag_prevrange(tag, end)
            text:list[str] = self.text.get(start, end).split("\n")
            add_line, add_char = start.split(".")
            add_line, add_char = int(add_line)-1, int(add_char)
        else:
            add_line = add_char = 0
            # Remove the strings/comments/both from text
            #   according to is_comment/is_string
            text:list[str] = self.text.get("1.0", end).split("\n")
            self._remove_tag(text, "comment", end)
            self._remove_tag(text, "string", end)
        stack:int = 1
        for line_number, line in enumerate(reversed(text)):
            for char_number, char in enumerate(reversed(line)):
                if char == open:
                    stack -= 1
                elif char == close:
                    stack += 1
                if stack == 0:
                    l:int = len(text) - line_number + add_line
                    c:int = len(line) - char_number + add_char - 1
                    return f"{l}.{c}"
        return None

    def _remove_tag(self, text:list[str], tag:str, end:str) -> None:
        cur:str = end
        while True:
            tag_range = self.text.tag_prevrange(tag, cur, "1.0")
            if not tag_range:
                return None
            self._remove_range(text, tag_range)
            cur:str = tag_range[0]

    def _remove_range(self, text:list[str], _range:tuple[tuple[str,str]]):
        start, end = _range
        start_line, start_char = start.split(".")
        start_line, start_char = int(start_line), int(start_char)
        end_line, end_char = end.split(".")
        end_line, end_char = int(end_line), int(end_char)

        in_between:list[str] = text[start_line-1:end_line]
        if start_line == end_line:
            in_between[0] = in_between[0][:start_char] + \
                            "-"*(end_char-start_char) + \
                            in_between[0][end_char:]
        else:
            in_between[0] = in_between[0][:start_char] + \
                            "-"*(len(in_between[0])-start_char)
            in_between[-1] = "-"*end_char + in_between[-1][end_char:]
            for i in range(1, len(in_between)-1):
                in_between[i] = "-"*len(in_between[i])
        text[start_line-1:end_line] = in_between