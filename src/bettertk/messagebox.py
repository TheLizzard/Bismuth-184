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
BUTTON_KWARGS = dict(fg="white", bg="black", activeforeground="white",
                     activebackground="black")

ICONS:SpriteCache = SpriteCache(size=64, compute_size=256)


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
            center:bool = False
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
            base_widget:tk.Misc = center_widget or self.get_root(master)
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
        super().update_idletasks()
        x:int = based_on.winfo_rootx() + based_on.winfo_width()//2
        y:int = based_on.winfo_rooty() + based_on.winfo_height()//2
        x -= super().winfo_width()//2
        y -= super().winfo_height()//2
        super().geometry(f"+{x}+{y}")

    def get_root(self, widget:tk.Misc) -> tk.Tk|tk.Toplevel:
        while True:
            if isinstance(widget, tk.Tk|tk.Toplevel|BetterTk):
                return widget
            assert widget is not None, "InternalError"
            assert isinstance(widget, tk.Misc), "InternalError"
            widget:tk.Misc = widget.master


class Tell(Popup):
    __slots__ = ()

    def __init__(self, master:tk.Misc|None, title:str, message:str, *, icon:str,
                 center:bool=True, center_widget:tk.Misc=None, block:bool=True,
                 multiline:bool=False, iconphoto_default:bool=False) -> Tell:
        super().__init__(master, title=title, icon=icon, center=center,
                         center_widget=center_widget, block=block,
                         iconphoto_default=iconphoto_default)
        super().bind("<Return>", lambda e: self._destroy())

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
                           width=80, height=20, wrap="none")
            text.insert("end", message)
            text.config(state="disabled")
            make_scrolled(text_frame, text, vscroll=True, hscroll=False)
            text.focus_set()
            def select_all(_:tk.Event) -> str:
                text.tag_add("sel", "1.0", "end")
                return "break"
            text.bind("<Control-a>", select_all)
        else:
            text = tk.Label(right_frame, text=message, bg="black", fg="white")
            text.pack(side="top", padx=15, pady=(15, 20))

        ok = tk.Button(right_frame, text="Ok", **BUTTON_KWARGS,
                       width=10, command=self._destroy)
        ok.pack(side="bottom", anchor="e", padx=(0, 15), pady=(0, 20))


class YesNoQuestion(Popup):
    __slots__ = "result"

    def __init__(self, master:tk.Misc|None, title:str, message:str, *, icon:str,
                 center:bool=True, center_widget:tk.Misc=None,
                 iconphoto_default:bool=False) -> YesNoQuestion:
        self.result:bool = None
        super().__init__(master, title=title, icon=icon, center=center,
                         center_widget=center_widget, block=True,
                         iconphoto_default=iconphoto_default)
        super().bind("<Return>", lambda e: self.yes_clicked())

        right_frame = tk.Frame(self, **FRAME_KWARGS)
        right_frame.pack(side="right", fill="both", expand=True)

        b_frame = tk.Frame(right_frame, **FRAME_KWARGS)
        b_frame.pack(side="bottom", anchor="e", expand=True)

        width, height = self.image.size
        icon = tk.Canvas(self, **FRAME_KWARGS, width=width, height=height)
        icon.pack(side="left", padx=(15, 0))
        icon.create_image(0, 0, anchor="nw", image=self.tk_image)

        text = tk.Label(right_frame, text=message, bg="black", fg="white")
        text.pack(side="top", padx=15, pady=15)

        yes = tk.Button(b_frame, text="Yes", **BUTTON_KWARGS,
                        width=7, command=self.yes_clicked)
        no = tk.Button(b_frame, text="No", **BUTTON_KWARGS,
                       width=7, command=self.no_clicked)
        yes.pack(side="left", anchor="e", padx=5, pady=(5, 20))
        no.pack(side="left", anchor="e", padx=15, pady=(5, 20))

        super().mainloop()

    def yes_clicked(self) -> None:
        self.result:bool = True
        self._destroy()

    def no_clicked(self) -> None:
        self.result:bool = False
        self._destroy()

    def get(self) -> None:
        return self.result


def askyesno(master:tk.Misc|None=None, *args:tuple, **kwargs:dict) -> bool|None:
    return YesNoQuestion(master, *args, **kwargs).get()

def tell(master:tk.Misc|None=None, *args, block:bool=True, **kwargs) -> None:
    tell:Tell = Tell(master, *args, block=block, **kwargs)
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

    root = tk.Tk()
    root.geometry("+170+50")
    #root.withdraw()

    msg:str = 'Are you sure you want to delete "Hi.txt"?'
    result = askyesno(root, title="Delete file?", message=msg, icon="warning")
    print(result)

    if result:
        msg:str = 'You deleted "Hi.txt"?'
        result = tell(root, title="Deleted file", message=msg, icon="info")
        print(result)