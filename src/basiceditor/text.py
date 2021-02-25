from .scrollbar import AutoScrollbar
import tkinter as tk

ALPHABET = "abcdefghijklmnopqrstuvwxyz"
ALPHABET += ALPHABET.upper()
ALPHANUMERIC = ALPHABET + "".join(map(str, range(10)))
ALPHANUMERIC_ = ALPHANUMERIC + "_"

KEY_REPLACE_DICT = {"Return": "\n"}
IGNORE_KEYS = ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L",
               "Alt_R", "Caps_Lock", "Num_Lock", "Win_L", "Win_R", "Insert",
               "Clear", "Next", "Prior")


class PauseSeparators:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.autoseparators = self.text_widget.cget("autoseparators")

    def __enter__(self):
        self.text_widget.edit_separator()
        if self.autoseparators:
            self.text_widget.config(autoseparators=False)

    def __exit__(self, *args):
        self.text_widget.edit_separator()
        if self.autoseparators:
            self.text_widget.config(autoseparators=True)


class BasicText(tk.Text):
    def __init__(self, master, wrap="none", undo=True, insertbackground=None,
                 **kwargs):
        if (insertbackground is None) and ("fg" in kwargs):
            insertbackground = kwargs["fg"]
        super().__init__(master, wrap=wrap, undo=undo,
                         insertbackground=insertbackground, **kwargs)
        self.separatorblocker = PauseSeparators(self)

    def init(self):
        # There is a class that takes over some of the functions (Colorizer)
        # so we are going to have this here
        super().bind("<Key>", self.add_text)
        self.set_select_colour()

        # Change the behaviour of double clicking:
        super().bind("<Double-Button-1>", self.double_click)
        super().focus()

    def double_click(self, event):
        insert = super().index("insert")
        chars_skip_left = self._ctrl_left(insert)
        chars_skip_right = self._ctrl_right(insert)
        left = "insert-%ic" % chars_skip_left
        right = "insert+%ic" % chars_skip_right

        super().tag_add("sel", left, right)
        self.mark_set("insert", left)
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

        # Normal key press like: ("a", "b", "c", ...)
        if len(char) == 1:
            if "Control" in state:
                # Normal key combinations like `ctrl+s`, `ctrl+a`.
                if char.lower() == "a":
                    self.select_all()
                elif char.lower() == "c":
                    self.copy()
                elif char.lower() == "v":
                    self.paste()
                elif char.lower() == "x":
                    self.cut()
                elif char.lower() == "z":
                    if "Shift" in state:
                        self.redo()
                    else:
                        self.undo()
            else:
                with self.separatorblocker:
                    self.delete_selected()
                    super().insert("insert", char)

        # Tab pressed
        elif char == "Tab":
            with self.separatorblocker:
                self.delete_selected()
                super().insert("insert", " "*4)

        # BackSpace pressed
        elif char == "BackSpace":
            # If the user has selected something delete it
            if not self.delete_selected():
                # Don't create another delete event if we deleted selected
                self.backspace(insert)

        # Delete pressed
        elif char == "Delete":
            # If the user has selected something delete it
            if not self.delete_selected():
                # Don't create another delete event if we deleted selected
                super().delete(insert, insert+"+1c")

        # Left key pressed
        elif char == "Left":
            if "Control" in state:
                self.ctrl_left(insert)
            else:
                self.mark_set("insert", "insert-1c")
                if "Shift" not in state:
                    super().tag_remove("sel", "0.0", "end")

        # Right key pressed
        elif char == "Right":
            if "Control" in state:
                self.ctrl_right(insert)
            else:
                self.mark_set("insert", "insert+1c")
                if "Shift" not in state:
                    super().tag_remove("sel", "0.0", "end")

        # Down key pressed
        elif char == "Down":
            self.mark_set("insert", "insert+1l")
            if "Shift" not in state:
                super().tag_remove("sel", "0.0", "end")

        # Up key pressed
        elif char == "Up":
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
        if (char in ("Up", "Down", "Left", "Right", "Home", "End")) and ("Shift" in state):
            current_insert = super().index("insert")
            sel = self.get_sel()
            if sel is None:
                indices = (current_insert, insert)
            else:
                indices = self.ctrl_arrows(sel, insert, current_insert)
            super().tag_remove("sel", "0.0", "end")
            super().tag_add("sel", *self.sort_idxs(*indices))

        self.see_insert()
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
        if super().get(line+".0", insert).replace(" ", "") == "":
            # Check if we moved to the last line
            if super().index(insert+"-4c").split(".")[0] == line:
                # Delete 4 characters
                super().delete(insert+"-4c", insert)
            else:
                # If we moved to the last line then just del 1 char
                super().delete(insert+"-1c", insert)
        else:
            # Normal backspace (delete 1 character)
            super().delete(insert+"-1c", insert)

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
                #chars_skipped -= 1
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

        with self.separatorblocker:
            self.delete_selected()
            self.insert("insert", text_copied)
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

    @classmethod
    def get_state(self, event):
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

    @classmethod
    def ctrl_arrows(sel_range, insert_before, insert_after):
        sel_range = list(sel_range)
        idx = sel_range.index(insert_before)
        sel_range[idx] = insert_after
        return tuple(sel_range)


class ScrolledText(BasicText):
    def __init__(self, master, **kwargs):
        self.scollframe = tk.Frame(master, bd=0)
        self.text_frame = tk.Frame(self.scollframe, bd=0)
        self.text_frame.pack(side="top")

        super().__init__(self.text_frame, bd=0, **kwargs)
        self.xscrollbar = AutoScrollbar(self.scollframe, command=super().xview,
                                        orient="horizontal")
        self.yscrollbar = AutoScrollbar(self.text_frame, command=super().yview,
                                        orient="vertical")
        super().config(xscrollcommand=self.xscrollbar.set,
                       yscrollcommand=self.yscrollbar.set)
        self.yscrollbar.pack(fill="y", side="right")
        super().pack(fill="both", expand=True, side="left")
        self.text_frame.pack(fill="both", side="top", expand=True)
        self.xscrollbar.pack(fill="x", side="bottom")

    def pack(self, **kwargs):
        self.scollframe.pack(**kwargs)

    def grid(self, **kwargs):
        self.scollframe.grid(**kwargs)

    def place(self, **kwargs):
        self.scollframe.place(**kwargs)


class ScrolledBarredText(ScrolledText):
    FOTMAT = "Line: %s\tCol: %s"
    def __init__(self, master, **kwargs):
        self.barredframe = tk.Frame(master, bd=0)

        super().__init__(self.barredframe, **kwargs)
        self.status_bar = tk.Label(self.barredframe, text="", padx=5,
                                   anchor="e", bg="black", fg="white")

        super().pack(side="top", expand=True, fill="both")
        self.status_bar.pack(side="bottom", fill="x", anchor="e")

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


text = "a"*80 + "\n"*23 + "a"*80

if __name__ == "__main__":
    root = tk.Tk()
    text_widget = ScrolledBarredText(root, bg="black", fg="white")
    text_widget.pack(fill="both", expand=True)
    text_widget.insert("end", text)
    root.mainloop()
