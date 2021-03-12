from PIL import Image, ImageTk
import tkinter as tk


class BetterTk(tk.Frame):
    def __init__(self, *args, show_close=True, show_minimise=True, bg=None,
                 show_questionmark=False, show_fullscreen=True, _class=tk.Tk,
                 highlightthickness=5, titlebar_bg="white", titlebar_size=1,
                 titlebar_fg="black", titlebar_sep_colour="black",
                 sensitivity=10, disable_north_west_resizing=False,
                 notactivetitle_bg="grey20", **kwargs):
        if bg is None:
            bg = titlebar_bg
        # Set up the window
        self.root = _class(*args, **kwargs)
        self.focused_widget = None
        self.dummy_root = tk.Toplevel(self.root)
        self.dummy_root.geometry("1x1")
        self.dummy_root.bind("<FocusIn>", self.focus_main)
        self.root.update()
        self.destroyed = False
        self.is_full_screen = False
        self.sensitivity = sensitivity
        geometry = "+%i+%i" % (self.root.winfo_x(), self.root.winfo_y())
        self.root.overrideredirect(True)
        self.root.geometry(geometry)
        self.dummy_root.geometry(geometry)
        self.root.bind("<FocusIn>", lambda e:self.change_bg(titlebar_bg))
        self.root.bind("<FocusOut>", lambda e:self.change_bg(notactivetitle_bg))

        self.root.config(bg=bg)

        # Master frame so that I can add a grey border around the window
        self.master_frame = tk.Frame(self.root, highlightbackground="grey",
                                     highlightthickness=3, bd=0)
        self.master_frame.bind("<Enter>", self.change_cursor_resizing)
        self.master_frame.bind("<Motion>", self.change_cursor_resizing)
        self.master_frame.pack(expand=True, fill="both")

        # The callback for when the "?" is pressed
        self._question = None

        # Set up the title bar frame
        self.title_bar = tk.Frame(self.master_frame, bg=titlebar_bg, bd=0,
                                  cursor="arrow")
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
        self.root.bind("<Button-1>", self.mouse_press)
        self.root.bind("<ButtonRelease-1>", self.mouse_release)
        self.root.bind("<B1-Motion>", self.mouse_motion)

        # Variables for resizing:
        self.started_resizing = False
        self.quadrant_resizing = None
        self.disable_north_west_resizing = disable_north_west_resizing
        self.resizable_horizontal = True
        self.resizable_vertical = True

        self.title_frame = tk.Frame(self.title_bar, bg=titlebar_bg)
        self.buttons_frame = tk.Frame(self.title_bar, bg=titlebar_bg)

        self.title_frame.pack(expand=True, side="left", anchor="w", padx=5)
        self.buttons_frame.pack(expand=True, side="right", anchor="e")

        self.title_label = tk.Label(self.title_frame, text="Better Tk",
                                    bg=titlebar_bg, fg=titlebar_fg)
        self.title_label.grid(row=1, column=2, sticky="news")
        self.icon_label = None

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

        # The actual <tk.Frame> where you can put your widgets
        super().__init__(self.master_frame, bd=0, bg=bg, cursor="arrow")
        super().pack(expand=True, side="bottom", fill="both")

    def focus_main(self, event=None):
        self.root.lift()
        self.root.deiconify()
        #pos = self.root.winfo_rootx(), self.root.winfo_rooty()
        #self.dummy_root.geometry("+%i+%i" % pos)
        if self.focused_widget is None:
            self.root.focus_force()
        else:
            self.focused_widget.focus_force()

    def get_focused_widget(self, event=None):
        widget = self.root.focus_get()
        if not ((widget == self.root) or (widget == None)):
            self.focused_widget = widget

    def change_bg(self, colour):
        self.get_focused_widget()
        items = (self.root, self.title_bar, self.title_frame,
                 self.buttons_frame, self.title_label)
        items += tuple(self.buttons.values())
        if self.icon_label is not None:
            items += (self.icon_label, )
        for item in items:
            item.config(background=colour)

    def check_parent_titlebar(self, event):
        # Get the widget that was pressed:
        widget = event.widget
        # Check if it is part of the title bar or something else
        # It checks its parent and its parent's parent and
        # its parent's parent's parent and ... until it finds
        # whether or not the widget clicked on is the title bar.
        while widget != self.root:
            if widget == self.buttons_frame:
                # Don't allow moving the window when buttons are clicked
                return False
            if widget == self.title_bar:
                return True
            widget = widget.master
        return False

    # Titlebar buttons:
    def toggle_fullscreen(self, event):
        if not self.check_parent_titlebar(event):
            return None
        # If it is the title bar toggle fullscreen:
        if self.is_full_screen:
            self.notfullscreen()
        else:
            self.fullscreen()

    def question(self):
        if self._question is not None:
            self._question()

    def minimise(self):
        self.dummy_root.iconify()
        self.root.withdraw()

    def fullscreen(self):
        # This toggles between the `fullscreen` and `notfullscreen` methods
        self.buttons["[]"].config(command=self.notfullscreen)
        self.root.overrideredirect(False)
        self.root.attributes("-fullscreen", True)
        self.is_full_screen = True

    def notfullscreen(self):
        # This toggles between the `fullscreen` and `notfullscreen` methods
        self.buttons["[]"].config(command=self.fullscreen)
        self.root.attributes("-fullscreen", False)
        self.root.overrideredirect(True)
        self.is_full_screen = False

    # Resizing and dragging:
    def mouse_motion(self, event):
        # Resizing:
        if self.started_resizing:
            new_params = [self.current_width, self.current_height,
                          self.currentx, self.currenty]

            if "e" in self.quadrant_resizing:
                self.update_resizing_params(new_params, self.resize_east())
            if "n" in self.quadrant_resizing:
                self.update_resizing_params(new_params, self.resize_north())
            if "s" in self.quadrant_resizing:
                self.update_resizing_params(new_params, self.resize_south())
            if "w" in self.quadrant_resizing:
                self.update_resizing_params(new_params, self.resize_west())

            self.root.geometry("%ix%i+%i+%i" % tuple(new_params))
            new_params = (new_params[2] + 75, new_params[3] + 20)
            self.dummy_root.geometry("+%i+%i" % new_params)
            return "break"
        # Dragging the window:
        if self.dragging:
            x = self.root.winfo_pointerx() - self._offsetx
            y = self.root.winfo_pointery() - self._offsety
            # Move to the cursor's location
            self.root.geometry("+%d+%d" % (x, y))
            self.dummy_root.geometry("+%i+%i" % (x + 75, y + 20))

    def mouse_release(self, event):
        self.dragging = False
        self.started_resizing = False

    def mouse_press(self, event):
        # Resizing the window:
        if event.widget == self.master_frame:
            self.current_width = self.root.winfo_width()
            self.current_height = self.root.winfo_height()
            self.currentx = self.root.winfo_rootx()
            self.currenty = self.root.winfo_rooty()

            quadrant_resizing = self.get_quadrant_resizing()

            if len(quadrant_resizing) > 0:
                self.started_resizing = True
                self.quadrant_resizing = quadrant_resizing

        # If it is the title bar start dragging:
        if not self.check_parent_titlebar(event):
            return None
        # Dragging the window:
        self.dragging = True
        self._offsetx = event.x+event.widget.winfo_rootx()-\
                        self.root.winfo_rootx()
        self._offsety = event.y+event.widget.winfo_rooty()-\
                        self.root.winfo_rooty()

    # For resizing:
    def change_cursor_resizing(self, event):
        if self.started_resizing:
            return None
        quadrant_resizing = self.get_quadrant_resizing()
        if quadrant_resizing == "":
            # Reset the cursor back to "arrow"
            self.master_frame.config(cursor="arrow")
        elif (quadrant_resizing == "ne") or (quadrant_resizing == "sw"):
            self.master_frame.config(cursor="size_ne_sw")
        elif (quadrant_resizing == "nw") or (quadrant_resizing == "se"):
            self.master_frame.config(cursor="size_nw_se")
        elif (quadrant_resizing == "n") or (quadrant_resizing == "s"):
            self.master_frame.config(cursor="size_ns")
        elif (quadrant_resizing == "e") or (quadrant_resizing == "w"):
            self.master_frame.config(cursor="size_we")

    def get_quadrant_resizing(self):
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        width, height = self.root.winfo_width(), self.root.winfo_height()

        x -= self.root.winfo_rootx()
        y -= self.root.winfo_rooty()
        quadrant_resizing = ""
        if self.resizable_vertical:
            if y + self.sensitivity > height:
                quadrant_resizing += "s"
            if not self.disable_north_west_resizing:
                if y < self.sensitivity:
                    quadrant_resizing += "n"
        if self.resizable_horizontal:
            if x + self.sensitivity > width:
                quadrant_resizing += "e"
            if not self.disable_north_west_resizing:
                if x < self.sensitivity:
                    quadrant_resizing += "w"
        return quadrant_resizing

    def resize_east(self):
        x = self.root.winfo_pointerx()
        new_width = x - self.currentx
        if new_width < 240:
            new_width = 240
        return new_width, None, None, None

    def resize_south(self):
        y = self.root.winfo_pointery()
        new_height = y - self.currenty
        if new_height < 80:
            new_height = 80
        return None, new_height, None, None

    def resize_north(self):
        y = self.root.winfo_pointery()
        dy = self.currenty - y
        if dy < 80 - self.current_height:
            dy = 80 - self.current_height
        new_height = self.current_height + dy
        return None, new_height, None, self.currenty - dy

    def resize_west(self):
        x = self.root.winfo_pointerx()
        dx = self.currentx - x
        if dx < 240 - self.current_width:
            dx = 240 - self.current_width
        new_width = self.current_width + dx
        return new_width, None, self.currentx - dx, None

    def update_resizing_params(self, _list, _tuple):
        for i in range(len(_tuple)):
            element = _tuple[i]
            if element is not None:
                _list[i] = element

    def destroy(self):
        # Using a flag here because `self.root.destroy()` calls
        # '<this frame>.destroy()' which calls `self.root.destroy()`
        # in an infinite loop
        # Do NOT call this directly
        if not self.destroyed:
            self.destroyed = True
            self.title_bar.destroy()
            super().destroy()
            self.master_frame.destroy()

    # Normal <tk.Tk> methods:
    def title(self, title):
        # Changing the title of the window
        # Note the name will aways be shows and the window can't be resized
        # to cover it up.
        self.title_label.config(text=title)
        self.root.title(title)
        self.dummy_root.title(title)

    def focus_force(self):
        self.root.deiconify()
        self.root.focus_force()

    def geometry(self, *args, **kwargs):
        self.root.geometry(*args, **kwargs)

    def close(self):
        self.root.destroy()

    def iconbitmap(self, filename):
        if self.icon_label is not None:
            self.icon_label.destroy()
        self.root.iconbitmap(filename)
        self.dummy_root.iconbitmap(filename)
        self.root.update_idletasks()
        size = self.title_frame.winfo_height()
        img = Image.open(filename).resize((size, size), Image.LANCZOS)
        self.icon = ImageTk.PhotoImage(img, master=self.root)
        colour = self.root.cget("background")
        self.icon_label = tk.Label(self.title_frame, image=self.icon, bg=colour)
        self.icon_label.grid(row=1, column=1, sticky="news")

    def resizable(self, width=None, height=None):
        if width is not None:
            self.resizable_horizontal = width
        if height is not None:
            self.resizable_vertical = height
        return None

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
                    titlebar_size=TITLEBAR_SIZE, bg="black")

    def function():
        print("question was pressed")
    root.buttons["?"].config(command=function)

    label = tk.Label(root, text="-"*10+" This is the better Tk "+"-"*10,
                     bg=BG_COLOUR, fg=FG_COLOUR)
    label.grid(row=1, column=1, sticky="news")

    entry = tk.Entry(root, bg=BG_COLOUR, fg=FG_COLOUR)
    entry.grid(row=2, column=1, sticky="news")

    root.mainloop()
