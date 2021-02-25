import tkinter as tk


class BetterTk(tk.Frame):
    def __init__(self, *args, show_close=True, show_minimise=True, bg=None,
                 show_questionmark=False, show_fullscreen=True, _class=tk.Tk,
                 highlightthickness=3, titlebar_bg="white", titlebar_size=1,
                 titlebar_fg="black", titlebar_sep_colour="black", **kwargs):
        if bg is None:
            bg = titlebar_bg
        # Set up the window
        self.root = _class(*args, **kwargs)
        self.root.update()
        self.destroyed = False
        geometry = "+%i+%i" % (self.root.winfo_x(), self.root.winfo_y())
        self.root.overrideredirect(True)
        self.root.geometry(geometry)
        self.root.bind("<Map>", self.check_map)
        self.root.config(background=titlebar_bg)

        # Master frame so that I can add a grey border around the window
        self.master_frame = tk.Frame(self.root, highlightbackground="grey",
                                     highlightthickness=1, bd=0)
        self.master_frame.pack(expand=True, fill="both")

        # The callback for when the "?" is pressed
        self._question = None

        super().__init__(self.master_frame, bd=0)
        super().pack(expand=True, side="bottom", fill="both")

        # Set up the title bar frame
        self.title_bar = tk.Frame(self.master_frame, bg=titlebar_bg, bd=0)
        self.title_bar.pack(side="top", fill="x")

        # When the user double clicks on the titlebar
        self.root.bind("<Double-Button-1>", self.toggle_fullscreen)

        # Add a separator
        self.separator = tk.Frame(self.master_frame, bg=titlebar_sep_colour,
                                  height=titlebar_size, bd=0)
        self.separator.pack(fill="x")

        # Set up the variables for dragging the window
        self._offsetx = 0
        self._offsety = 0
        self.dragging = False
        self.root.bind("<Button-1>", self.clickwin)
        self.root.bind("<ButtonRelease-1>", self.stopclickwin)
        self.root.bind("<B1-Motion>", self.dragwin)

        self.title_frame = tk.Frame(self.title_bar, bg=titlebar_bg)
        self.buttons_frame = tk.Frame(self.title_bar, bg=titlebar_bg)

        self.title_frame.pack(expand=True, side="left", anchor="w", padx=5)
        self.buttons_frame.pack(expand=True, side="right", anchor="e")

        self.title_label = tk.Label(self.title_frame, text="Better Tk",
                                    bg=titlebar_bg, fg=titlebar_fg)
        self.title_label.grid(row=1, column=1, sticky="news")

        # Set up all of the buttons
        self.buttons = {}
        column = 1
        if show_questionmark:
            button = tk.Button(self.buttons_frame, text="?", relief="flat",
                               command=self.question, bg=titlebar_bg,
                               fg=titlebar_fg)
            button.grid(row=1, column=column)
            self.buttons.update({"?": button})
            column += 1
        if show_minimise:
            button = tk.Button(self.buttons_frame, text="_", relief="flat",
                               command=self.minimise, bg=titlebar_bg,
                               fg=titlebar_fg)
            button.grid(row=1, column=column)
            self.buttons.update({"_": button})
            column += 1
        if show_fullscreen:
            button = tk.Button(self.buttons_frame, text="[]", relief="flat",
                               command=self.fullscreen, bg=titlebar_bg,
                               fg=titlebar_fg)
            button.grid(row=1, column=column)
            self.buttons.update({"[]": button})
            column += 1
        if show_close:
            button = tk.Button(self.buttons_frame, text="X", relief="flat",
                               command=self.close, bg=titlebar_bg,
                               fg=titlebar_fg)
            button.grid(row=1, column=column)
            self.buttons.update({"X": button})
            column += 1

    def check_parent_titlebar(self, event):
        # Get the widget that was pressed:
        widget = event.widget
        # Check if it is part of the title bar or something else
        # It checks its parent and its parent's parent and
        # its parent's parent's parent and ... until it finds
        # whether or not the widget clicked on is the title bar.
        while widget != self.root:
            if widget == self:
                # If it isn't the title bar just stop
                return False
            widget = widget.master
        return True

    def toggle_fullscreen(self, event):
        if not self.check_parent_titlebar(event):
            return None
        # If it is the title bar toggle fullscreen:
        if self.root.attributes("-fullscreen"):
            self.notfullscreen()
        else:
            self.fullscreen()

    def title(self, title):
        # Changing the title of the window
        self.title_label.config(text=title)

    def geometry(self, *args, **kwargs):
        self.root.geometry(*args, **kwargs)

    def question(self):
        if self._question is not None:
            self._question()

    def close(self):
        self.root.destroy()

    def minimise(self):
        self.root.withdraw()
        self.root.overrideredirect(False)
        self.root.iconify()

    def check_map(self, event):
        # Whenever the user clicks on the window from the Windows bar
        # Kindly plagiarised from:
        # https://stackoverflow.com/a/52720802/11106801
        self.root.overrideredirect(True)

    def fullscreen(self):
        # This toggles between the `fullscreen` and `notfullscreen` methods
        self.buttons["[]"].config(command=self.notfullscreen)
        self.root.overrideredirect(False)
        self.root.attributes("-fullscreen", True)

    def notfullscreen(self):
        # This toggles between the `fullscreen` and `notfullscreen` methods
        self.buttons["[]"].config(command=self.fullscreen)
        self.root.attributes("-fullscreen", False)
        self.root.overrideredirect(True)

    def dragwin(self, event):
        # If started dragging:
        if self.dragging:
            x = self.root.winfo_pointerx() - self._offsetx
            y = self.root.winfo_pointery() - self._offsety
            # Move to the cursor's location
            self.root.geometry("+%d+%d"%(x, y))

    def stopclickwin(self, event):
        self.dragging = False

    def clickwin(self, event):
        if not self.check_parent_titlebar(event):
            return None
        # If it is the title bar start dragging:
        self.dragging = True
        self._offsetx = event.x+event.widget.winfo_rootx()-\
                        self.root.winfo_rootx()
        self._offsety = event.y+event.widget.winfo_rooty()-\
                        self.root.winfo_rooty()

    def destroy(self):
        # Using a flag here because `self.root.destroy()` calls
        # '<this frame>.destroy()' which calls `self.root.destroy()`
        # in an infinite loop
        if not self.destroyed:
            self.destroyed = True
            self.title_bar.destroy()
            super().destroy()
            self.master_frame.destroy()

    def protocol(self, *args, **kwargs):
        raise Exception("Use `<BetterTk>.buttons[\"X\"]"+\
                        ".config(command=<function>)` instead")


if __name__ == "__main__":
    BG_COLOUR = "black"
    FG_COLOUR = "white"
    TITLEBAR_COLOUR = "light grey"
    TITLEBAR_SIZE = 1

    root = BetterTk(show_questionmark=True, titlebar_bg=BG_COLOUR,
                    titlebar_fg=TITLEBAR_COLOUR, titlebar_sep_colour=FG_COLOUR,
                    titlebar_size=TITLEBAR_SIZE)

    def function():
        print("question was pressed")
    root.buttons["?"].config(command=function)

    label = tk.Label(root, text="-"*10+" This is the better Tk "+"-"*10,
                     bg=BG_COLOUR, fg=FG_COLOUR)
    label.grid(row=1, column=1, sticky="news")

    entry = tk.Entry(root, bg=BG_COLOUR, fg=FG_COLOUR)
    entry.grid(row=2, column=1, sticky="news")

    #root.mainloop()
