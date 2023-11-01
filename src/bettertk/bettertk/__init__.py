from PIL import Image, ImageTk
import tkinter as tk


try:
    from get_os import IS_WINDOWS, IS_UNIX, HAS_X11
    if IS_WINDOWS:
        from notitlebartk_win import NoTitlebarTk
    elif HAS_X11:
        from notitlebartk_x11 import NoTitlebarTk
    else:
        raise NotImplementedError("Not Windows and no libX11.so.6")
except ImportError:
    from .get_os import IS_WINDOWS, IS_UNIX, HAS_X11
    if IS_WINDOWS:
        from .notitlebartk_win import NoTitlebarTk
    elif HAS_X11:
        from .notitlebartk_x11 import NoTitlebarTk
    else:
        raise NotImplementedError("Not Windows and no libX11.so.6")


THEME_OPTIONS = ("light", "dark")

# Unchangable settings:
NUMBER_OF_CUSTOM_BUTTONS = 10 # The number of custom buttons allowed at 1 time
MIN_WIDTH = 240 # The minimum width to hide the dummy window
MIN_HEIGHT = 80 # The minimum height to hide the dummy window


__author__ = "TheLizzard"


class BetterTkSettings:
    def __init__(self, theme="dark", use_unicode=False, separator_size=1,
                 bd=3):
        self.SEPARATOR_SIZE = separator_size
        self.BORDER_WIDTH = bd

        self.USE_UNICODE = use_unicode

        if theme == "dark":
            self.BG = "black"
            self.SEP_COLOUR = "grey"
            self.HIGHLIGHT = "grey"
            self.ACTIVE_TITLEBAR_BG = "black"
            self.ACTIVE_TITLEBAR_FG = "white"
            self.INACTIVE_TITLEBAR_BG = "grey20"
            self.INACTIVE_TITLEBAR_FG = "white"
        elif theme == "light":
            self.BG = "#f0f0ed"
            self.SEP_COLOUR = "grey"
            self.HIGHLIGHT = "grey"
            self.ACTIVE_TITLEBAR_BG = "white"
            self.ACTIVE_TITLEBAR_FG = "black"
            self.INACTIVE_TITLEBAR_BG = "grey80"
            self.INACTIVE_TITLEBAR_FG = "black"
        else:
            raise ValueError("Invalid theme option.")

        # Keep track of the number of BetterTk windows attached to this
        self.bettertk_users = 0

    def started_using(self) -> None:
        self.bettertk_users += 1

    def stoped_using(self) -> None:
        self.bettertk_users -= 1

    def config(self, bg=None, separator_colour=None, hightlight_colour=None,
               active_titlebar_bg=None, active_titlebar_fg=None,
               inactive_titlebar_bg=None, inactive_titlebar_fg=None, bd=None,
               use_unicode=None, separator_size=None):
        """
        Possible settings:
            bg:str                    The window's background colour
            separator_colour:str      The separator's colour that is between
                                      the titlebar and your widgets
            hightlight_colour:str     The colour of the window's edges
            active_titlebar_bg:str
            active_titlebar_fg:str
            inactive_titlebar_bg:str
            inactive_titlebar_fg:str

            use_unicode:bool          If the window should use unicode
                                      characters for the buttons
            separator_size:int        The separator's height that is between
                                      the titlebar and your widgets
                                      (Best to keep it around 1)
            bd:int                    The boarder width of the window

        Notes:
            You can't change the settings while there is a BetterTk window
            attached to this object. If you want to change the background of
            the window use `<BetterTk>.config(bg=...)`
        """
        if self.bettertk_users != 0:
            raise Exception("It isn't safe to change the settings while " \
                            "the window is running.")
        if bg is not None:
            self.BG = bg
        if separator_colour is not None:
            self.SEP_COLOUR = separator_colour
        if hightlight_colour is not None:
            self.HIGHLIGHT = hightlight_colour
        if active_titlebar_bg is not None:
            self.ACTIVE_TITLEBAR_BG = active_titlebar_bg
        if active_titlebar_fg is not None:
            self.ACTIVE_TITLEBAR_FG = active_titlebar_fg
        if inactive_titlebar_bg is not None:
            self.INACTIVE_TITLEBAR_BG = inactive_titlebar_bg
        if inactive_titlebar_fg is not None:
            self.INACTIVE_TITLEBAR_FG = inactive_titlebar_fg
        if bd is not None:
            self.BORDER_WIDTH = bd
        if use_unicode is not None:
            self.USE_UNICODE = use_unicode
        if separator_size is not None:
            self.SEPARATOR_SIZE = separator_size
    configure = config


DEFAULT_SETTINGS = BetterTkSettings()
DEFAULT_SETTINGS.started_using()


class CustomButton(tk.Button):
    def __init__(self, master, betterroot, name="#", function=None, column=0):
        self.betterroot = betterroot
        if function is None:
            self.callback = lambda: None
        else:
            self.callback = function
        super().__init__(master, text=name, relief="flat", takefocus=False,
                         command=lambda: self.callback())
        if HAS_X11:
            super().config(bd=0, highlightthickness=0)
        self.column = column

        # active_bg = self.betterroot.settings.ACTIVE_TITLEBAR_BG
        # active_fg = self.betterroot.settings.ACTIVE_TITLEBAR_FG
        inactive_bg = self.betterroot.settings.INACTIVE_TITLEBAR_BG
        inactive_fg = self.betterroot.settings.INACTIVE_TITLEBAR_FG
        super().config(bg=inactive_bg, activebackground=inactive_bg,
                       fg=inactive_fg, activeforeground=inactive_fg)
        self.show()

    def show(self, column=None):
        """
        Shows the button on the screen
        """
        if column is None:
            column = self.column
        self.shown = True
        super().grid(row=1, column=column)

    def hide(self):
        """
        Hides the button from the screen
        """
        self.shown = False
        super().grid_forget()


class MinimiseButton(tk.Button):
    def __init__(self, master, betterroot, settings:BetterTkSettings):
        self.betterroot = betterroot
        if settings.USE_UNICODE:
            text = "\u2014"
        else:
            text = "_"
        super().__init__(master, text=text, relief="flat", takefocus=False,
                         command=self.betterroot.root.iconify)
        if HAS_X11:
            super().config(bd=0, highlightthickness=0)
        self.show()

    def show(self, column:int=NUMBER_OF_CUSTOM_BUTTONS+2) -> None:
        """
        Shows the button on the screen
        """
        self.shown = True
        super().grid(row=1, column=column)

    def hide(self) -> None:
        """
        Hides the button from the screen
        """
        self.shown = False
        super().grid_forget()


class MaximiseButton(tk.Button):
    def __init__(self, master, betterroot, settings:BetterTkSettings):
        self.betterroot = betterroot
        if settings.USE_UNICODE:
            text = "\u2610"
        else:
            text = "[]"
        super().__init__(master, text=text, relief="flat", takefocus=False,
                         command=self.betterroot.toggle_maximised)
        if HAS_X11:
            super().config(bd=0, highlightthickness=0)
        self.show()

    def show(self, column:int=NUMBER_OF_CUSTOM_BUTTONS+3) -> None:
        """
        Shows the button on the screen
        """
        self.shown = True
        super().grid(row=1, column=column)

    def hide(self) -> None:
        """
        Hides the button from the screen
        """
        self.shown = False
        super().grid_forget()


class CloseButton(tk.Button):
    def __init__(self, master, betterroot, settings:BetterTkSettings):
        self.betterroot = betterroot
        if settings.USE_UNICODE:
            text = "\u26cc" # "\u2715"
        else:
            text = "X"
        super().__init__(master, text=text, relief="flat", takefocus=False,
                         command=self.betterroot.generate_destroy)
        if HAS_X11:
            super().config(bd=0, highlightthickness=0)
        self.show()

    def show(self, column:int=NUMBER_OF_CUSTOM_BUTTONS+4) -> None:
        """
        Shows the button on the screen
        """
        self.shown = True
        super().grid(row=1, column=column)

    def hide(self) -> None:
        """
        Hides the button from the screen
        """
        self.shown = False
        super().grid_forget()


class BetterTk(tk.Frame):
    """
    Attributes:
        disable_north_west_resizing
        *Buttons*
            minimise_button
            maximise_button
            close_button
        *List of all buttons*
            buttons: [minimise_button, maximise_button, close_button, ...]

    Methods:
        *List of newly defined methods*
            __init__(master=None, settings:BetterTkSettings=DEFAULT_SETTINGS)
            protocol_generate(protocol:str) -> None
            topmost() -> None
            #custom_buttons#

        *List of methods that act the same was as tkinter.Tk's methods*
            title
            config
            protocol
            geometry
            focus_force
            destroy
            iconbitmap
            resizable
            attributes
            withdraw
            iconify
            deiconify
            maxsize
            minsize
            state
            report_callback_exception


    The buttons:
        minimise_button:
            minimise_window() => None
            show(column) => None
            hide() => None

        maximise_button:
            toggle_maximised() => None
            show(column) => None
            hide() => None

        close_button:
            close_window_protocol() => None
            show(column) => None
            hide() => None
        buttons: # It is a list of all of the buttons

    The custom_buttons:
        The proper way of using it is:
            ```
            root = BetterTk()

            root.custom_buttons = {"name": "?",
                                   "function": questionmark_pressed,
                                   "column": 0}
            questionmark_button = root.buttons[-1]

            root.custom_buttons = {"name": "\u2263",
                                   "function": three_lines_pressed,
                                   "column": 2}
            threelines_button = root.buttons[-1]
            ```
        You can call:
            show(column) => None
            hide() => None
    """
    def __init__(self, master=None, settings:BetterTkSettings=DEFAULT_SETTINGS,
                 withdraw:bool=False, **kwargs):
        self.settings = settings
        self.settings.started_using()
        self.allow_ctrl_w:bool = True
        self._overrideredirect:bool = False

        self.root = NoTitlebarTk(master, **kwargs)
        if withdraw:
            self.root.withdraw()
        self.protocols = {"WM_DELETE_WINDOW": self.destroy}
        self.root.protocol("WM_DELETE_WINDOW", self.generate_destroy)
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)

        bd = self.settings.BORDER_WIDTH
        # Master frame so that I can add a grey border around the window
        self.master_frame = tk.Frame(self.root, bd=0, highlightthickness=0,
                                     bg=self.settings.HIGHLIGHT)
        self.master_frame.pack(expand=True, fill="both")
        self.resizable_window = ResizableWindow(self.master_frame, self)

        # The actual <tk.Frame> where you can put your widgets
        super().__init__(self.master_frame, bd=0, bg=self.settings.BG,
                         cursor="arrow")

        # Set up the title bar frame
        self.title_bar = tk.Frame(self.master_frame, bd=0, cursor="arrow")
        self.title_bar.pack(side="top", fill="x", padx=bd, pady=(bd, 0))
        self.draggable_window = DraggableWindow(self.title_bar, self)

        # Needs to packed after `self.title_bar`.
        super().pack(expand=True, side="bottom", fill="both", padx=bd,
                     pady=(0, bd))

        # Separator
        self.separator = tk.Frame(self.master_frame, bd=0, cursor="arrow",
                                  bg=self.settings.SEP_COLOUR,
                                  height=self.settings.SEPARATOR_SIZE)
        self.separator.pack(fill="x")

        # Buttons frame
        self.buttons_frame = tk.Frame(self.title_bar, bd=0)
        self.buttons_frame.pack(expand=True, side="right", anchor="e")

        # Titlebar frame
        self.title_frame = tk.Frame(self.title_bar, bd=0)
        self.title_frame.pack(expand=True, side="left", anchor="w", padx=5)

        # Icon
        self._tk_icon = None
        self.icon_label = tk.Label(self.title_frame,
                                   bg=self.settings.ACTIVE_TITLEBAR_BG)
        self.icon_label.grid(row=1, column=1, sticky="news")

        # Title text
        self.title_label = tk.Label(self.title_frame, text="",
                                    bg=self.settings.ACTIVE_TITLEBAR_BG,
                                    fg=self.settings.ACTIVE_TITLEBAR_FG)
        self.title("Better Tk")
        self.title_label.grid(row=1, column=2, sticky="news")

        # Buttons
        self.minimise_button = MinimiseButton(self.buttons_frame, self,
                                              self.settings)
        self.maximise_button = MaximiseButton(self.buttons_frame, self,
                                              self.settings)
        self.close_button = CloseButton(self.buttons_frame, self, self.settings)

        # When the user double clicks on the titlebar
        self.bind_titlebar("<Double-Button-1>",
                           self.toggle_maximised)
        # When the user middle clicks on the titlebar
        self.bind_titlebar("<Button-2>", self.snap_to_side)

        self.buttons = [self.minimise_button, self.maximise_button,
                        self.close_button]

        bg = self.settings.INACTIVE_TITLEBAR_BG
        fg = self.settings.INACTIVE_TITLEBAR_FG
        for button in self.buttons:
            button.config(activebackground=bg, activeforeground=fg)

        if self.focus_displayof() is None:
            self.window_unfocused()
        else:
            self.window_focused()
        self.root.bind("<FocusIn>", self.window_focused, add=True)
        self.root.bind("<FocusOut>", self.window_unfocused, add=True)

        # This is actually needed otherwise sometimes the window
        #    doesn't autoresize to child widgets needing more than
        #    200 pixels of height. I have no clue why
        # def inner() -> None:
        #     self.root.geometry("")
        #     self.root.quit()
        # self.root.after(100, inner)
        # self.root.mainloop()
        self.root.update()     # DON'T TOUCH
        self.root.geometry("") # DON'T TOUCH

        if master is None:
            super().bind_all("<Control-w>", self.maybe_destroy)
            super().bind_all("<Control-W>", self.maybe_destroy)

        super().focus_set()

    def focus_displayof(self) -> tk.Misc|None:
        # Bug: https://github.com/python/cpython/issues/88758
        try:
            return self.root.focus_displayof()
        except KeyError:
            return self

    def fullscreen(self, *, wait:bool=False) -> None:
        self.root.fullscreen(wait=wait)

    def notfullscreen(self, *, wait:bool=False) -> None:
        self.root.notfullscreen(wait=wait)

    def toggle_fullscreen(self, event:tk.Event=None, *, wait:bool=False):
        """
        Toggles fullscreen.
        """
        # If it is called from double clicking:
        if event is not None:
            # Make sure that we didn't double click something else
            if not self.check_parent_titlebar(event):
                return None
        self.root.toggle_fullscreen(wait=wait)

    def maximised(self, *, wait:bool=False) -> None:
        self.root.maximised(wait=wait)

    def notmaximised(self, *, wait:bool=False) -> None:
        self.root.notmaximised(wait=wait)

    def toggle_maximised(self, event:tk.Event=None, *, wait:bool=False) -> None:
        """
        Toggles maximised.
        """
        # If it is called from double clicking:
        if event is not None:
            # Make sure that we didn't double click something else
            if not self.check_parent_titlebar(event):
                return None
        if self.resizable_window.resizable_horizontal and \
           self.resizable_window.resizable_vertical:
            self.root.toggle_maximised(wait=wait)

    def maybe_destroy(self, event:tk.Event) -> None:
        widget:tk.Misc = event.widget
        if isinstance(widget, str):
            # If the widget was already destroyed by something
            # Don't know when/why this happens?
            return None
        while (not isinstance(widget, BetterTk)) and (widget.master is not None):
            widget:tk.Misc = widget.master

        if widget == self.root:
            widget:tk.Misc = self
        if getattr(widget, "allow_ctrl_w", False):
            widget.generate_destroy()

    def generate_destroy(self) -> None:
        self.protocol_generate("WM_DELETE_WINDOW")

    def protocol(self, protocol:str=None, function=None):
        """
        Binds a function to a protocol.
        """
        if protocol is None:
            return tuple(self.protocols.keys())
        if function is None:
            return self.protocols[protocol]
        self.protocols.update({protocol: function})

    def protocol_generate(self, protocol:str) -> None:
        """
        Generates a protocol.
        """
        try:
            protocol:Function[None] = self.protocols[protocol]
        except KeyError:
            raise tk.TclError(f'Unknown protocol: "{protocol}"')
        protocol()

    def bind_titlebar(self, sequence:str=None, func=None, add:bool=None):
        to_bind = [self.title_bar]
        while len(to_bind) > 0:
            widget = to_bind.pop()
            widget.bind(sequence, func, add=add)
            to_bind.extend(widget.winfo_children())

    def snap_to_side(self, event:tk.Event=None) -> None:
        """
        Moves the window to the closest corner.
        """
        if (event is not None) and (not self.check_parent_titlebar(event)):
            return None
        rootx, rooty = self.root.winfo_rootx(), self.root.winfo_rooty()
        width = self.master_frame.winfo_width()
        height = self.master_frame.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        rootx += width//2
        rooty += height//2
        newx = int(rootx/screen_width*2)/2
        newy = int(rooty/screen_height*2)/2

        if int(newx) == newx:
            newx = int(newx*screen_width)
        else:
            newx = int((newx+0.5)*screen_width) - width

        if int(newy) == newy:
            newy = int(newy*screen_height)
        else:
            newy = int((newy+0.5)*screen_height) - height

        self.geometry(f"+{newx}+{newy}")

    def window_focused(self, event:tk.Event=None) -> None:
        if self.focus_displayof() is None:
            return None
        self.change_titlebar_bg(self.settings.ACTIVE_TITLEBAR_BG)
        self.change_titlebar_fg(self.settings.ACTIVE_TITLEBAR_FG)

    def window_unfocused(self, event:tk.Event=None) -> None:
        if self.focus_displayof() is not None:
            return None
        self.change_titlebar_bg(self.settings.INACTIVE_TITLEBAR_BG)
        self.change_titlebar_fg(self.settings.INACTIVE_TITLEBAR_FG)

    def change_titlebar_bg(self, colour:str) -> None:
        """
        Changes the titlebar's background colour.
        """
        items = (self.title_bar, self.buttons_frame, self.title_label,
                 self.icon_label) + tuple(self.buttons)
        for item in items:
            item.config(background=colour)

    def change_titlebar_fg(self, colour:str) -> None:
        """
        Changes the titlebar's foreground colour.
        """
        items = (self.title_label, )
        items += tuple(self.buttons)
        for item in items:
            item.config(foreground=colour)

    def bind_root(self, *args, **kwargs) -> str:
        """
        Binds the root. Please use only for events that aren't always
        associated with a widget like: "<KeyPress-f>" or "<Return>".
        Please don't use for events like "<Button-1>" or "<Enter>" or "Motion"
        """
        return self.root.bind(*args, **kwargs)

    def check_parent_titlebar(self, event:tk.Event) -> bool:
        return event.widget not in self.buttons

    @property
    def custom_buttons(self) -> [CustomButton, CustomButton, ...]:
        return self.buttons[3:]

    @custom_buttons.setter
    def custom_buttons(self, value:dict()) -> None:
        self.custom_button = CustomButton(self.buttons_frame, self, **value)
        self.buttons.append(self.custom_button)
        if self.focus_displayof() is None:
            self.window_unfocused()
        else:
            self.window_focused()

    @property
    def disable_north_west_resizing(self) -> bool:
        return self.resizable_window.disable_north_west_resizing

    @disable_north_west_resizing.setter
    def disable_north_west_resizing(self, value:bool) -> None:
        self.resizable_window.disable_north_west_resizing = value

    @property
    def is_fullscreen(self) -> bool:
        return self.root._fullscreen

    @property
    def is_maximised(self) -> bool:
        return self.root._maximised

    # Normal <tk.Tk> methods:
    def title(self, title:str=None) -> str:
        # Changing the title of the window
        # Note the name will aways be shows and the window can't be resized
        # to cover it up.
        if title is None:
            return self.root.title()
        self.title_label.config(text=title)
        self.root.title(title)

    def config(self, bg:str=None, **kwargs) -> dict:
        if bg is not None:
            super().config(bg=bg)
        return self.root.config(**kwargs)

    def topmost(self, value:bool) -> None:
        self.attributes("-topmost", bool(value))

    def overrideredirect(self, value:bool, *, border:bool=True) -> None:
        if value:
            self.turnon_overrideredirect(border=border)
        else:
            self.turnoff_overrideredirect()

    def turnon_overrideredirect(self, *, border:bool) -> None:
        if self._overrideredirect:
            return None
        self._overrideredirect:bool = True
        self.separator.pack_forget()
        self.title_bar.pack_forget()
        if border:
            bd:int = self.settings.BORDER_WIDTH
            kwargs:dict = dict(padx=bd, pady=bd)
        else:
            kwargs:dict = dict(padx=0, pady=0)
        super().pack(expand=True, fill="both", **kwargs)

    def turnoff_overrideredirect(self) -> None:
        if not self._overrideredirect:
            return None
        self._overrideredirect:bool = False
        bd:int = self.settings.BORDER_WIDTH
        self.title_bar.pack(side="top", fill="x", padx=bd, pady=(bd, 0))
        self.separator.pack(fill="x")
        super().pack(expand=True, side="bottom", fill="both", padx=bd,
                     pady=(0, bd))

    def geometry(self, geometry:str=None) -> str:
        return self.root.geometry(geometry)

    def focus_force(self) -> None:
        self.root.deiconify()
        self.root.focus_force()

    def destroy(self) -> None:
        self.settings.stoped_using()
        # Some trickery:
        self.master.children.pop(self._name)
        super().destroy()
        self.root.destroy()

    def _change_icon(self, image:Image.Image) -> None:
        if isinstance(image, str):
            self._tk_icon_2 = ImageTk.PhotoImage(file=image, master=self)
            image:Image.Image = Image.open(image)
        elif isinstance(image, Image.Image):
            self._tk_icon_2 = ImageTk.PhotoImage(image, master=self)
        else:
            raise ValueError("Image must be a str path or a PIL.Image.Image "\
                             "otherwise the image can't be resized")
        self.root.update_idletasks()
        # The 4 is because of the label's border
        size = self.title_frame.winfo_height() - 4
        img = image.resize((size, size), Image.LANCZOS)
        self._tk_icon = ImageTk.PhotoImage(img, master=self.root)
        self.icon_label.config(image=self._tk_icon)

    def iconbitmap(self, filepath:str) -> None:
        assert isinstance(filepath, str), "TypeError"
        # I recommend `.iconphoto` instead
        self._change_icon(filepath)
        self.root.iconbitmap(filepath)

    def iconphoto(self, default:bool, image:str|Image.Image) -> None:
        assert isinstance(default, bool), "TypeError"
        self._change_icon(image)
        self.root.iconphoto(default, self._tk_icon_2)

    def resizable(self, width:int=None, height:int=None) -> (bool, bool):
        if width is not None:
            self.resizable_window.resizable_horizontal = width
        if height is not None:
            self.resizable_window.resizable_vertical = height

        if (width is None) and (height is None):
            return (self.resizable_window.resizable_horizontal,
                    self.resizable_window.resizable_vertical)

        if self.resizable_window.resizable_horizontal and \
           self.resizable_window.resizable_vertical:
            if self.maximise_button.shown:
                self.maximise_button.show()
        else:
            self.maximise_button.grid_forget()
        return None

    def attributes(self, *args, **kwargs):
        return self.root.attributes(*args, **kwargs)

    def withdraw(self, *args, **kwargs) -> None:
        return self.root.withdraw(*args, **kwargs)

    def iconify(self, *args, **kwargs) -> None:
        return self.root.iconify(*args, **kwargs)

    def deiconify(self, *args, **kwargs) -> None:
        return self.root.deiconify(*args, **kwargs)

    def maxsize(self, *args, **kwargs):
        return self.root.maxsize(*args, **kwargs)

    def minsize(self, *args, **kwargs):
        return self.root.minsize(*args, **kwargs)

    def state(self, *args, **kwargs):
        return self.root.state(*args, **kwargs)

    def grab_set(self, *args, **kwargs):
        return self.root.grab_set(*args, **kwargs)

    # This method has problems. I am looking for a solution but...
    # def bind_all(self, *args, **kwargs):
    #     raise NotImplementedError("This is the only method that hasn't been "\
    #                               "implemented. Please try to use another "\
    #                               "method.")


class ResizableWindow:
    def __init__(self, frame, betterroot):
        # Makes the frame resizable like a window
        self.frame = frame
        self.geometry = betterroot.geometry
        self.betterroot = betterroot

        self.sensitivity = 10

        # Variables for resizing:
        self.started_resizing = False
        self.quadrant_resizing = None
        self.disable_north_west_resizing = False
        self.resizable_horizontal = True
        self.resizable_vertical = True

        self.frame.bind("<Enter>", self.change_cursor_resizing)
        self.frame.bind("<Motion>", self.change_cursor_resizing)

        self.frame.bind("<Button-1>", self.mouse_press)
        self.frame.bind("<B1-Motion>", self.mouse_motion)
        self.frame.bind("<ButtonRelease-1>", self.mouse_release)

        self.started_resizing = False

    def mouse_motion(self, event:tk.Event) -> None:
        if self.started_resizing:
            # Must be a list for `self.update_resizing_params` to change it
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

    def mouse_release(self, event):
        self.started_resizing = False

    def mouse_press(self, event:tk.Event) -> None:
        if self.betterroot.is_fullscreen or self.betterroot.is_maximised:
            return None
        # Resizing the window:
        if event.widget == self.frame:
            self.current_width = self.betterroot.root.winfo_width()
            self.current_height = self.betterroot.root.winfo_height()
            self.currentx = self.betterroot.root.winfo_rootx()
            self.currenty = self.betterroot.root.winfo_rooty()

            quadrant_resizing = self.get_quadrant_resizing()

            if len(quadrant_resizing) > 0:
                self.started_resizing = True
                self.quadrant_resizing = quadrant_resizing

    # For resizing:
    def change_cursor_resizing(self, event) -> None:
        if self.betterroot.is_fullscreen or self.betterroot.is_maximised:
            self.frame.config(cursor="arrow")
            return None
        if self.started_resizing:
            return None
        quadrant_resizing = self.get_quadrant_resizing()

        if quadrant_resizing == "":
            # Reset the cursor back to "arrow"
            self.frame.config(cursor="arrow")
        elif (quadrant_resizing == "ne") or (quadrant_resizing == "sw"):
            if IS_WINDOWS:
                # Available on Windows
                self.frame.config(cursor="size_ne_sw")
            else:
                # Available on Linux
                if quadrant_resizing == "nw":
                    self.frame.config(cursor="bottom_left_corner")
                else:
                    self.frame.config(cursor="top_right_corner")
        elif (quadrant_resizing == "nw") or (quadrant_resizing == "se"):
            if IS_WINDOWS:
                # Available on Windows
                self.frame.config(cursor="size_nw_se")
            else:
                # Available on Linux
                if quadrant_resizing == "nw":
                    self.frame.config(cursor="top_left_corner")
                else:
                    self.frame.config(cursor="bottom_right_corner")
        elif (quadrant_resizing == "n") or (quadrant_resizing == "s"):
            # Available on Windows/Linux
            self.frame.config(cursor="sb_v_double_arrow")
        elif (quadrant_resizing == "e") or (quadrant_resizing == "w"):
            # Available on Windows/Linux
            self.frame.config(cursor="sb_h_double_arrow")

    def get_quadrant_resizing(self) -> str:
        x, y = self.betterroot.root.winfo_pointerx(), self.betterroot.root.winfo_pointery()
        width, height = self.betterroot.root.winfo_width(), self.betterroot.root.winfo_height()

        x -= self.betterroot.root.winfo_rootx()
        y -= self.betterroot.root.winfo_rooty()
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

    def resize_east(self) -> (int, int, int, int):
        x = self.betterroot.root.winfo_pointerx()
        new_width = max(x-self.currentx, MIN_WIDTH)
        return new_width, None, None, None

    def resize_west(self) -> (int, int, int, int):
        x = self.betterroot.root.winfo_pointerx()
        dx = max(self.currentx-x, MIN_WIDTH-self.current_width)
        new_width = self.current_width + dx
        return new_width, None, self.currentx-dx, None

    def resize_south(self) -> (int, int, int, int):
        y = self.betterroot.root.winfo_pointery()
        new_height = max(y-self.currenty, MIN_HEIGHT)
        return None, new_height, None, None

    def resize_north(self) -> (int, int, int, int):
        y = self.betterroot.root.winfo_pointery()
        dy = max(self.currenty-y, MIN_HEIGHT-self.current_height)
        new_height = self.current_height + dy
        return None, new_height, None, self.currenty-dy

    def update_resizing_params(self, _list:list, _tuple:tuple):
        """
        Changes each element of `_list` to the corresponding on in `_tuple`
        if that element is not `None`. If it is, ignore it.
        """
        for i in range(len(_tuple)):
            element = _tuple[i]
            if element is not None:
                _list[i] = element


class DraggableWindow:
    def __init__(self, frame:tk.Frame, betterroot:BetterTk):
        # Makes the frame draggable like a window
        self.frame = frame
        self.geometry = betterroot.geometry
        self.betterroot = betterroot

        self.dragging = False
        self._offsetx = 0
        self._offsety = 0
        frame.after(100, self.set_up_bindings, betterroot)

    def set_up_bindings(self, betterroot:BetterTk) -> None:
        betterroot.bind_titlebar("<Button-1>", self.clickwin)
        betterroot.bind_titlebar("<B1-Motion>", self.dragwin)
        betterroot.bind_titlebar("<ButtonRelease-1>", self.stopdragwin)

    def stopdragwin(self, event):
        self.dragging = False

    def dragwin(self, event):
        if self.dragging:
            x = self.frame.winfo_pointerx() - self._offsetx
            y = self.frame.winfo_pointery() - self._offsety
            self.geometry("+%i+%i" % (x, y))

    def clickwin(self, event):
        if self.betterroot.is_fullscreen or self.betterroot.is_maximised:
            return None
        if not self.betterroot.check_parent_titlebar(event):
            return None
        self.dragging = True
        self._offsetx = event.widget.winfo_rootx() -\
                        self.betterroot.root.winfo_rootx() + event.x
        self._offsety = event.widget.winfo_rooty() -\
                        self.betterroot.root.winfo_rooty() + event.y


# Example 1:
if __name__ == "__main__":
    root = BetterTk()
    root.title("Example 1")
    root.geometry("400x400")
    root.allow_ctrl_w:bool = True

    root.bind_root("<KeyPress-f>", lambda event: root.toggle_fullscreen())

    # Adding a custom button:
    root.custom_buttons = {"name": "?",
                           "function": lambda: print("\"?\" was pressed"),
                           "column": 0}

    # Adding another custom button:
    root.custom_buttons = {"name": "\u2263",
                           "function": lambda: print("\"\u2263\" was pressed"),
                           "column": 2}

    # root.minimise_button.hide()
    # root.maximise_button.hide()
    # root.close_button.hide()

    root.mainloop()


# Example 2
if __name__ == "__main__a":
    settings = BetterTkSettings(theme="light")
    # use_unicode doesn't work on Linux (because of fonts?)
    settings.config(separator_colour="red", use_unicode=HAS_X11,
                    active_titlebar_bg="#00ff00",
                    inactive_titlebar_bg="#009900",
                    active_titlebar_fg="white",
                    inactive_titlebar_fg="white",
                    hightlight_colour="cyan")

    root = BetterTk(settings=settings)
    root.geometry("400x400")
    root.title("Example 2")

    # Adding a custom button:
    root.custom_buttons = {"name": "?",
                           "function": lambda: print("\"?\" was pressed"),
                           "column": 0}
    button = root.buttons[-1]
    button.config(command=lambda: print("New command set"))

    label = tk.Label(root, text="This is just to show how to change the " \
                                "window's settings.\nI know it looks bad.",
                     justify="left")
    label.pack(anchor="w")

    root.mainloop()


# Test
if __name__ == "__main__a":
    for i in range(100):
        root = BetterTk()

        frame = tk.Frame(root, bg="black", width=500, height=500)
        frame.pack(fill="both", expand=True)

        for j in range(100):
            root.update()

        assert frame.winfo_height() == frame.winfo_width() == 500
        root.destroy()

        print(f"passed {i}th test")


# Test
if __name__ == "__main__a":
    for i in range(100):
        root = BetterTk()
        root.geometry("300x400")

        frame = tk.Frame(root, bg="red", width=50, height=50)
        frame.pack(fill="both", expand=True)

        for j in range(100):
            root.update()

        assert "300x400" in root.geometry()
        root.destroy()

        print(f"passed {i}th test")