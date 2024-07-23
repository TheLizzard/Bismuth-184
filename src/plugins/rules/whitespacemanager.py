from __future__ import annotations
from time import perf_counter
import tkinter as tk

from .baserule import Rule

UPDATE_INDENTATION_DELAY:int = 15000
DEBUG:bool = False

# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4


class WhiteSpaceManager(Rule):
    __slots__ = "text", "indentation", "after_id"
    REQUESTED_LIBRARIES:tuple[str] = "event_generate", "bind", "unbind"
    REQUESTED_LIBRARIES_STRICT:bool = False

    INDENTATIONS:dict[str,int] = {" ":4, "\t":1}
    INDENTATION_DELTAS:dict[str,int] = {}
    DEFAULT_INDENTATION:str = " "

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        self.after_id:str = None
        self.indentation:str = self.DEFAULT_INDENTATION
        evs:tuple[str] = (
                           # Returns
                           "<Return>", "<KP_Enter>",
                           # Backspace/Tab
                           "<BackSpace>", "<Tab>",
                           # Key bindings
                           "<Control-bracketleft>", "<Control-bracketright>",
                           # Get default indentation
                           "<<After-Insert>>")
        super().__init__(plugin, text, evs)
        self.text:tk.Text = self.widget

    def attach(self) -> None:
        super().attach()
        self.update_default_indentation()
        self.text.event_generate("<<Move-Insert>>", data=("insert",))

    def detach(self) -> None:
        super().detach()
        if self.after_id is not None:
            self.text.after_cancel(self.after_id)
            self.after_id:str = None

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if (on == "<after-insert>") and (len(event.data[1]) < 50):
            return False
        return event.state&SHIFT, True

    def do(self, on:str, shift:bool) -> Break:
        if on in ("return", "kp_enter"):
            ret, *_ = self.plugin.undo_wrapper(self.return_pressed, shift)
            return ret
        elif on == "backspace":
            return self.plugin.undo_wrapper(self.backspace_pressed)
        elif on == "tab":
            return self.plugin.undo_wrapper(self.tab_pressed)
        elif on in ("control-bracketleft", "control-bracketright"):
            return self.plugin.double_wrapper(self.indent_deintent_section, on)
        elif on == "<after-insert>":
            self.update_default_indentation()
            return False
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # Return
    def return_pressed(self, shift:bool) -> tuple[Break,...]:
        with self.plugin.see_end:
            # Get all of the data we need:
            before:str = self.text.get("insert linestart", "insert")
            after:str = self.text.get("insert", "insert lineend")
            indentation_type, size = self.get_indentation(before or after)
            if before == "":
                size:int = 0 # counter the before or after

            # Delete the whitespaces at the end of the line and after the cursor
            ws_before, ws_aftr = self.get_whites_delete(before, after, shift,
                                                         indentation_type)
            if ws_before + ws_aftr > 0:
                self.text.delete(f"insert -{ws_before}c", f"insert +{ws_aftr}c")

            # Copy the last indentation
            if not shift:
                chars:str = self.get_new_line(before, after, indentation_type,
                                              size)
                self.text.insert("insert", chars)
                return (True, size, indentation_type, chars)
            else:
                return (False,)

    def get_whites_delete(self, before, after, shift, indentation_type):
        """
        Returns the characters to delete before and after the cursor when
          return is pressed from a line line this:
          ```
          def f(x):..|...
          ```
          where "." is any whitespace character in self.INDENTATIONS and "|"
          is the cursor. In this case returns (2, 3)
        Arguments:
          before            The line before the cursor
          after             The rest of the line after the cursor
          shift             A boolean showing if shift is pressed
          indentation_type  The indentation type (eg " " or "\t")
        """
        # Remove all of the whites before the cursor and after the cursor
        whites_before:int = self.count(before, self.INDENTATIONS.keys(), -1)
        whites_after_1:int = self.count(after, self.INDENTATIONS.keys(), +1)
        whites_after_2:int = self.count(after, indentation_type, +1)
        whites_after:int = whites_after_1 if whites_after_1 == len(after) else \
                           whites_after_2
        # if the cursor is inside the indentation of a non empty line
        if (len(after) != whites_after) and (len(before) == whites_before):
            whites_after:int = 0
        # Respect shift:
        if shift:
            whites_after:int = 0
        return whites_before, whites_after

    def get_new_line(self, before, after, indentation_type, size) -> str:
        """
        Get the characters to insert when return is pressed. Must return
          a string. The newline is going to be blocked after this function
          so this function is advised to return a string containing "\n"
        Arguments:
          before            The line before the cursor
          after             The rest of the line after the cursor
          indentation_type  The indentation type (eg " " or "\t")
          size              The number of `indentation_type` characters
                              at the start of `before`
        """
        last_char:str = self.plugin.get_virline("insert")[-1:]
        type_size:int = self.INDENTATIONS[indentation_type]
        size += self.INDENTATION_DELTAS.get(last_char, 0)*type_size
        return "\n" + indentation_type*size

    # Backspace
    def backspace_pressed(self) -> Break:
        line_start:str = self.text.get("insert linestart", "insert")
        if (line_start == "") or (line_start.strip(" ") != ""):
            return False
        toremove:int = len(line_start) % 4
        toremove:int = 4 if toremove == 0 else toremove
        self.text.delete(f"insert -{toremove}c", "insert")
        return True

    # Tab
    def tab_pressed(self) -> Break:
        line:str = self.text.get("insert linestart", "insert")
        indentation_type, size = self.get_indentation(line)
        # If we aren't at the start of a line, don't block "\t"
        if len(line) != size:
            return False
        type_size:int = self.INDENTATIONS[indentation_type]
        self.text.insert("insert", indentation_type*type_size)
        return True

    # Indent/Deindent
    def indent_deintent_section(self, on:str) -> Break:
        on:str = on.removeprefix("control-")
        # Get the selection
        start, end = self.plugin.get_selection()
        self.text.mark_set("sav1", start)
        self.text.mark_set("sav2", end)
        self.text.mark_set("sav3", "insert")
        getline = lambda idx: int(idx.split(".")[0])
        # For each line in the selection
        if on == "bracketright":
            for line in range(getline(start), getline(end)+1):
                self.indent_line(line)
            self.plugin.set_selection("sav1", "sav2")
        elif on == "bracketleft":
            for line in range(getline(start), getline(end)+1):
                self.deindent_line(line)
        self.text.event_generate("<<Move-Insert>>", data=("sav3",))
        return True

    def indent_line(self, linenumber:int) -> None:
        line:str = self.text.get(f"{linenumber}.0", f"{linenumber}.0 lineend")
        if line == "":
            return None
        indentation_type, _ = self.get_indentation(line)
        type_size:int = self.INDENTATIONS[indentation_type]
        self.text.insert(f"{linenumber}.0", indentation_type*type_size,
                         "program")

    def deindent_line(self, linenumber:int) -> None:
        line:str = self.text.get(f"{linenumber}.0", f"{linenumber}.4")
        if (line == "") or (line[:1] not in self.INDENTATIONS):
            return None
        chars:int = self.INDENTATIONS[line[:1]]
        new_line:str = line[:chars].lstrip(line[:1]) + line[chars:]
        diff:int = len(line) - len(new_line)
        self.text.delete(f"{linenumber}.0", f"{linenumber}.{diff}")

    # Update default indentation
    def update_default_indentation(self) -> None:
        if self.after_id is not None:
            self.text.after_cancel(self.after_id)
            self.after_id:str = None
        start:float = perf_counter()
        self._update_default_indentation()
        if DEBUG: print(f"[DEBUG]: update_default_indentation took {perf_counter()-start:.3f} seconds")
        self.after_id:str = self.text.after(UPDATE_INDENTATION_DELAY,
                                            self.update_default_indentation)

    def _update_default_indentation(self) -> None:
        """
        Update the default indentation stored in `self.indentation`. Must be
          one of `self.INDENTATION`.
        This function is called periodically `UPDATE_INDENTATION_DELAY`
          unless the user [pastes >50 characters]/[opens a file]
        """
        data:str = self.text.get("1.0", "end")
        indentations:dict[str,int] = {char:0 for char in self.INDENTATIONS}
        for line in data.split("\n"):
            if line[:1] in self.INDENTATIONS:
                indentations[line[:1]] += 1
        self.indentation:str = max(indentations.items(), key=lambda x: x[1])[0]
        if DEBUG:print(f"[DEBUG]: Set default indentation {self.indentation!r}")

    # Helpers
    def get_indentation(self, line:str) -> tuple[str,int]:
        """
        Returns the indentation_type, size, type_size.
            indentation_type   the type of indentation. Must be one of
                               self.INDENTATIONS. The default is
                               plugin.default_indentation
            size               the number of `indentation_type` chars
                               at the start of the line
            type_size          the usual number of indentation_type chars
        """
        indentation_type:str = line[:1]
        if indentation_type not in self.INDENTATIONS.keys():
            indentation_type:str = self.indentation
        size:int = len(line) - len(line.lstrip(indentation_type))
        return indentation_type, size

    def count(self, line:str, characters:str, direction:int) -> int:
        assert abs(direction) == 1, "ValueError"
        if direction > 0:
            stripped_line:str = line.lstrip("".join(characters))
        else:
            stripped_line:str = line.rstrip("".join(characters))
        return len(line) - len(stripped_line)