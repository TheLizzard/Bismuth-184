import tkinter as tk


class FindReplaceBox:
    def __init__(self, text):
        self.text = text
        self.found_tag = []

    def show(self, type):
        if type == "find":
            self.show_find()
        elif type == "replace":
            self.show_replace()
        else:
            raise ValueError("Unkown type: "+str(type))

    def show_replace(self):
        self.show_find()
        self.label_replace = tk.Label(self.root, text="Replace:")
        self.entry_replace = tk.Entry(self.root)
        self.button_replace = tk.Button(self.root, text="Replace All",
                                        command=self.replace)
        self.label_replace.grid(row=2, column=1, sticky="nes")
        self.entry_replace.grid(row=2, column=2, sticky="news")
        self.button_replace.grid(row=2, column=3, sticky="news")

        # Change the tab order of the widgets
        new_order = (self.entry_find, self.entry_replace, self.button_find,
                     self.button_replace, self.options_menu)
        for widget in new_order:
            widget.lift()

    def show_find(self):
        self.root = tk.Toplevel()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.label_find = tk.Label(self.root, text="Find:")
        self.entry_find = tk.Entry(self.root)
        self.button_find = tk.Button(self.root, text="Find Next",
                                     command=self.find_next)
        self.options_menu = tk.Frame(self.root)
        self.set_up_options()

        self.label_find.grid(row=1, column=1, sticky="nes")
        self.entry_find.grid(row=1, column=2, sticky="news")
        self.button_find.grid(row=1, column=3, sticky="news")
        self.options_menu.grid(row=3, column=1, columnspan=3, sticky="news")

        self.entry_find.focus()

    def remove_tags(self, event=None):
        self.text.tag_remove("found", "0.0", "end")

    def set_up_options(self):
        self.regex_var = tk.BooleanVar()
        self.case_var = tk.BooleanVar()
        self.wholeword_var = tk.BooleanVar()
        self.direction_var = tk.BooleanVar()

        self.label_options = tk.Label(self.options_menu, text="Options: ")
        self.checkbox_regex = tk.Checkbutton(self.options_menu, text="Regex",
                                             var=self.regex_var)
        self.checkbox_case = tk.Checkbutton(self.options_menu,
                                            text="Match Case",
                                            var=self.case_var)
        self.checkbox_wholeword = tk.Checkbutton(self.options_menu,
                                                 text="Whole word",
                                                 var=self.wholeword_var)
        self.label_options.grid(row=1, column=1, sticky="nes")
        self.checkbox_regex.grid(row=1, column=2, sticky="news")
        self.checkbox_case.grid(row=1, column=3, sticky="news")
        self.checkbox_wholeword.grid(row=1, column=4, sticky="news")

        self.label_direction = tk.Label(self.options_menu, text="Direction: ")
        self.radio_up = tk.Radiobutton(self.options_menu, text="Up",
                                       value=True, var=self.direction_var)
        self.radio_down = tk.Radiobutton(self.options_menu, text="Down",
                                         value=False, var=self.direction_var)
        self.label_direction.grid(row=2, column=1, sticky="news")
        self.radio_up.grid(row=2, column=2)
        self.radio_down.grid(row=2, column=3)

    def find_next(self):
        direction = self.direction_var.get()
        self.find_and_tag(direction)
        idx = self.text.index("insert")
        l, c = map(int, idx.split("."))
        for start, end in self.found_tag:
            end_l, end_c = map(int, end.split("."))
            if (end_l > l) or ((end_l == l) and (end_c > c)):
                self.text.tag_remove("sel", "0.0", "end")
                self.text.tag_add("sel", start, end)
                self.text.see(start)
                self.text.see(end)
                self.text.mark_set("insert", end)
                return None
        if len(self.found_tag) > 0:
            start, end = self.found_tag[0]
            self.text.tag_remove("sel", "0.0", "end")
            self.text.tag_add("sel", start, end)
            self.text.mark_set("insert", end)

    def find_and_tag(self, direction=None):
        self.found_tag = []
        self.remove_tags()
        search_str = self.entry_find.get()
        regex = self.regex_var.get()
        case = not self.case_var.get()
        exact = self.wholeword_var.get()
        if search_str == "":
            return None
        idx = "0.0"
        while True:
            var = tk.StringVar()
            idx = self.text.search(search_str, idx, nocase=case, regexp=regex,
                                   stopindex="end", count=var, exact=exact,
                                   backwards=direction)
            if not idx:
                break
            lastidx = "%s+%ic" % (idx, int(var.get()))
            self.text.tag_add("found", idx, lastidx)
            pair = (self.text.index(idx), self.text.index(lastidx))
            self.found_tag.append(pair)
            idx = lastidx

    def replace(self):
        autoseparators = self.text["autoseparators"]
        self.text["autoseparators"] = False
        self.text.edit_separator()
        self.find_and_tag()
        target = self.entry_replace.get()
        for start, end in reversed(self.found_tag):
            self.text.delete(start, end)
            self.text.insert(start, target)
        self.close()
        self.text.edit_separator()
        self.text["autoseparators"] = autoseparators

    def close(self):
        self.root.destroy()


if __name__ == "__main__":
    class Text(tk.Text):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.bind("<Control-f>", self.find)
            self.bind("<Control-F>", self.find)
            self.bind("<Control-r>", self.replace)
            self.bind("<Control-R>", self.replace)

        def find(self, event):
            replace = FindReplaceBox(self)
            replace.show("find")

        def replace(self, event):
            replace = FindReplaceBox(self)
            replace.show("replace")


    root = tk.Tk()
    text = Text(root, autoseparators=True, undo=True, maxundo=-1)
    text.pack()
    root.mainloop()
