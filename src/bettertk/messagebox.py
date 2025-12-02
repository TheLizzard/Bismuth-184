from __future__ import annotations
from PIL import ImageTk
import tkinter as tk

try:
    from . import BetterTk, make_scrolled
    from .terminaltk.sprites.creator import SpriteCache, SPRITES_REMAPPING
except ImportError:
    from __init__ import BetterTk, make_scrolled
    from terminaltk.sprites.creator import SpriteCache, SPRITES_REMAPPING


FRAME_KWARGS = dict(bd=0, highlightthickness=0, bg="black")
BUTTON_KWARGS = dict(activeforeground="white", activebackground="black",
                     fg="white", bg="black", takefocus=True)

ICONS:SpriteCache = SpriteCache(size=64, compute_size=256)


def tk_center_window(r:tk.Tk) -> None:
    r.update_idletasks()
    r.geometry(f"+{(r.winfo_screenwidth()-r.winfo_width()) // 2}" + \
               f"+{(r.winfo_screenheight()-r.winfo_height()) // 2}")


class Popup(BetterTk):
    __slots__ = "root", "image", "tk_image", "block"

    def __init__(self, master:tk.Misc|None, title:str, *, icon:str,
                 center:bool=True, center_widget:tk.Misc=None,
                 block:bool=True, iconphoto_default:bool=False) -> Popup:
        if center_widget is not None:
            assert center, "No point in passing in center_widget if " \
                           "center is False"
        self.block:bool = block
        if master is None:
            super().__init__(className=str(icon))
        else:
            super().__init__(master)
        super().title(title)
        self.minimise_button.hide()
        super().resizable(False, False)
        super().protocol("WM_DELETE_WINDOW", self._destroy)
        super().topmost(True)
        super().topmost(False)
        self.image:Image.Image = self.get_image(icon)
        self.tk_image = ImageTk.PhotoImage(self.image, master=self)
        self.root.iconphoto(iconphoto_default, self.tk_image)
        super().bind("<Escape>", lambda e: self._destroy())
        super().focus_set()
        try:
            super().grab_set()
        except tk.TclError:
            pass
        if center:
            base_widget:tk.Misc = center_widget or \
                                  self.get_root(master) or \
                                  self
            # Use `after_idle(···)` instead of `after(1, ···)`???
            super().after(1, self.center, base_widget)

    def get_image(self, icon_name:str) -> Image.Image:
        return ICONS[SPRITES_REMAPPING.get(icon_name,icon_name)]

    def _destroy(self) -> None:
        if self.block:
            super().quit()
        super().destroy()

    def mainloop(self) -> YesNoQuestion:
        super().mainloop()
        return self

    def center(self, based_on:tk.Misc) -> None:
        if based_on == self:
            tk_center_window(self)
        else:
            super().update_idletasks()
            x:int = based_on.winfo_rootx() + based_on.winfo_width()//2
            y:int = based_on.winfo_rooty() + based_on.winfo_height()//2
            x -= super().winfo_width()//2
            y -= super().winfo_height()//2
            super().geometry(f"+{x}+{y}")

    def get_root(self, widget:tk.Misc|None) -> tk.Tk|tk.Toplevel|BetterTk:
        if widget is None: return None
        while True:
            if isinstance(widget, tk.Tk|tk.Toplevel|BetterTk):
                return widget
            assert widget is not None, "InternalError"
            assert isinstance(widget, tk.Misc), "InternalError"
            widget:tk.Misc = widget.master


class Tell(Popup):
    __slots__ = ()

    def __init__(self, master:tk.Misc|None, *, title:str, message:str, icon:str,
                 center:bool=True, center_widget:tk.Misc=None, block:bool=True,
                 multiline:bool=False, iconphoto_default:bool=False) -> Tell:
        super().__init__(master, title=title, icon=icon, center=center,
                         center_widget=center_widget, block=block,
                         iconphoto_default=iconphoto_default)

        left_frame = tk.Frame(self, **FRAME_KWARGS)
        left_frame.pack(side="left", fill="y", expand=True)
        right_frame = tk.Frame(self, **FRAME_KWARGS)
        right_frame.pack(side="right", fill="y", expand=True)

        width, height = self.image.size
        icon = tk.Canvas(left_frame, **FRAME_KWARGS, width=width, height=height)
        icon.pack(side="left", padx=(15, 0))
        icon.create_image(0, 0, anchor="nw", image=self.tk_image)

        if multiline:
            text_frame:tk.Frame = tk.Frame(right_frame, bg="black", bd=0,
                                           highlightthickness=0)
            text_frame.pack(side="top", padx=15, pady=(15, 20))
            text = tk.Text(text_frame, font=("mono",10), bg="black", fg="white",
                           width=80, height=20, wrap="none", takefocus=False)
            text.insert("end", message)
            text.config(state="disabled")
            make_scrolled(text_frame, text, vscroll=True, hscroll=False)
            def select_all(_:tk.Event) -> str:
                text.tag_add("sel", "1.0", "end")
                return "break"
            text.bind("<Control-a>", select_all)
        else:
            text = tk.Label(right_frame, text=message, bg="black", fg="white")
            text.pack(side="top", padx=15, pady=(15, 20))

        ok = tk.Button(right_frame, text="Ok", **BUTTON_KWARGS, width=10,
                       command=self._destroy)
        ok.pack(side="bottom", anchor="e", padx=(0, 15), pady=(0, 20))
        ok.focus_set()

        for widget in (self, ok):
            for event in ("<Return>", "<KP_Enter>", "<Escape>"):
                widget.bind(event, lambda e: self._destroy())


class MultipleChoiceQuestion(Popup):
    """
    A multiple choice popup. The `options`, `title`, `message` and `icon` must
      be provided. If `default` isn't provided, `option[0]` is used.
    If the user presses the enter/space key, the default is returned.
    If the user presses escape/closes the popup, `None` is returned.
    """

    __slots__ = "result"

    def __init__(self, master:tk.Misc|None, *, title:str, message:str, icon:str,
                 center_widget:tk.Misc=None, iconphoto_default:bool=False,
                 center:bool=True, options:list[str],
                 default:str=None) -> MultipleChoiceQuestion:
        if default is None:
            default:str = options[0]
        assert isinstance(default, str), "TypeError"
        assert default in options, "ValueError"
        self.result:str = None
        super().__init__(master, title=title, icon=icon, center=center,
                         center_widget=center_widget, block=True,
                         iconphoto_default=iconphoto_default)

        right_frame = tk.Frame(self, **FRAME_KWARGS)
        right_frame.pack(side="right", fill="both", expand=True)

        b_frame = tk.Frame(right_frame, **FRAME_KWARGS)
        b_frame.pack(side="bottom", anchor="e", expand=True, padx=10, pady=15)

        width, height = self.image.size
        icon = tk.Canvas(self, **FRAME_KWARGS, width=width, height=height)
        icon.pack(side="left", padx=(15, 0))
        icon.create_image(0, 0, anchor="nw", image=self.tk_image)

        text = tk.Label(right_frame, text=message, bg="black", fg="white")
        text.pack(side="top", padx=15, pady=(15,0))

        max_option_width:int = max(map(len, options))
        for option in options:
            cmd = lambda *e, opt=option: self.selected(opt)
            but = tk.Button(b_frame, text=option, **BUTTON_KWARGS, command=cmd,
                            width=max_option_width)
            but.pack(side="left", anchor="e", padx=5)
            for event in ("<Return>", "<KP_Enter>", "<Escape>"):
                but.bind(event, cmd)

        cmd = lambda *e: self.selected(default)
        for event in ("<Return>", "<KP_Enter>", "<space>"):
            self.bind(event, cmd)
        self.bind("<Escape>", lambda e: self._destroy())

        super().mainloop()

    def selected(self, option:str) -> None:
        self.result:str = option
        self._destroy()

    def get(self) -> str:
        return self.result


class YesNoQuestion(MultipleChoiceQuestion):
    __slots__ = "result"

    def __init__(self, master:tk.Misc=None, **kwargs:dict) -> YesNoQuestion:
        super().__init__(master, **kwargs, options=["yes","no"])

    def get(self) -> bool:
        return super().get() == "yes"


def askyesno(master:tk.Misc|None=None, **kwargs:dict) -> bool|None:
    return YesNoQuestion(master, **kwargs).get()

def askmulti(master:tk.Misc|None=None, **kwargs:dict) -> bool|None:
    return MultipleChoiceQuestion(master, **kwargs).get()

def tell(master:tk.Misc|None=None, block:bool=True, **kwargs) -> None:
    tell:Tell = Tell(master, block=block, **kwargs)
    if block:
        tell.mainloop()

def debug(text:str, block:bool=True, **kwargs:dict) -> None:
    tell(title="Debug", message=text, icon="info", block=block, **kwargs)


if __name__ == "__main__a":
    # TeXInfo apparently uses className="info" for something...
    tcl = tk._tkinter.create(None, "messagebox", "info", False, 1, True,
                             False, None)


if __name__ == "__main__":
    def tksleep(time:int) -> None:
        root.after(time*1000, root.quit)
        root.mainloop()

    root:tk.Misc|None = None
    # root = tk.Tk()
    # root.geometry("+170+50")

    msg:str = 'Are you sure you want to delete "Hi.txt"?'
    result = askyesno(root, title="Delete file?", message=msg, icon="warning",
                      center=True)
    print(result)

    if result:
        msg:str = 'You deleted "Hi.txt"?'
        tell(root, title="Deleted file", message=msg, icon="info", center=True)
