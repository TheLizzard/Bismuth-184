from . import coloured_text
import re
import time

from .delegator import Delegator

DEBUG = False

def any(name, alternates):
    "Return a named group pattern matching list of alternates."
    return "(?P<%s>" % name + "|".join(alternates) + ")"

def make_pat():
    kw = r"\b" + any("keyword", coloured_text.get_keywords()) + r"\b"
    builtinlist = coloured_text.get_builtins()
    builtin = r"([^.'\"\\#]\b|^)" + any("builtin", builtinlist) + r"\b"
    include = any("include", [r"#[^\n]*"])
    multiline_comment = r"/\*[^\*]*((\*(?!/))[^\*]*)*(\*/)?"
    comment = any("comment", [r"//[^\n]*", multiline_comment])
    string = any("string", [r"\"[^\"\\\n]*(\\.[^\"\\\n]*)*\"?",
                            r"'[^'\\\n]*(\\.[^'\\\n]*)*'?"])
    return kw + "|" + builtin + "|" + comment + "|" + include + "|" +\
           string + "|" + any("SYNC", [r"\n"])

prog = re.compile(make_pat(), re.S)
idprog = re.compile(r"\s+(\w+)", re.S)


class ColorDelegator(Delegator):
    """Delegator for syntax highlighting (text coloring).

    Instance variables:
        delegate: Delegator below this one in the stack, meaning the
                one this one delegates to.

        Used to track state:
        after_id: Identifier for scheduled after event, which is a
                timer for colorizing the text.
        allow_colorizing: Boolean toggle for applying colorizing.
        colorizing: Boolean flag when colorizing is in process.
        stop_colorizing: Boolean flag to end an active colorizing
                process.
    """

    def __init__(self):
        Delegator.__init__(self)
        self.init_state()
        self.prog = prog
        self.idprog = idprog
        self.LoadTagDefs()

    def init_state(self):
        "Initialize variables that track colorizing state."
        self.after_id = None
        self.allow_colorizing = True
        self.stop_colorizing = False
        self.colorizing = False

    def setdelegate(self, delegate):
        """Set the delegate for this instance.

        A delegate is an instance of a Delegator class and each
        delegate points to the next delegator in the stack.  This
        allows multiple delegators to be chained together for a
        widget.  The bottom delegate for a colorizer is a Text
        widget.

        If there is a delegate, also start the colorizing process.
        """
        if self.delegate is not None:
            self.unbind("<<toggle-auto-coloring>>")
        Delegator.setdelegate(self, delegate)
        if delegate is not None:
            self.config_colors()
            self.bind("<<toggle-auto-coloring>>", self.toggle_colorize_event)
            self.notify_range("1.0", "end")
        else:
            # No delegate - stop any colorizing.
            self.stop_colorizing = True
            self.allow_colorizing = False

    def config_colors(self):
        "Configure text widget tags with colors from tagdefs."
        for tag, cnf in self.tagdefs.items():
            self.tag_configure(tag, **cnf)
        self.tag_raise('sel')

    def LoadTagDefs(self):
        "Create dictionary of tag names to text colors."
        self.tagdefs = {
            "comment": {"foreground": "red"},
            "keyword": {"foreground": "orange"},
            "builtin": {"foreground": "purple"},
            "string": {"foreground": "green"},
            "include": {"foreground": "blue"},
            #"definition": {"foreground": "orange"},
            "SYNC": {'background':None,'foreground':None},
            "TODO": {'background':None,'foreground':None},
            #"ERROR": {'background': "red"},
            }

        if DEBUG: print('tagdefs',self.tagdefs)

    def insert(self, index, chars, tags=None):
        "Insert chars into widget at index and mark for colorizing."
        index = self.index(index)
        self.delegate.insert(index, chars, tags)
        self.notify_range(index, index + "+%dc" % len(chars))

    def delete(self, index1, index2=None):
        "Delete chars between indexes and mark for colorizing."
        index1 = self.index(index1)
        self.delegate.delete(index1, index2)
        self.notify_range(index1)

    def notify_range(self, index1, index2=None):
        "Mark text changes for processing and restart colorizing, if active."
        self.tag_add("TODO", index1, index2)
        if self.after_id:
            if DEBUG: print("colorizing already scheduled")
            return
        if self.colorizing:
            self.stop_colorizing = True
            if DEBUG: print("stop colorizing")
        if self.allow_colorizing:
            if DEBUG: print("schedule colorizing")
            self.after_id = self.after(1, self.recolorize)
        return

    def close(self):
        if self.after_id:
            after_id = self.after_id
            self.after_id = None
            if DEBUG: print("cancel scheduled recolorizer")
            self.after_cancel(after_id)
        self.allow_colorizing = False
        self.stop_colorizing = True

    def toggle_colorize_event(self, event=None):
        """Toggle colorizing on and off.

        When toggling off, if colorizing is scheduled or is in
        process, it will be cancelled and/or stopped.

        When toggling on, colorizing will be scheduled.
        """
        if self.after_id:
            after_id = self.after_id
            self.after_id = None
            if DEBUG: print("cancel scheduled recolorizer")
            self.after_cancel(after_id)
        if self.allow_colorizing and self.colorizing:
            if DEBUG: print("stop colorizing")
            self.stop_colorizing = True
        self.allow_colorizing = not self.allow_colorizing
        if self.allow_colorizing and not self.colorizing:
            self.after_id = self.after(1, self.recolorize)
        if DEBUG:
            print("auto colorizing turned",\
                  self.allow_colorizing and "on" or "off")
        return "break"

    def recolorize(self):
        """Timer event (every 1ms) to colorize text.

        Colorizing is only attempted when the text widget exists,
        when colorizing is toggled on, and when the colorizing
        process is not already running.

        After colorizing is complete, some cleanup is done to
        make sure that all the text has been colorized.
        """
        self.after_id = None
        if not self.delegate:
            if DEBUG: print("no delegate")
            return
        if not self.allow_colorizing:
            if DEBUG: print("auto colorizing is off")
            return
        if self.colorizing:
            if DEBUG: print("already colorizing")
            return
        try:
            self.stop_colorizing = False
            self.colorizing = True
            if DEBUG: print("colorizing...")
            t0 = time.perf_counter()
            self.recolorize_main()
            t1 = time.perf_counter()
            if DEBUG: print("%.3f seconds" % (t1-t0))
        finally:
            self.colorizing = False
        if self.allow_colorizing and self.tag_nextrange("TODO", "1.0"):
            if DEBUG: print("reschedule colorizing")
            self.after_id = self.after(1, self.recolorize)

    def recolorize_main(self):
        "Evaluate text and apply colorizing tags."
        next = "1.0"
        while True:
            item = self.tag_nextrange("TODO", next)
            if not item:
                break
            head, tail = item
            self.tag_remove("SYNC", head, tail)
            item = self.tag_prevrange("SYNC", head)
            if item:
                head = item[1]
            else:
                head = "1.0"

            chars = ""
            next = head
            lines_to_get = 1
            ok = False
            while not ok:
                mark = next
                next = self.index(mark + "+%d lines linestart" %
                                         lines_to_get)
                lines_to_get = min(lines_to_get * 2, 100)
                ok = "SYNC" in self.tag_names(next + "-1c")
                line = self.get(mark, next)
                ##print head, "get", mark, next, "->", repr(line)
                if not line:
                    return
                for tag in self.tagdefs:
                    self.tag_remove(tag, mark, next)
                chars = chars + line
                m = self.prog.search(chars)
                while m:
                    for key, value in m.groupdict().items():
                        if value:
                            a, b = m.span(key)
                            self.tag_add(key,
                                         head + "+%dc" % a,
                                         head + "+%dc" % b)
                            if value in ("def", "class"):
                                m1 = self.idprog.match(chars, b)
                                if m1:
                                    a, b = m1.span(1)
                                    self.tag_add("DEFINITION",
                                                 head + "+%dc" % a,
                                                 head + "+%dc" % b)
                    m = self.prog.search(chars, m.end())
                if "SYNC" in self.tag_names(next + "-1c"):
                    head = next
                    chars = ""
                else:
                    ok = False
                if not ok:
                    # We're in an inconsistent state, and the call to
                    # update may tell us to stop.  It may also change
                    # the correct value for "next" (since this is a
                    # line.col string, not a true mark).  So leave a
                    # crumb telling the next invocation to resume here
                    # in case update tells us to leave.
                    self.tag_add("TODO", next)
                self.update()
                if self.stop_colorizing:
                    if DEBUG: print("colorizing stopped")
                    return

    def removecolors(self):
        "Remove all colorizing tags."
        for tag in self.tagdefs:
            self.tag_remove(tag, "1.0", "end")


def _color_delegator():  # htest #
    from tkinter import Tk, Text
    from .percolator import Percolator

    top = Tk()
    top.title("Test ColorDelegator")
    top.geometry("700x250")
    source = ("#include <stdio.h>\n"
              "\n"
              "int main(){\n"
              "	printf(\"Hello World\");\n"
              "	return 0; // this is a comment\n"
              "}"
              )
    text = Text(top, background="white")
    text.pack(expand=1, fill="both")
    text.insert("insert", source)
    text.focus_set()

    p = Percolator(text)
    d = ColorDelegator()
    p.insertfilter(d)


if __name__ == "__main__":
    _color_delegator()
