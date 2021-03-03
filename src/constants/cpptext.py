from functools import partial

from colorizer.text import ColouredLinedScrolledBarredText


BRACKETS = (("[", "]", "bracketleft"),
            ("(", ")", "parenleft"),
            ("{", "}", "braceleft"),
            ("'", "'", "'"),
            ("\"", "\"", "\""))
BRACKETS_LIST = tuple(i+j for i, j, _ in BRACKETS)


class CPPText(ColouredLinedScrolledBarredText):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        super().bind("<BackSpace>", self.backspace_pressed)
        super().bind("<Delete>", self.delete_pressed)
        super().bind("<Return>", self.enter_pressed)
        for open, close, tcl in BRACKETS:
            super().bind(open, partial(self.close_bracket, open, close))
            super().bind(f"<Alt-{tcl}>", partial(self.open_bracket, open))
        super().bind("<Control-bracketleft>", self.unindent_lines)
        super().bind("<Control-bracketright>", self.indent_lines)
        super().bind("<Control-/>", self.toggle_comment_lines)

    def indent_lines(self, event):
        with self.separatorblocker:
            sel = super().get_sel()
            if sel is None:
                start = int(float(super().index("insert")))
                end = start
            else:
                start = int(float(sel[0]))
                end = int(float(sel[1]))
            for line in range(start, end+1):
                super().insert(str(line)+".0", " "*4)

    def unindent_lines(self, event):
        with self.separatorblocker:
            sel = super().get_sel()
            if sel is None:
                start = int(float(super().index("insert")))
                end = start
            else:
                start = int(float(sel[0]))
                end = int(float(sel[1]))
            for line in range(start, end+1):
                line = str(line)+".0"
                for i in range(4):
                    if super().get(line, line+"+1c") == " ":
                        super().delete(line, line+"+1c")
                    else:
                        break

    def toggle_comment_lines(self, event):
        with self.separatorblocker:
            sel = super().get_sel()
            if sel is None:
                start = int(float(super().index("insert")))
                end = start
            else:
                start = int(float(sel[0]))
                end = int(float(sel[1]))
            for line in range(start, end+1):
                line = str(line)+".0"
                self.toggle_comment_line(line)
        return "break"

    def toggle_comment_line(self, line):
        line_text = self.get_line_text(line)
        if line_text[:2] == "//":
            # Get the number of spaces after "//"
            line_text = line_text[2:]
            spaces = len(line_text) - len(line_text.lstrip(" "))
            if ((spaces-1) % 4) == 0:
                # If the number of " "s % 4 != 0
                super().delete(line, line+"+3c")
            else:
                # If we have the perfect amount of " ". Don't remove any.
                super().delete(line, line+"+2c")
        else:
            if line_text == "":
                # Blank lines don't add " " at the end
                super().insert(line, "//")
            else:
                # Full lines add " " at the end of the "//"
                super().insert(line, "// ")

    def close_bracket(self, opening_bracket, closing_bracket, event):
        sel = super().get_sel()
        if sel is None:
            first, last = ("insert", "insert")
        else:
            first, last = sel
            if first.split(".")[0] == last.split(".")[0]:
                last = last+"+1c"
        super().insert(first, opening_bracket)
        super().insert(last, closing_bracket)
        if sel is None:
            super().mark_set("insert", "insert-1c")
        return "break"

    def backspace_pressed(self, event):
        char_before = super().get("insert-1c", "insert")
        char_after = super().get("insert", "insert+1c")
        both_chars = char_before+char_after
        # If it is "()" or "[]" then delete the right one as well
        if both_chars in BRACKETS_LIST:
            super().delete("insert", "insert+1c")

    def delete_pressed(self, event):
        char_after = super().get("insert", "insert+1c")
        char_after_after = super().get("insert+1c", "insert+2c")
        both_chars = char_after+char_after_after
        # If it is "()" or "[]" then delete the right one as well
        if both_chars in BRACKETS_LIST:
            super().delete("insert+1c", "insert+2c")

    def open_bracket(self, opening_bracket, event):
        super().insert("insert", opening_bracket)
        return "break"

    def enter_pressed(self, event):
        insert = super().index("insert")
        text = self.get_line_text(insert)
        last_line_indentation = self.get_indentation(insert)
        needs_more_indentation = self.check_needs_more_indentation(insert,
                                                                   insert)
        new_indentation = last_line_indentation
        if needs_more_indentation:
            new_indentation += 4

        super().insert("insert", "\n"+" "*new_indentation)

        if needs_more_indentation and (text[-2:] == "{}"):
            insert = super().index("insert")
            super().insert("insert", "\n"+" "*last_line_indentation)
            super().mark_set("insert", insert)
        return "break"

    def get_indentation(self, line):
        line_text = self.get_line_text(line)
        return len(line_text) - len(line_text.lstrip(" "))

    def check_needs_more_indentation(self, line, insert):
        line_text = self.get_without_comments(line).rstrip(" ")
        if len(self.get_line_text(line).rstrip(" ")) == 0:
            super().delete(line+" linestart", line+" lineend")
        in_brackets = (super().get(insert, insert+"+1c") == "}") and \
                      (super().get(insert+"-1c", insert) == "{")
        return (line_text[-1:] == ":") or ((line_text[-2:] == "{}") and \
                                           in_brackets)

    def get_without_comments(self, line):
        line = super().index(line+" lineend-1c")
        skip = 0
        while "comment" in super().tag_names(line+"-%ic" % skip):
            skip += 1
            char_left = super().index(line+"-%ic" % (skip+1))
            char_right = super().index(line+"-%ic" % skip)
            if char_left == char_right:
                break
        line = self.get_line_text(line)
        if skip == 0:
            return line
        return line[:-skip]

    def get_line_text(self, line):
        return super().get(line+" linestart", line+" lineend")
