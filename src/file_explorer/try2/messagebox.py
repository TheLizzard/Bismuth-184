import tkinter as tk
import os.path

from constants.bettertk import BetterTk


filepath = os.path.dirname(__file__).replace("\\", "/") + "/"
ICON_TO_FILENAME = {"warning": filepath+"images/warning.png"}
ICON_TO_FILENAME[None] = ICON_TO_FILENAME["warning"]


class YesNoQuestion:
    def __init__(self, title:str, message:str, icon:str=None, master=None):
        if master is None:
            master = tk._default_root
        self.root = BetterTk(master)

        self.result = None

        self.root.title(title)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.destroy)
        self.root.minimise_button.hide()

        self.top_frame = tk.Frame(self.root, bd=0, highlightthickness=0,
                                  bg="black")
        self.top_frame.pack(fill="x", expand=True, pady=20)
        self.bottom_frame = tk.Frame(self.root, bd=0, highlightthickness=0,
                                  bg="black")
        self.bottom_frame.pack(fill="x", expand=True, pady=(0, 10))

        self.image = self.get_image(icon)
        self.icon = tk.Canvas(self.top_frame, bd=0, highlightthickness=0,
                              bg="black", width=self.image.width(),
                              height=self.image.height())
        self.icon.pack(side="left", padx=(15, 0))
        self.icon.create_image(0, 0, anchor="nw", image=self.image)

        self.text = tk.Label(self.top_frame, text=message, bg="black",
                             fg="white")
        self.text.pack(side="left", padx=15)

        button_kwargs = dict(fg="white", activeforeground="white", width=7,
                             bg="black", activebackground="black")

        self.yes = tk.Button(self.bottom_frame, text="Yes", **button_kwargs,
                             command=self.yes_clicked)
        self.no = tk.Button(self.bottom_frame, text="No", **button_kwargs,
                             command=self.no_clicked)

        self.no.pack(side="right", anchor="e", padx=(0, 15))
        self.yes.pack(side="right", anchor="e", padx=20)

        self.root.bind_all("<Escape>", self.no_clicked)
        self.root.bind_all("<Return>", self.yes_clicked)

        self.root.grab_set()

    def yes_clicked(self, event:tk.Event=None) -> None:
        self.result = True
        self.destroy()

    def no_clicked(self, event:tk.Event=None) -> None:
        self.result = False
        self.destroy()

    def get_image(self, icon:str) -> tk.PhotoImage:
        if icon in ICON_TO_FILENAME:
            return tk.PhotoImage(file=ICON_TO_FILENAME[icon], master=self.root)
        else:
            raise ValueError(f"Unknown icon: \"{icon}\"")

    def destroy(self) -> None:
        self.root.quit()
        self.root.destroy()

    def get(self) -> None:
        self.root.mainloop()
        return self.result


def askyesno(**kwargs) -> bool:
    question = YesNoQuestion(**kwargs)
    return question.get()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    msg = "Are you sure you want to delete \"Hi.txt\"?"
    result = askyesno(title="Delete file?", message=msg, icon="warning")
    print(result)
    root.destroy()
