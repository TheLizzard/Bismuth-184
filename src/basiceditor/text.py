from functools import partial
from time import perf_counter
import tkinter as tk

from .linenumbers import LineNumbers
from constants.settings import settings
from constants.bettertk import ScrolledText as BasicScrolledText


FG_COLOUR = settings.editor.fg.get()

ALPHABET = "abcdefghijklmnopqrstuvwxyz"
ALPHABET += ALPHABET.upper()
ALPHANUMERIC = ALPHABET + "".join(map(str, range(10)))
ALPHANUMERIC_ = ALPHANUMERIC + "_"

KEY_REPLACE_DICT = {"Return": "\n"}
IGNORE_KEYS = ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L",
               "Alt_R", "Caps_Lock", "Num_Lock", "Win_L", "Win_R", "Insert",
               "Clear", "Next", "Prior", "BackSpace", "Delete")


class BasicText(BasicScrolledText):
    def __init__(self, master, wrap="none", undo=True, insertbackground=None,
                 call_init=True, **kwargs):
        if (insertbackground is None) and ("fg" in kwargs):
            insertbackground = kwargs["fg"]
        super().__init__(master, wrap=wrap, undo=undo, autoseparators=False,
                         insertbackground=insertbackground, **kwargs)
        if call_init:
            self.init()

    def bind(self, sequence, function, add=True):
        return super().bind(sequence, function, add=add)

    def init(self):
        # There is a class that takes over some of the functions (Colorizer)
        # so we are going to have this here
        self.chars_since_last_sep = 100
        self.time_last_sep = perf_counter()
        self.bind("<Key>", self.add_text)
        self.bind("<Return>", self.generate_view_changed_event)
        self.bind("<Return>", lambda e: self.after(0, self.see_insert))
        self.bind("<BackSpace>", self.backspace_pressed)
        self.bind("<Delete>", self.delete_pressed)
        self.set_select_colour()

        # Change the behaviour of double clicking:
        self.bind("<Double-Button-1>", self.double_click)
        super().focus()

    def generate_changed_event(self, event=None):
        super().event_generate("<<Changed>>", when="tail")

    def generate_view_changed_event(self, event=None):
        self.generate_changed_event()
        super().event_generate("<<ViewChanged>>", when="tail")

    def double_click(self, event):
        super().tag_remove("sel", "0.0", "end")

        # Doesn't work when we double click twice. "insert" moves to the
        # right so next time we double click `_ctrl_right` doesn't behave
        # correctly
        #insert = super().index("insert")
        insert = super().index("@%i,%i" % (event.x, event.y))
        self.mark_set("insert", insert)

        chars_skip_left = self._ctrl_left(super().index(insert+"+1c"))-1
        chars_skip_right = self._ctrl_right(insert)
        left = "insert-%ic" % chars_skip_left
        right = "insert+%ic" % chars_skip_right

        left = super().index(left)
        if super().compare(left, "==", left+" lineend"):
            left += "+1c"

        super().tag_add("sel", left, right)
        self.mark_set("insert", right)
        return "break"

    def add_text(self, event):
        insert = super().index("insert")
        state = self.get_state(event)
        char = event.char

        # If the key isn't printable make it a word like:
        #     "Left"/"Right"/"BackSpace"
        if (not char.isprintable()) or (char == ""):
            char = event.keysym

        # Replace all of the words that can be expressed with 1 character
        if char in KEY_REPLACE_DICT:
            char = KEY_REPLACE_DICT[char]

        if char in IGNORE_KEYS:
            return "break"

        self.generate_changed_event()

        # Normal key press like: ("a", "b", "c", ...)
        if len(char) == 1:
            if "Control" in state:
                # Normal key combinations like `ctrl+s`, `ctrl+a`.
                if char.lower() == "a":
                    self.select_all()
                elif char.lower() == "c":
                    self.copy()
                    # Stop code execution before it reaches
                    # `self.see_insert()` down there (at the
                    # end of this function)
                    return "break"
                elif char.lower() == "v":
                    self.paste()
                    self.generate_view_changed_event()
                elif char.lower() == "x":
                    self.cut()
                    self.generate_view_changed_event()
                    # Stop code execution before it reaches
                    # `self.see_insert()` down there (at the
                    # end of this function)
                    return "break"
                elif char.lower() == "z":
                    if "Shift" in state:
                        self.redo()
                    else:
                        self.undo()
                elif char.lower() == "w":
                    return None
            elif "Alt" not in state:
                if char in ALPHANUMERIC:
                    self.chars_since_last_sep += 1
                    if (self.chars_since_last_sep >= 5) or\
                       (perf_counter() - self.time_last_sep > 3):
                        super().edit_separator()
                        self.chars_since_last_sep = 0
                        self.time_last_sep = perf_counter()
                else:
                    super().edit_separator()
                self.delete_selected()
                super().insert("insert", char)
                if char not in ALPHANUMERIC:
                    super().edit_separator()

        # Tab pressed
        elif char == "Tab":
            if "Control" in state:
                return None
            else:
                super().edit_separator()
                self.delete_selected()
                super().insert("insert", " "*4)
                super().edit_separator()

        # Left key pressed
        elif char == "Left":
            if "Control" in state:
                self.ctrl_left(insert)
            else:
                self.mark_set("insert", "insert-1c")
                if "Shift" not in state:
                    sel = self.get_sel()
                    if sel is not None:
                        self.mark_set("insert", sel[0])
                    super().tag_remove("sel", "0.0", "end")

        # Right key pressed
        elif char == "Right":
            if "Control" in state:
                self.ctrl_right(insert)
            else:
                self.mark_set("insert", "insert+1c")
                if "Shift" not in state:
                    sel = self.get_sel()
                    if sel is not None:
                        self.mark_set("insert", sel[1])
                    super().tag_remove("sel", "0.0", "end")

        # Down key pressed
        elif char == "Down":
            self.mark_set("insert", "insert+1l")
            if "Shift" not in state:
                super().tag_remove("sel", "0.0", "end")

        # Up key pressed
        elif char == "Up":
            if super().compare("0.0", "==", "insert linestart"):
                self.mark_set("insert", "0.0")
            else:
                self.mark_set("insert", "insert-1l")
            if "Shift" not in state:
                super().tag_remove("sel", "0.0", "end")

        # Home key pressed
        elif char == "Home":
            if "Control" in state:
                self.mark_set("insert", "0.0")
            else:
                self.mark_set("insert", insert.split(".")[0]+".0")
            if "Shift" not in state:
                super().tag_remove("sel", "0.0", "end")

        # End key pressed
        elif char == "End":
            if "Control" in state:
                self.mark_set("insert", "end")
            else:
                self.mark_set("insert", insert.split(".")[0]+".0 lineend")
            if "Shift" not in state:
                super().tag_remove("sel", "0.0", "end")

        # Unknown key pressed
        else:
            print("Unknown char: "+char)

        # ONLY for keys that change `insert`:
        # When shift is pressed we want to extend the sel tag.
        movement_keys = ("Up", "Down", "Left", "Right", "Home", "End")
        if char in movement_keys:
            if "Shift" in state:
                current_insert = super().index("insert")
                sel = self.get_sel()
                if sel is None:
                    indices = (current_insert, insert)
                else:
                    indices = self.ctrl_arrows(sel, insert, current_insert)
                super().tag_remove("sel", "0.0", "end")
                super().tag_add("sel", *self.sort_idxs(*indices))
            else:
                super().tag_remove("sel", "0.0", "end")

        self.see_insert()
        return "break"

    def backspace_pressed(self, event):
        self.generate_view_changed_event()
        # If the user has selected something delete it
        if self.delete_selected():
            return "break"
        else:
            # Don't create another delete event if we deleted selected
            return self.backspace(super().index("insert"))

    def delete_pressed(self, event):
        self.generate_view_changed_event()
        # If the user has selected something delete it
        if self.delete_selected():
            return "break"

    def sort_idxs(self, idx1, idx2):
        if super().compare(idx1, "<", idx2):
            return idx1, idx2
        else:
            return idx2, idx1

    def backspace(self, insert):
        # Get the line number
        line = insert.split(".")[0]
        # Check if everything (from the start of the line) in only spaces
        if super().get(line+".0", insert).lstrip(" ") == "":
            # Check if we moved to the last line
            if super().index(insert+"-4c").split(".")[0] == line:
                # Delete 4 characters
                super().delete(insert+"-4c", insert)
                return "break"

    def ctrl_left(self, insert):
        chars_skipped = self._ctrl_left(insert)
        self.mark_set("insert", insert+"-%ic" % chars_skipped)

    def _ctrl_left(self, start):
        chars_skipped = 0
        current_char = super().get(start+"-1c", start)
        last_char = current_char
        if current_char in ALPHANUMERIC_:
            looking_for_alphabet = False
        else:
            looking_for_alphabet = True

        while not (looking_for_alphabet^(last_char not in ALPHANUMERIC_)):
            chars_skipped += 1
            left = start+"-%ic" % (chars_skipped+1)
            right = start+"-%ic" % chars_skipped
            last_char = super().get(left, right)

            if (last_char == "") or (last_char in "(){}[]"):
                break
            if last_char == "\n":
                chars_skipped += 1
                break
        return chars_skipped

    def ctrl_right(self, insert):
        chars_skipped = self._ctrl_right(insert)
        self.mark_set("insert", insert+"+%ic" % chars_skipped)

    def _ctrl_right(self, start):
        chars_skipped = 0
        current_char = super().get(start, start+"+1c")
        last_char = current_char
        if current_char in ALPHANUMERIC_:
            looking_for_alphabet = False
        else:
            looking_for_alphabet = True

        while not (looking_for_alphabet^(last_char not in ALPHANUMERIC_)):
            chars_skipped += 1
            left = start+"+%ic" % chars_skipped
            right = start+"+%ic" % (chars_skipped+1)
            last_char = super().get(left, right)

            if last_char in "'\"(){}[]\n":
                break
        return chars_skipped

    def delete_selected(self):
        # Deletes the selected text and returns True if successful
        sel = self.get_sel()
        if sel is None:
            return False
        super().delete(*sel)
        return True

    def get_sel(self):
        sel = super().tag_ranges("sel")
        if len(sel) == 2:
            return str(sel[0]), str(sel[1])
        return None

    def mark_set(self, mark_name, location):
        super().mark_set(mark_name, location)
        if mark_name == "insert":
            self.see_insert()

    def see_insert(self):
        super().see("insert")

    def select_all(self):
        super().tag_add("sel", "0.0", "end-1c")
        self.mark_set("insert", "end")

    def copy(self):
        sel = self.get_sel()
        if sel is None:
            return False
        else:
            text = self.get(*sel)
            self.clipboard_clear()
            self.clipboard_append(text)
            return True

    def paste(self):
        try:
            text_copied = self.clipboard_get()
        except:
            # No text coppied so ignore it
            return False
        # Check if the text copied is the same as the tet selected:
        sel = self.get_sel()
        if sel is not None:
            if super().get(*sel) == text_copied:
                super().tag_remove("sel", "0.0", "end")
                self.mark_set("insert", sel[1])
                return True

        super().edit_separator()
        self.delete_selected()
        self.insert("insert", text_copied)
        super().edit_separator()
        return True

    def cut(self):
        if self.copy():
            self.delete_selected()

    def redo(self):
        try:
            self.edit_redo()
        except:
            # Nothing to redo
            return False

    def undo(self):
        try:
            self.edit_undo()
        except:
            # Nothing to undo
            return False

    def set_select_colour(self, bg="orange", fg="black"):
        super().tag_config("sel", background=bg, foreground=fg)
        super().config(inactiveselectbackground=bg)

    @staticmethod
    def get_state(event):
        # Checks if any other keys/events are happening
        # Returns a list like this:
        #    ["Shift", "Control", "Mod1", "Button1", "Button3"]
        mods = ("Shift", "Lock", "Control",
                "Mod1", "Mod2", "Mod3", "Mod4", "Mod5",
                "Button1", "Button2", "Button3", "Button4", "Button5")
        state = []
        for i, name in enumerate(mods):
            if event.state & (1 << i):
                state.append(name)
        return state

    @staticmethod
    def ctrl_arrows(sel_range, insert_before, insert_after):
        sel_range = list(sel_range)
        idx = sel_range.index(insert_before)
        sel_range[idx] = insert_after
        return tuple(sel_range)


class LinedText(BasicText):
    def __init__(self, master, **kwargs):
        self.linedframe = tk.Frame(master, bd=0)
        super().__init__(self.linedframe, **kwargs)
        self.linenumbers = LineNumbers(self.linedframe)
        self.separator = tk.Canvas(self.linedframe, width=1, bg=FG_COLOUR,
                                   bd=0, highlightthickness=0)
        self.linenumbers.attach(self)
        self.linenumbers.pack(side="left", fill="y")
        self.separator.pack(side="left")
        super().pack(side="right", fill="both", expand=True)
        super().bind("<<ViewChanged>>", self.update_lines)

    def pack(self, **kwargs):
        self.linedframe.pack(**kwargs)

    def grid(self, **kwargs):
        self.linedframe.grid(**kwargs)

    def place(self, **kwargs):
        self.linedframe.place(**kwargs)

    def update_lines(self, event):
        self.linenumbers.redraw(event)


ScrolledLinedText = LinedText
ScrolledText = BasicText


class BarredScrolledLinedText(ScrolledLinedText):
    FOTMAT = "Line: %s    Col: %s"
    def __init__(self, master, **kwargs):
        self.barredframe = tk.Frame(master, bd=0)

        super().__init__(self.barredframe, **kwargs)
        self.status_bar = tk.Label(self.barredframe, text="", padx=5,
                                   anchor="e", bg="black", fg="white")
        self.separator = tk.Canvas(self.barredframe, height=1, bg=FG_COLOUR,
                                   bd=0, highlightthickness=0)

        super().pack(expand=True, fill="both")
        self.separator.pack(fill="x")
        self.status_bar.pack(fill="x", anchor="e")

        super().bind("<Key>", self.update_bar)
        super().bind("<Button-1>", self.update_bar)

        self.update_bar()

    def update_bar(self, event=None):
        self.barredframe.after(0, self._update_bar)

    def _update_bar(self, event=None):
        cursor_position = super().index("insert")
        new_text = self.FOTMAT % tuple(cursor_position.split("."))
        self.status_bar.config(text=new_text)

    def pack(self, **kwargs):
        self.barredframe.pack(**kwargs)

    def grid(self, **kwargs):
        self.barredframe.grid(**kwargs)

    def place(self, **kwargs):
        self.barredframe.place(**kwargs)


if __name__ == "__main__":
    def callback(event):
        print("!", event)
        text_widget.generate_changed_event()
    root = tk.Tk()
    text_widget = BarredScrolledLinedText(root, bg="black", fg="white")
    text_widget.pack(fill="both", expand=True)
    text_widget.bind("<BackSpace>", callback)
    text = r".aaa"
    text_widget.insert("end", text)
    root.mainloop()
