from tkinter import TclError
import time
import re

from . import colours


def any(name, alternates):
    "Return a named group pattern matching list of alternates."
    return "(?P<%s>" % name + "|".join(alternates) + ")"

def make_pat():
    kw = r"\b" + any("keyword", colours.get_keywords()) + r"\b"
    builtinlist = colours.get_builtins()
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


class Delegator:
    def __init__(self, delegate=None):
        self.delegate = delegate
        self.__cache = set()
        # Cache is used to only remove added attributes
        # when changing the delegate.

    def __getattr__(self, name):
        attr = getattr(self.delegate, name) # May raise AttributeError
        setattr(self, name, attr)
        self.__cache.add(name)
        return attr

    def resetcache(self):
        "Removes added attributes while leaving original attributes."
        # Function is really about resetting delegator dict
        # to original state.  Cache is just a means
        for key in self.__cache:
            try:
                delattr(self, key)
            except AttributeError:
                pass
        self.__cache.clear()

    def setdelegate(self, delegate):
        "Reset attributes and change delegate."
        self.resetcache()
        self.delegate = delegate


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
            "comment": {"foreground": colours.COMMENTS_COLOUR},
            "keyword": {"foreground": colours.KEY_WORDS_COLOUR},
            "builtin": {"foreground": colours.BUILTINS_COLOUR},
            "string": {"foreground": colours.STRINGS_COLOUR},
            "include": {"foreground": colours.INCLUDE_COLOUR},
            #"definition": {"foreground": colours.DEFINITIONS},
            "SYNC": {"background": None, "foreground": None},
            "TODO": {"background": None, "foreground": None},
            }

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
            return
        if self.colorizing:
            self.stop_colorizing = True
        if self.allow_colorizing:
            self.after_id = self.after(1, self.recolorize)
        return

    def close(self):
        if self.after_id:
            after_id = self.after_id
            self.after_id = None
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
            self.after_cancel(after_id)
        if self.allow_colorizing and self.colorizing:
            self.stop_colorizing = True
        self.allow_colorizing = not self.allow_colorizing
        if self.allow_colorizing and not self.colorizing:
            self.after_id = self.after(1, self.recolorize)
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
            return
        if not self.allow_colorizing:
            return
        if self.colorizing:
            return
        try:
            self.stop_colorizing = False
            self.colorizing = True
            t0 = time.perf_counter()
            self.recolorize_main()
            t1 = time.perf_counter()
        finally:
            self.colorizing = False
        if self.allow_colorizing and self.tag_nextrange("TODO", "1.0"):
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
                                    self.tag_add("definition",
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
                    return

    def removecolors(self):
        "Remove all colorizing tags."
        for tag in self.tagdefs:
            self.tag_remove(tag, "1.0", "end")


class Percolator:
    def __init__(self, text):
        # XXX would be nice to inherit from Delegator
        self.text = text
        self.redir = WidgetRedirector(text)
        self.top = self.bottom = Delegator(text)
        self.bottom.insert = self.redir.register("insert", self.insert)
        self.bottom.delete = self.redir.register("delete", self.delete)
        self.filters = []

    def close(self):
        while self.top is not self.bottom:
            self.removefilter(self.top)
        self.top = None
        self.bottom.setdelegate(None)
        self.bottom = None
        self.redir.close()
        self.redir = None
        self.text = None

    def insert(self, index, chars, tags=None):
        # Could go away if inheriting from Delegator
        self.top.insert(index, chars, tags)

    def delete(self, index1, index2=None):
        # Could go away if inheriting from Delegator
        self.top.delete(index1, index2)

    def insertfilter(self, filter):
        # Perhaps rename to pushfilter()?
        assert isinstance(filter, Delegator)
        assert filter.delegate is None
        filter.setdelegate(self.top)
        self.top = filter

    def removefilter(self, filter):
        # XXX Perhaps should only support popfilter()?
        assert isinstance(filter, Delegator)
        assert filter.delegate is not None
        f = self.top
        if f is filter:
            self.top = filter.delegate
            filter.setdelegate(None)
        else:
            while f.delegate is not filter:
                assert f is not self.bottom
                f.resetcache()
                f = f.delegate
            f.setdelegate(filter.delegate)
            filter.setdelegate(None)


class WidgetRedirector:
    """Support for redirecting arbitrary widget subcommands.

    Some Tk operations don't normally pass through tkinter.  For example, if a
    character is inserted into a Text widget by pressing a key, a default Tk
    binding to the widget's 'insert' operation is activated, and the Tk library
    processes the insert without calling back into tkinter.

    Although a binding to <Key> could be made via tkinter, what we really want
    to do is to hook the Tk 'insert' operation itself.  For one thing, we want
    a text.insert call in idle code to have the same effect as a key press.

    When a widget is instantiated, a Tcl command is created whose name is the
    same as the pathname widget._w.  This command is used to invoke the various
    widget operations, e.g. insert (for a Text widget). We are going to hook
    this command and provide a facility ('register') to intercept the widget
    operation.  We will also intercept method calls on the tkinter class
    instance that represents the tk widget.

    In IDLE, WidgetRedirector is used in Percolator to intercept Text
    commands.  The function being registered provides access to the top
    of a Percolator chain.  At the bottom of the chain is a call to the
    original Tk widget operation.
    """
    def __init__(self, widget):
        '''Initialize attributes and setup redirection.

        _operations: dict mapping operation name to new function.
        widget: the widget whose tcl command is to be intercepted.
        tk: widget.tk, a convenience attribute, probably not needed.
        orig: new name of the original tcl command.

        Since renaming to orig fails with TclError when orig already
        exists, only one WidgetDirector can exist for a given widget.
        '''
        self._operations = {}
        self.widget = widget            # widget instance
        self.tk = tk = widget.tk        # widget's root
        w = widget._w                   # widget's (full) Tk pathname
        self.orig = w + "_orig"
        # Rename the Tcl command within Tcl:
        tk.call("rename", w, self.orig)
        # Create a new Tcl command whose name is the widget's pathname, and
        # whose action is to dispatch on the operation passed to the widget:
        tk.createcommand(w, self.dispatch)

    def __repr__(self):
        return "%s(%s<%s>)" % (self.__class__.__name__,
                               self.widget.__class__.__name__,
                               self.widget._w)

    def close(self):
        "Unregister operations and revert redirection created by .__init__."
        for operation in list(self._operations):
            self.unregister(operation)
        widget = self.widget
        tk = widget.tk
        w = widget._w
        # Restore the original widget Tcl command.
        tk.deletecommand(w)
        tk.call("rename", self.orig, w)
        del self.widget, self.tk  # Should not be needed
        # if instance is deleted after close, as in Percolator.

    def register(self, operation, function):
        '''Return OriginalCommand(operation) after registering function.

        Registration adds an operation: function pair to ._operations.
        It also adds a widget function attribute that masks the tkinter
        class instance method.  Method masking operates independently
        from command dispatch.

        If a second function is registered for the same operation, the
        first function is replaced in both places.
        '''
        self._operations[operation] = function
        setattr(self.widget, operation, function)
        return OriginalCommand(self, operation)

    def unregister(self, operation):
        '''Return the function for the operation, or None.

        Deleting the instance attribute unmasks the class attribute.
        '''
        if operation in self._operations:
            function = self._operations[operation]
            del self._operations[operation]
            try:
                delattr(self.widget, operation)
            except AttributeError:
                pass
            return function
        else:
            return None

    def dispatch(self, operation, *args):
        '''Callback from Tcl which runs when the widget is referenced.

        If an operation has been registered in self._operations, apply the
        associated function to the args passed into Tcl. Otherwise, pass the
        operation through to Tk via the original Tcl function.

        Note that if a registered function is called, the operation is not
        passed through to Tk.  Apply the function returned by self.register()
        to *args to accomplish that.  For an example, see colorizer.py.

        '''
        m = self._operations.get(operation)
        try:
            if m:
                return m(*args)
            else:
                return self.tk.call((self.orig, operation) + args)
        except TclError:
            return ""


class OriginalCommand:
    '''Callable for original tk command that has been redirected.

    Returned by .register; can be used in the function registered.
    redir = WidgetRedirector(text)
    def my_insert(*args):
        print("insert", args)
        original_insert(*args)
    original_insert = redir.register("insert", my_insert)
    '''

    def __init__(self, redir, operation):
        '''Create .tk_call and .orig_and_operation for .__call__ method.

        .redir and .operation store the input args for __repr__.
        .tk and .orig copy attributes of .redir (probably not needed).
        '''
        self.redir = redir
        self.operation = operation
        self.tk = redir.tk  # redundant with self.redir
        self.orig = redir.orig  # redundant with self.redir
        # These two could be deleted after checking recipient code.
        self.tk_call = redir.tk.call
        self.orig_and_operation = (redir.orig, operation)

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__,
                               self.redir, self.operation)

    def __call__(self, *args):
        return self.tk_call(self.orig_and_operation + args)
