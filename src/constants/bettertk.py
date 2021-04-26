from PIL import Image, ImageTk
import tkinter as tk

import sys
USING_WINDOWS = ("win" in sys.platform)

SNAP_THRESHOLD = 300


class BetterTk(tk.Frame):
    def __init__(self, *args, show_close=True, show_minimise=True, bg=None,
                 show_questionmark=False, show_fullscreen=True, _class=tk.Tk,
                 highlightthickness=5, titlebar_bg="white", titlebar_size=1,
                 titlebar_fg="black", titlebar_sep_colour="black",
                 sensitivity=10, disable_north_west_resizing=False,
                 notactivetitle_bg="grey17", **kwargs):
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
        if USING_WINDOWS:
            self.root.overrideredirect(True)
        else:
            self.root.attributes("-type", "splash")
        self.geometry(geometry)
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
        self.root.bind("<Button-2>", self.move_to_side)

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
        """
        When the dummy window gets focused it passes the focus to the main
        window. It also focuses the last focused widget.
        """
        self.root.lift()
        self.root.deiconify()
        if self.focused_widget is None:
            self.root.focus_force()
        else:
            self.focused_widget.focus_force()

    def get_focused_widget(self, event=None):
        widget = self.root.focus_get()
        if not ((widget == self.root) or (widget == None)):
            self.focused_widget = widget

    def change_bg(self, colour):
        """
        Changes the bg of the root.
        """
        self.get_focused_widget()
        items = (self.root, self.title_bar, self.title_frame,
                 self.buttons_frame, self.title_label)
        items += tuple(self.buttons.values())
        if self.icon_label is not None:
            items += (self.icon_label, )
        for item in items:
            item.config(background=colour)

    def config(self, bg=None, **kwargs):
        if bg is not None:
            self.change_bg(bg)
            kwargs.update({"bg": bg})
        self.root.config(**kwargs)

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
    def toggle_fullscreen(self, event=None):
        """
        Toggles fullscreen.
        """
        if (event is not None) and (not self.check_parent_titlebar(event)):
            return None
        # If it is the title bar toggle fullscreen:
        if self.is_full_screen:
            self.notfullscreen()
        else:
            self.fullscreen()

    def move_to_side(self, event=None):
        """
        Moves the window to the side that it's close to.
        """
        if (event is not None) and (not self.check_parent_titlebar(event)):
            return None
        rootx, rooty = self.root.winfo_rootx(), self.root.winfo_rooty()
        width = self.master_frame.winfo_width()
        height = self.master_frame.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        geometry = [rootx, rooty]

        if rootx < SNAP_THRESHOLD:
            geometry[0] = 0
        if rooty < SNAP_THRESHOLD:
            geometry[1] = 0
        if screen_width - (rootx + width) < SNAP_THRESHOLD:
            geometry[0] = screen_width - width
        if screen_height - (rooty + height) < SNAP_THRESHOLD:
            geometry[1] = screen_height - height
        self.geometry("+%i+%i" % tuple(geometry))

    def question(self):
        """
        This is called when the question mark is clicked. Only works
        when created with `show_questionmark=True`.
        """
        if self._question is not None:
            self._question()

    def minimise(self):
        """
        Minimises the window
        """
        self.dummy_root.iconify()
        self.root.withdraw()

    def fullscreen(self):
        """
        Switches to full screen.
        """
        # This toggles between the `fullscreen` and `notfullscreen` methods
        self.buttons["[]"].config(command=self.notfullscreen)
        self.root.overrideredirect(False)
        self.root.attributes("-fullscreen", True)
        self.is_full_screen = True

    def notfullscreen(self):
        """
        Switches to back to normal (not full) screen.
        """
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

            self.geometry("%ix%i+%i+%i" % tuple(new_params))
            return "break"
        # Dragging the window:
        if self.dragging:
            x = self.root.winfo_pointerx() - self._offsetx
            y = self.root.winfo_pointery() - self._offsety
            # Move to the cursor's location
            self.geometry("+%d+%d" % (x, y))

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
            if USING_WINDOWS:
                # Available on Windows
                self.master_frame.config(cursor="size_ne_sw")
            else:
                # Available on Linux
                if quadrant_resizing == "nw":
                    self.master_frame.config(cursor="bottom_left_corner")
                else:
                    self.master_frame.config(cursor="top_right_corner")
        elif (quadrant_resizing == "nw") or (quadrant_resizing == "se"):
            if USING_WINDOWS:
                # Available on Windows
                self.master_frame.config(cursor="size_nw_se")
            else:
                # Available on Linux
                if quadrant_resizing == "nw":
                    self.master_frame.config(cursor="top_left_corner")
                else:
                    self.master_frame.config(cursor="bottom_right_corner")
        elif (quadrant_resizing == "n") or (quadrant_resizing == "s"):
            # Available on Windows/Linux
            self.master_frame.config(cursor="sb_v_double_arrow")
        elif (quadrant_resizing == "e") or (quadrant_resizing == "w"):
            # Available on Windows/Linux
            self.master_frame.config(cursor="sb_h_double_arrow")

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

    def geometry(self, geometry):
        if not isinstance(geometry, str):
            raise ValueError("The geometry must be a string")
        if geometry.count("+") not in (0, 2):
            raise ValueError("Invalid geometry: \"%s\"" % repr(geometry)[1:-1])
        dummy_geometry = ""
        if "+" in geometry:
            _, posx, posy = geometry.split("+")
            dummy_geometry = "+%i+%i" % (int(posx) + 75, int(posy) + 20)
        self.root.geometry(geometry)
        self.dummy_root.geometry(dummy_geometry)

    def focus_force(self):
        self.root.deiconify()
        self.root.focus_force()

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

    def attributes(self, *args, **kwargs):
        self.root.attributes(*args, **kwargs)

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
