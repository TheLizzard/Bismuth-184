from cidle.text import Text as RawText
import string


WORD_CHARS = string.ascii_lowercase+string.ascii_uppercase+"_0123456789"


class Text(RawText):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.focus()
        self.brackets = ("()", "<>", "{}", "[]", "\"\"", "''")
        self.set_select_colour()
        self.bind("<Tab>", self.indent)
        self.bind("<Return>", self.new_line)
        self.bind("<KP_Enter>", self.new_line)
        self.bind("<space>", self.space_bar)
        self.bind("<BackSpace>", self.backspace)

        self.bind("{", self.close_bracket)
        self.bind("(", self.close_bracket)
        self.bind("[", self.close_bracket)
        self.bind("\"", self.close_bracket)
        self.bind("'", self.close_bracket)

        self.bind("<Alt-braceleft>", self.open_bracket)
        self.bind("<Alt-parenleft>", self.open_bracket)
        self.bind("<Alt-bracketleft>", self.open_bracket)
        self.bind("<Alt-\">", self.open_bracket)

        self.bind("<Control-/>", self.toggle_comment_lines)
        self.bind("<Control-Left>", self.skip_left)
        self.bind("<Control-Right>", self.skip_right)
        self.bind("<Control-bracketright>", self.indent_lines)
        self.bind("<Control-bracketleft>", self.unindent_lines)

    def skip_left(self, event):
        i = 1
        start_idx = str(self.index("insert"))
        first_char = self.get("insert-1c", "insert")

        using_word_chars = first_char in WORD_CHARS
        while True:
            next_char = self.get("insert-%ic"%i, "insert-%ic"%(i-1))
            if next_char in WORD_CHARS:
                if not using_word_chars:
                    break
            else:
                if using_word_chars:
                    break
            if next_char == "":
                break
            i += 1

        insert = str(self.index("insert-%ic"%(i-1)))
        self.mark_set("insert", insert)

        if "shift" in get_key_modifiers(event):
            if len(self.tag_ranges("sel")) == 0:
                self.tag_add("sel", insert, start_idx)
                return "break"

            first, second = self.tag_ranges("sel")

            if str(first) == start_idx:
                self.tag_add("sel", insert, str(second))
            else:
                self.tag_remove("sel", "sel.first", "sel.last")
                self.tag_add("sel", str(first), insert)
        return "break"

    def skip_right(self, event):
        i = 1
        start_idx = str(self.index("insert"))
        first_char = self.get("insert", "insert+1c")

        using_word_chars = first_char in WORD_CHARS
        while True:
            next_char = self.get("insert+%ic"%i, "insert+%ic"%(i+1))
            if next_char in WORD_CHARS:
                if not using_word_chars:
                    break
            else:
                if using_word_chars:
                    break
            i += 1

        insert = str(self.index("insert+%ic"%i))
        self.mark_set("insert", insert)

        if "shift" in get_key_modifiers(event):
            if len(self.tag_ranges("sel")) == 0:
                self.tag_add("sel", start_idx, insert)
                return "break"

            first, second = self.tag_ranges("sel")

            if str(first) == start_idx:
                self.tag_remove("sel", "sel.first", "sel.last")
                self.tag_add("sel", insert, str(second))
            else:
                self.tag_add("sel", str(first), insert)
        return "break"

    def space_bar(self, event):
        self.add_sep()
        self.insert("insert", " ")
        self.add_sep()
        return "break"

    def toggle_comment_lines(self, event):
        self.add_sep()
        starting_idx = self.index("insert")
        a, b = self.get_select_lines()
        for line in range(a, b+1):
            self.toggle_comment_line(line, add_sep=False)
        self.mark_set("insert", starting_idx)
        self.add_sep()
        return "break"

    def toggle_comment_line(self, linenumber, add_sep=True):
        if self.get(str(linenumber)+".0", str(linenumber)+".0"+"+2c") == "//":
            self.uncomment_line(linenumber, add_sep=add_sep)
        else:
            self.comment_line(linenumber, add_sep=add_sep)

    def comment_line(self, line, add_sep=True):
        if add_sep:
            self.add_sep()
        self.insert(str(line)+".0", "//")
        if add_sep:
            self.add_sep()

    def uncomment_line(self, line, add_sep=True):
        if add_sep:
            self.add_sep()
        idx = str(line)+".0"
        self.delete(idx, idx+"+2c")
        if add_sep:
            self.add_sep()

    def add_sep(self):
        self.edit_separator()

    def indent(self, event):
        self.insert(self.index("insert"), " "*4)
        return "break"

    def indent_lines(self, event):
        self.add_sep()
        starting_idx = self.index("insert")
        a, b = self.get_select_lines()
        for line in range(a, b+1):
            self.indent_line(line, add_sep=False)
        self.mark_set("insert", starting_idx)
        self.add_sep()

    def unindent_lines(self, event):
        self.add_sep()
        starting_idx = self.index("insert")
        sel = self.get_select_lines()
        a, b = sel
        b += 1
        for line in range(a, b):
            self.unindent_line(line, add_sep=False)
        self.mark_set("insert", starting_idx)
        self.add_sep()

    def indent_line(self, line, add_sep=True):
        if add_sep:
            self.add_sep()
        self.insert(str(line)+".0", " "*4)
        if add_sep:
            self.add_sep()

    def unindent_line(self, line, add_sep=True):
        if add_sep:
            self.add_sep()
        idx = str(line)+".0"
        for i in range(4):
            if self.get(idx, idx+"+1c") == " ":
                self.delete(idx, idx+"+1c")
        if add_sep:
            self.add_sep()

    def get_select_lines(self):
        sel = self.tag_ranges("sel")
        sel = tuple(map(lambda x:int(str(x).split(".")[0]), sel))
        if len(sel) == 0:
            idx = self.index("insert")
            idx = int(idx.split(".")[0])
            sel = (idx, idx)
        return sel

    def backspace(self, event):
        a, b = self.get_select_lines()
        if len(self.tag_ranges("sel")) > 0:
            return None
        self.add_sep()
        idx = self.index("insert")
        text = self.get(idx+"-4c", idx)
        if text == " "*4:
            self.delete(idx+"-4c", idx)
            self.add_sep()
            return "break"
        self.add_sep()

    def new_line(self, event):
        self.add_sep()
        idx = self.index("insert")
        has_end = self.get(idx, idx+"+1c") == "}"
        #get the text
        text = self.get("0.0", "end")
        #get the current cursor position
        idx = self.index("insert")
        #get the previous line so that we can get it's indentation
        line = self.get_line(text, idx)
        if line.count(" ") == len(line):
            start = self.index(idx+" linestart")
            self.delete(start, start+"+%ic"%len(line))
        #we still need a new line
        self.insert(idx, "\n")
        #get the indentation from the last line
        indent = self.copy_indent(line)
        #get the cursor position again.
        pos = self.index("insert")
        #insert the indentation
        self.insert(pos, indent)

        #check if the last character is "{" or ":"
        last_char = self.get(idx+"-1c", idx)
        has_start = (last_char == "{") or (last_char == ":")
        if has_start:
            #get the cursor position again.
            idx = self.index("insert")
            #insert more indentation
            self.insert(idx, " "*4)
            if has_end:
                #the new position of the cursor = the last one +4 characters
                pos = idx+"+4c"
                #insert the the line the indentation
                self.insert(pos, "\n"+indent)
                #reset the cursor position back in between the "{" and "}"
                self.mark_set("insert", pos)
        self.add_sep()
        self.see("insert")
        return "break"

    def close_bracket(self, event):
        self.add_sep()
        add = None
        char = event.char
        for brackets in self.brackets:
            if brackets[0] == char:
                add = brackets
                break
        if add is not None:
            sel = self.tag_ranges("sel")
            sel = tuple(map(str, sel))
            if len(sel) == 0:
                idx = self.index("insert")
                self.insert(idx, add)
                self.mark_set("insert", idx+"+1c")
            else:
                self.insert(sel[0], add[0])
                self.insert(sel[1]+"+1c", add[1])
                self.mark_set("insert", sel[1]+"+1c")
            self.add_sep()
            return "break"
        self.add_sep()

    def open_bracket(self, event):
        char = event.keysym
        if char == "parenleft":
            char = "("
        elif char == "braceleft":
            char = "{"
        elif char == "bracketleft":
            char = "["
        elif char == "quotedbl":
            char = "\""
        self.insert("insert", char)
        return "break"

    def get_line(self, text, idx):
        return text.split("\n")[int(float(idx))-1]

    def copy_indent(self, line):
        i = ""
        for char in line:
            if char == " ":
                i += " "
            else:
                break
        return i


def get_key_modifiers(event):
    char = event.keysym
    state = event.state

    ctrl = (state & 0x4) != 0
    alt = (state & 0x8) != 0 or (s & 0x80) != 0
    shift = (state & 0x1) != 0

    output = ""
    if alt:
         output += "alt+"
    if shift:
        output += "shift+"
    if ctrl:
        output += "ctrl+"
    return output[:-1]


if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    text = Text(root, width=30)
    text.pack()
    text.insert("end", "self.kill.everyone\na = \"zz5.5\"\nb = 'Hello_World'")
