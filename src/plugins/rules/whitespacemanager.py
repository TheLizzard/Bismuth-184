from __future__ import annotations
from time import perf_counter
import tkinter as tk

from .baserule import Rule, SHIFT, ALT, CTRL

UPDATE_INDENTATION_DELAY:int = 15000
DEBUG:bool = False


BRACKETS:dict[str:str] = {"(":")", "[":"]", "{":"}", "'":"'", '"':'"'}
RBRACKETS:dict[str:str] = {v:k for k,v in BRACKETS.items()}


class WhiteSpaceManager(Rule):
    __slots__ = "text", "indentation", "after_id"
    REQUESTED_LIBRARIES:tuple[str] = "insertdeletemanager"
    REQUESTED_LIBRARIES_STRICT:bool = True

    INDENTATIONS:dict[str,int] = {" ":4, "\t":1}

    INDENTATION_NEWLINE_IGN:set[str] = set()
    INDENTATION_DELTAS:dict[str,int] = {}
    INDENTATION_CP:set[str] = set()
    INDENTATION_DEFAULT:str = " "

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        self.indentation:str = self.INDENTATION_DEFAULT
        self.after_id:str = None
        evs:tuple[str] = (
                           # Returns
                           "<Return>", "<KP_Enter>",
                           # Backspace/Tab
                           "<BackSpace>", "<Tab>",
                           # Key bindings
                           "<Control-bracketleft>", "<Control-bracketright>",
                           # Get default indentation
                           "<<Raw-After-Insert>>")
        super().__init__(plugin, text, evs)
        self.text:tk.Text = self.widget

    def attach(self) -> None:
        super().attach()
        self.update_default_indentation()
        self.plugin.move_insert("insert")

    def detach(self) -> None:
        super().detach()
        if self.after_id is not None:
            self.text.after_cancel(self.after_id)
            self.after_id:str = None

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if (on == "<raw-after-insert>") and (len(event.data["raw"][1]) < 50):
            return False
        return event.state&SHIFT, True

    def do(self, on:str, shift:bool) -> Break:
        if on in ("return", "kp_enter"):
            with self.plugin.see_end_wrapper():
                with self.plugin.undo_wrapper():
                    return self.return_pressed(shift)[0]
        elif on == "backspace":
            with self.plugin.undo_wrapper():
                return self.backspace_pressed()
        elif on == "tab":
            with self.plugin.undo_wrapper():
                return self.tab_pressed()
        elif on in ("control-bracketleft", "control-bracketright"):
            with self.plugin.double_wrapper():
                return self.indent_deintent_section(on)
        elif on == "<raw-after-insert>":
            self.update_default_indentation()
            return False
        raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

    # Return
    def return_pressed(self, shift:bool) -> tuple[Break,str]:
        inds:str = "".join(self.INDENTATIONS)
        self.plugin.delete_selection()
        # If before insert, only spaces, copy them and break
        if not self.text.get("insert linestart", "insert").strip(inds):
            self.text.insert("insert linestart", "\n", "program")
            return True, ""
        # Delete trailing whitespaces
        while True:
            if self.text.get("insert -1c", "insert") in self.INDENTATIONS:
                self.text.delete("insert -1c", "insert")
            else:
                break
        # If shift, insert \n and return
        if shift:
            self.text.insert("insert", "\n", "program")
            return True, ""
        # Delete whitespaces after the cursor but before EOL
        while True:
            if self.text.get("insert", "insert +1c") in self.INDENTATIONS:
                self.text.delete("insert", "insert +1c")
            else:
                break
        # Figure out the indentation change (in python ":")
        last_char:str = self.plugin.get_virline("insert")[-1:]
        indent_delta:str = self.indentation * \
                           self.INDENTATIONS[self.indentation] * \
                           self.INDENTATION_DELTAS.get(last_char, 0)
        # Figure out the prev indentation:
        ind_before:str = self.get_new_indentation("insert")
        self.text.insert("insert", "\n"+ind_before+indent_delta)
        return True, ind_before

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
        with self.plugin.select_wrapper():
            start, end = self.plugin.get_selection()
            getline = lambda idx: int(idx.split(".")[0])
            # For each line in the selection
            if on == "bracketright":
                for line in range(getline(start), getline(end)+1):
                    self.indent_line(line)
            elif on == "bracketleft":
                for line in range(getline(start), getline(end)+1):
                    self.deindent_line(line)
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
        if DEBUG:
            time:str = f"{perf_counter()-start:.3f}"
            print(f"[DEBUG]: update_default_indentation took {time} seconds")
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
        Returns the indentation_type, size.
            indentation_type   the type of indentation. Must be one of
                               self.INDENTATIONS. The default is
                               plugin.default_indentation
            size               the number of `indentation_type` chars
                               at the start of the line
        """
        indentation_type:str = line[:1]
        if indentation_type not in self.INDENTATIONS.keys():
            indentation_type:str = self.indentation
        size:int = len(line) - len(line.lstrip(indentation_type))
        return indentation_type, size

    def get_new_indentation(self, idx:str) -> str:
        """
        Gets the indentation of the new line without applying
          self.INDENTATION_DELTAS
        """
        idx_linestart:str = self.text.index(f"{idx} linestart")
        inds:str = "".join(self.INDENTATIONS)
        stack:list[str] = []
        skipped:bool = False
        while True:
            # Get the line up to idx
            # Repalce strings, with "\xfe"
            line:str = self.text.get(idx_linestart, idx)
            line:str = self.plugin.text_replace_tag(line, idx_linestart, idx,
                                                    "comment", "\xff")
            target:str = line[:len(line)-len(line.lstrip(inds))]
            line:str = line.rstrip(inds+"\xff")
            line:str = self.plugin.text_replace_tag(line, idx_linestart, idx,
                                                    "string", "\xfe")
            if not line.rstrip("\xfe"):
                # Follow ()s iff not in string/comment
                return target
            for j, char in enumerate(reversed(line)):
                if char in self.INDENTATION_CP:
                    # If the stack is empty (eg "f(x", ")" not in stack)
                    #   copy the indentation of the line + more spaces
                    if not stack:
                        return target + " "*(len(line)-j-len(target))
                    # If in stack, (eg. "f()")
                    if char == stack[-1]:
                        stack.pop()
                    # If stack is different (eg. "(]")
                    else:
                        return ""
                elif char in RBRACKETS:
                    # Add the char to the stack
                    op_char:str = RBRACKETS[char]
                    if op_char in self.INDENTATION_CP:
                        stack.append(op_char)
            idx_linestart:str = self.text.index(f"{idx_linestart} -1l")
            idx:str = self.text.index(f"{idx_linestart} lineend")
            if not stack:
                if line[-1:] in self.INDENTATION_NEWLINE_IGN:
                    if not skipped:
                        return target
                char:str = self.text.get(f"{idx} -1c", idx)
                if char not in self.INDENTATION_NEWLINE_IGN:
                    return target
            if self.text.compare(idx_linestart, "==", "1.0"):
                break
            skipped:bool = True
        return ""