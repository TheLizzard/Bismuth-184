from functools import partial
import tkinter as tk


class Notebook(tk.Frame):
    def __init__(self, master, bd=0, highlightthickness=0, fg="white",
                 bg="black", select_fg="black", select_bg="white",
                 button_activebackground="grey", plus_callback=None,
                 button_activeforeground="white", **kwargs):
        self.bg = bg
        self.fg = fg
        self.select_fg = select_fg
        self.select_bg = select_bg
        self.plus_callback = plus_callback
        self.button_activebackground = button_activebackground
        self.button_activeforeground = button_activeforeground

        super().__init__(master, bd=bd, highlightthickness=highlightthickness,
                         bg=bg, **kwargs)
        self.buttons_frame = tk.Frame(self, bd=0, bg=bg, highlightthickness=0)
        self.buttons_frame.pack(fill="x")

        self.button_frames = {} # idx: (button_frame, button)
        self.next_idx = 0
        self.caller_frames = {} # idx: frame
        self.current_tab = None

        self.add_plus_button()

        self.bind_all("<Control-Tab>", self.move_next_tab)
        self.bind_all("<Control-Shift-Tab>", self.move_prev_tab)
        self.bind_all("<Control-w>", self.__delete_current_tab)

    def delete_current_tab(self, event=None):
        try:
            self.delete_tab(self.current_tab)
        except ValueError:
            # Last tab so we can't delete it
            pass

    def _delete_current_tab(self, event=None):
        self.delete_current_tab(event)

    def __delete_current_tab(self, event=None):
        self._delete_current_tab(event)

    def next_tab(self):
        assert self.current_tab is not None, "You need at least 1 tab."
        for idx in range(self.current_tab + 1, self.next_idx):
            if idx in self.button_frames:
                return idx
        for idx in range(0, self.current_tab + 1):
            if idx in self.button_frames:
                return idx
        return "?"

    def prev_tab(self):
        assert self.current_tab is not None, "You need at least 1 tab."
        for idx in range(self.current_tab - 1, -1, -1):
            if idx in self.button_frames:
                return idx
        for idx in range(self.next_idx, self.current_tab, -1):
            if idx in self.button_frames:
                return idx
        return "?"

    def move_next_tab(self, event=None):
        next_idx = self.next_tab()
        self.__set_active(next_idx)

    def move_prev_tab(self, event=None):
        next_idx = self.prev_tab()
        self.__set_active(next_idx)

    def add_plus_button(self):
        button_frame = tk.Frame(self.buttons_frame, bd=0, highlightthickness=1,
                                highlightbackground="grey")
        button = tk.Button(button_frame, bg=self.bg, fg=self.fg, text="+",
                           relief="flat", command=self.__plus_pressed,
                           activebackground=self.button_activebackground,
                           activeforeground=self.button_activeforeground,
                           takefocus=False)
        button.pack(side="right")
        button_frame.grid(row=1, column=101)

    def add(self, frame, text="Untitled"):
        idx = self.next_idx
        self.event_generate("<<NewTabAdded>>", when="tail")
        self.caller_frames.update({idx: frame})

        button_frame = tk.Frame(self.buttons_frame, bd=0, highlightthickness=1,
                                highlightbackground="grey")
        button = tk.Button(button_frame, bg=self.bg, fg=self.fg, text=text,
                           relief="flat", command=partial(self.__set_active,
                                                          idx),
                           activebackground=self.button_activebackground,
                           activeforeground=self.button_activeforeground,
                           takefocus=False)
        button.pack(side="right")
        button.bind("<Button-2>", partial(self.__delete_tab, idx))
        button_frame.grid(row=1, column=self.next_idx + 1)
        self.button_frames.update({idx: (button_frame, button)})

        if self.current_tab == None:
            self.__set_active(idx)
        self.next_idx += 1
        return idx

    def rename(self, idx, text):
        self.button_frames[idx][1].config(text=text)

    def plus_pressed(self):
        if self.plus_callback is not None:
            self.plus_callback()

    def _plus_pressed(self):
        self.plus_pressed()

    def __plus_pressed(self):
        self._plus_pressed()

    def delete_tab(self, idx, event=None):
        self.event_generate("<<TabDeleted>>", when="tail")
        if len(self.button_frames) == 1:
            raise ValueError("Can't remove the last tab.")
        if self.current_tab == idx:
            self.move_prev_tab()
        button_frame, button = self.button_frames[idx]
        button_frame.destroy()
        del self.button_frames[idx]
        del self.caller_frames[idx]

    def _delete_tab(self, idx, event=None):
        self.delete_tab(idx, event)

    def __delete_tab(self, idx, event=None):
        self._delete_tab(idx, event)

    def set_active(self, idx):
        self.event_generate("<<TabSetActive>>", when="tail")
        # Reset the old active tab's button's bg
        if self.current_tab is not None:
            self.button_frames[self.current_tab][1].config(bg=self.bg,
                                                           fg=self.fg)
            frame = self.caller_frames[self.current_tab].pack_forget()

        self.current_tab = idx
        frame = self.caller_frames[idx]
        frame.pack(fill="both", expand=True)
        button_frame, button = self.button_frames[idx]
        button.config(bg=self.select_bg, fg=self.select_fg)

    def _set_active(self, idx):
        self.set_active(idx)

    def __set_active(self, idx):
        self._set_active(idx)


if __name__ == "__main__":
    def delete_tab(idx, event=None):
        print("Deleting tab")
        notebook.delete_tab(idx, event)

    def set_active(idx):
        print("Setting a tab as active")
        notebook.set_active(idx)

    def plus_pressed():
        print("Plus pressed")
        notebook.plus_pressed()
        notebook._set_active(notebook.next_idx - 1)

    def new_tab():
        global idx
        text = "%s Label %i %s" % ("-"*50, idx, "-"*50)
        frame = tk.Label(notebook, bg="black", fg="white", text=text)
        notebook.add(frame, text="Tab %i" % idx)
        idx += 1

    root = tk.Tk()
    notebook = Notebook(root, plus_callback=new_tab)
    notebook.pack(fill="both", expand=True)

    notebook._delete_tab = delete_tab
    notebook._set_active = set_active
    notebook._plus_pressed = plus_pressed

    idx = 1

    new_tab()
    new_tab()
