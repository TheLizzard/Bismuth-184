from __future__ import annotations
from PIL import Image, ImageTk, UnidentifiedImageError
from mimetypes import guess_type, guess_extension
from collections import defaultdict
from glob import glob
import tkinter as tk
from os import path

SELF_DIR:str = path.dirname(__file__)
UNKNOWN_MIMETYPE:str = "application-x-zerosize"
SYMLINK_FOLLOWS:int = 16 # max levels of symlink to follow (can be 0)


ICON_PATHS:list[str] = [
             "/usr/share/icons/Yaru/16x16/mimetypes",
             "/usr/share/icons/*/16x16/mimetypes",
             # path.expanduser("~/.icons"), # don't know how they are sorted
             path.expanduser("~/.local/share/icons/*/*/mimetypes"),
             path.join(SELF_DIR, "KDE-oxygen-icons", "16x16", "mimetypes"),
             path.join(SELF_DIR, "sprites"),
                       ]

WIDTH:int = 16
HEIGHT:int = 16
MimeType:type = str


_ICON_PATHS:list[str] = []
for icon_path in ICON_PATHS:
    _ICON_PATHS.extend(sorted(glob(icon_path)))


# https://mimetype.io/all-types
# TODO: Parse and use: /usr/share/mime/generic-icons


_MIMETYPE_CACHE:dict[MimeType:str] = {}
def _spritepath_from_mimetype(mimetype:MimeType) -> str:
    imagename:str = mimetype.replace("/", "-") + ".png"
    if mimetype not in _MIMETYPE_CACHE:
        for imagepath in _ICON_PATHS:
            spritepath:str = path.join(imagepath, imagename)
            if not path.exists(spritepath): continue
            _MIMETYPE_CACHE[mimetype] = spritepath
            break
        else:
            _MIMETYPE_CACHE[mimetype] = _BLANK_SPRITEPATH
    return _MIMETYPE_CACHE[mimetype]
_BLANK_SPRITEPATH:str = _spritepath_from_mimetype(UNKNOWN_MIMETYPE)


def mimetype_from_shebang(shebang:str) -> MimeType:
    if "perl" in shebang:
        return "application/x-perl"
    if ("python" in shebang) or ("pypy" in shebang):
        return "text/x-python"
    if "sh" in shebang:
        return "application/x-shellscript"

_CACHE:dict[tk.Misc:dict[MimeType:ImageTk.PhotoImage]] = defaultdict(dict)
def get_sprite(master:tk.Misc, filepath:str) -> ImageTk.PhotoImage:
    cache:dict[str:ImageTk.PhotoImage] = _CACHE[master]
    # Get mimetype
    mimetype, _ = guess_type(filepath)
    # If no mimetype, try looking at the shebang
    if mimetype is None:
        try:
            with open(filepath, "r") as file:
                if file.read(2) == "#!":
                    shebang:str = file.readline()
                    mimetype:MimeType = mimetype_from_shebang(shebang)
        except (UnicodeDecodeError, OSError):
            pass
    # Handle known mimetype
    mimetype:MimeType = mimetype or UNKNOWN_MIMETYPE
    # If in cache
    if mimetype in cache: return cache[mimetype]
    # Get spritepath
    spritepath:str = _spritepath_from_mimetype(mimetype)
    # Check if spritepath is a symlink that the filesystem refuses to resolve
    for _ in range(SYMLINK_FOLLOWS):
        with open(spritepath, "rb") as file:
            # Check if it starts with magic value
            if file.read(len(b"IntxLNK\x01")) != b"IntxLNK\x01":
                break
            # Decode the rest as UTF-16
            try:
                newpath:str = file.read().decode("utf-16")
            except UnicodeDecodeError:
                break
            spritepath:str = path.join(path.dirname(spritepath), newpath)
    else:
        if SYMLINK_FOLLOWS:
            raise RuntimeError("Symbolic links too deep to resolve")
    # Convert to tkinter image
    img:Image.Image = Image.open(spritepath) \
                           .resize((WIDTH,HEIGHT), Image.LANCZOS)
    tkimg:ImageTk.PhotoImage = ImageTk.PhotoImage(img, master=master)
    cache[mimetype] = tkimg
    return cache[mimetype]


if __name__ == "__main__":
    class MovableTk(tk.Tk):
        def __init__(self):
            super().__init__()
            super().overrideredirect(True)

            # Moving the window
            super().bind("<ButtonPress-1>", self.start_move)
            super().bind("<ButtonRelease-1>", self.stop_move)
            super().bind("<Motion>", self.do_move)
            self.last_x = self.last_y = None

            # Resizing the window
            super().bind("<Button-4>", self.resize_plus)
            super().bind("<Button-5>", self.resize_minus)

            # Exit the window
            super().bind("<Control-w>", self.exit)

            self.moved = False

        def exit(self, event:tk.Event=None) -> None:
            self.destroy()

        def resize_plus(self, event:tk.Event) -> str:
            if self._fullscreen:
                return None
            width, height = super().winfo_width(), super().winfo_height()
            new_width = width + 10
            if new_width >= super().winfo_screen_width():
                new_width = super().winfo_screen_width()
                new_height = super().winfo_screen_height()
            else:
                new_height = int(height/width*new_width + 0.5)
            super().geometry(f"{new_width}x{new_height}")

        def resize_minus(self, event:tk.Event) -> str:
            if self._fullscreen:
                return None
            width, height = super().winfo_width(), super().winfo_height()
            new_width = width - 10
            if new_width < 300:
                new_width = 300
            new_height = int(height/width*new_width + 0.5)
            super().geometry(f"{new_width}x{new_height}")

        def start_move(self, event:tk.Event) -> str:
            self.moved = False
            self.last_x = event.x
            self.last_y = event.y
            return "break"

        def stop_move(self, event) -> str:
            self.last_x = self.last_y = None
            if self.moved:
                return "break"

        def do_move(self, event:tk.Event) -> str:
            if self.last_x is not None:
                self.moved = True
                x = super().winfo_rootx() + event.x - self.last_x
                y = super().winfo_rooty() + event.y - self.last_y
                super().geometry(f"+{x}+{y}")
                return "break"


    root = MovableTk()

    canvas = tk.Canvas(root, width=100, height=500, bg="black")
    canvas.pack()

    y = HEIGHT
    for ext in ("blank", "py", "txt", "cpp", "hpp", "rar", "json"):
        tk_img = get_sprite(root, "file." + ext)
        canvas.create_image(20, y, image=tk_img)
        y += int(HEIGHT*2)

    root.mainloop()