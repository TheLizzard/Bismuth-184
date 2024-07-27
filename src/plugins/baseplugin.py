from __future__ import annotations
import tkinter as tk

try:
    from virtualevents import VirtualEvents
except ImportError:
    from .virtualevents import VirtualEvents


WARNINGS:bool = True
DEBUG:bool = False


class ProtoPlugin:
    __slots__ = "rules", "widget"

    def __init__(self, widget:tk.Misc) -> ProtoPlugin:
        self.widget:tk.Misc = widget
        self.rules:list[Rule] = []

    def attach(self) -> None:
        has_plugin:bool = getattr(self.widget, "plugin", None) is None
        assert has_plugin, "already has a plugin"
        self.widget.plugin:ProtoPlugin = self
        rules:list[Rule] = self.rules.copy()
        for _pass in ("safe", "warn", "error"):
            self._load_rules(rules, _pass=_pass)

    def _load_rules(self, rules:list[Rule], _pass:str) -> None:
        while True:
            for i, rule in enumerate(rules):
                Rule:type = rule.__class__
                unmet:tuple[str] = self._try_load_rule(Rule)
                if not unmet:
                    if DEBUG: print(f"[DEBUG]: attaching {Rule.__name__}")
                    rule.attach()
                    rules.pop(i)
                    break
                msg:str = f"{Rule.__name__} requested {unmet[0]!r} library " \
                          f"but it's not loaded."
                if _pass == "warn":
                    if Rule.REQUESTED_LIBRARIES_STRICT:
                        continue
                    print(f"[WARNING] {msg} {Rule.__name__} might "
                          f"malfunction.")
                    if DEBUG: print(f"[DEBUG]: attaching {Rule.__name__}")
                    rule.attach()
                    rules.pop(i)
                    break
                if _pass == "error":
                    raise RuntimeError(msg)
            else:
                break

    def _try_load_rule(self, Rule:type) -> tuple[str]:
        libraries:tuple[str] = self._get_rule_dependencies(Rule)
        unmet:tuple[str] = self._unmet_dependencies(libraries)
        return unmet

    def _unmet_dependencies(self, libraries:tuple[str]) -> tuple[str]:
        unmet:list[str] = []
        for lib in libraries:
            if not self.is_library_loaded(lib):
                unmet.append(lib)
        return tuple(unmet)

    def _get_rule_dependencies(self, Rule:type) -> tuple[str]:
        libraries:tuple[str]|str = Rule.REQUESTED_LIBRARIES
        if isinstance(libraries, str):
            libraries:tuple[str] = (libraries,)
        assert isinstance(libraries, tuple|list), "TypeError"
        for lib in libraries:
            assert isinstance(lib, str), "TypeError"
        return libraries

    def request_library(self, method:str, requester:str, strict:bool=False):
        if not self.is_library_loaded(method):
            msg:str = f"{requester} requested the library {method!r} " \
                      f"but it's not loaded."
            if strict:
                raise RuntimeError(msg)
            elif WARNINGS:
                print(f"[WARNING] {msg} {requester} might malfunction.")

    def detach(self) -> None:
        if self.widget.plugin == self:
            self.widget.plugin:ProtoPlugin = None
        for rule in self.rules:
            rule.detach()

    def destroy(self) -> None:
        if self.widget.plugin == self:
            self.widget.plugin:ProtoPlugin = None
        for rule in self.rules:
            rule.destroy()
        self.rules.clear()
        self.widget:tk.Misc = None

    def add(self, Rule:type[Rule]) -> None:
        try:
            self.rules.append(Rule(self, self.widget))
        except BaseException as error:
            print(f"[ERROR]: {Rule.__name__} errored out")
            raise

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


class BasePlugin(ProtoPlugin):
    __slots__ = "text", "master", "virtual_events"
    DEFAULT_CODE:str = ""
    SEL_TAG:str = "selected" # used in SelectManager

    def __init__(self, master:tk.Misc, text:tk.Text,
                 rules:list[Rule]) -> BasePlugin:
        self.virtual_events:VirtualEvents = VirtualEvents(text)
        self.master:tk.Misc = master
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
        try:
            self.text.tag_raise(self.text.plugin.SEL_TAG)
        except tk.TclError:
            pass

    def detach(self) -> None:
        self.virtual_events.paused:bool = True
        super().detach()

    def left_has_tag(self, tag:str, idx:str) -> bool:
        return tag in self.text.tag_names(f"{idx} -1c")

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
        """
        The argument `func` is called with the rest of the given arguments
          and all of the changes made to `self.text` are grouped and atomic
          in terms of undo/redo.
        """
        def inner():
            try:
                self.text.event_generate("<<Add-Separator>>", data=(True,))
                self.text.event_generate("<<Pause-Separator>>")
                return func(*args)
            finally:
                self.text.event_generate("<<Unpause-Separator>>")
                self.text.event_generate("<<Add-Separator>>", data=(True,))
                self.text.event_generate("<<Modified-Change>>")
        return self.select_wrapper(inner)

    def select_wrapper(self, func:Function, *args):
        try:
            # Get the selection
            start, end = self.get_selection()
            selected:bool = (start != end)
            if selected:
                self.text.mark_unset("sav1", "sav2")
                self.text.mark_set("sav1", start)
                self.text.mark_set("sav2", end)
                self.text.mark_gravity("sav1", "right")
                self.text.mark_gravity("sav2", "left")
                if self.text.compare("sav1", "==", "insert"):
                    sav3:str = "sav1"
                else:
                    sav3:str = "sav2"
            return func(*args)
        finally:
            if selected:
                try:
                    start, end = self.get_selection()
                except AssertionError:
                    # Set the selection
                    self.set_selection("sav1", "sav2")
                    self.text.event_generate("<<Move-Insert>>", data=(sav3,))

    def virual_event_wrapper(self, func:Function, *args):
        if self.virtual_events.paused:
            return func(*args)
        try:
            self.virtual_events.paused:bool = True
            return func(*args)
        finally:
            self.virtual_events.paused:bool = False

    def double_wrapper(self, func:Function, *args):
        """
        Both `undo_wrapper` and `virual_event_wrapper`.
        """
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