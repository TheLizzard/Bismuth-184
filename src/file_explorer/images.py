from PIL import Image, ImageTk
import tkinter as tk
import os.path


def init(root:tk.Tk) -> None:
    global TK_IMAGES
    TK_IMAGES = {}
    for extension in EXTENSIONS:
        path = os.path.join(base_folder, f"sprites/.{extension}.png")
        img:Image.Image = Image.open(path)
        img:Image.Image = img.resize((WIDTH,HEIGHT), Image.LANCZOS)
        tk_image = ImageTk.PhotoImage(img, master=root)
        TK_IMAGES[extension] = tk_image
    TK_IMAGES["*"] = TK_IMAGES["star"]


EXTENSIONS = ("py", "txt", "cpp", "folder", "rar", "star")
base_folder:str = os.path.dirname(__file__)
WIDTH:int = 16
HEIGHT:int = 16


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

    init(root)

    canvas = tk.Canvas(root, width=100, height=500, bg="black")
    canvas.pack()

    y = HEIGHT
    for extension, tk_img in TK_IMAGES.items():
        canvas.create_image(20, y, image=tk_img)
        y += int(HEIGHT*2)

    root.mainloop()
