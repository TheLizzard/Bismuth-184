from threading import Thread, Lock
from time import sleep
import tkinter as tk
import subprocess
import sys
import os

from constants.bettertk import BetterTk
from basiceditor.text import ScrolledText, KEY_REPLACE_DICT
from constants.settings import settings


FONT = settings.terminal.font
HEIGHT = settings.terminal.height
WIDTH = settings.terminal.width
BG_COLOUR = settings.terminal.bg
FG_COLOUR = settings.terminal.fg
TITLEBAR_COLOUR = settings.terminal.titlebar_colour
TITLEBAR_SIZE = settings.terminal.titlebar_size


KILL_PROCESS = "taskkill /f /pid %i /t"


def add_padding_to_text(text):
    text = " %s " % text
    length = len(text)
    p1 = "="*int((WIDTH-length)/2+0.5)
    p2 = "="*int((WIDTH-length)/2)
    return p1 + text + p2


class FinishedProcess:
    def __init__(self):
        self.returncode = 0
        self.pid = None

    def poll(self):
        return "Process already finished"

    def terminate(self):
        pass

    def kill(self):
        pass


class FileDestriptor:
    def __init__(self, file_descriptor):
        self.fd = file_descriptor

    def __repr__(self):
        return f"FileDestriptor({self.fd})"

    def fileno(self):
        return self.fd

    def write(self, text, add_padding=False, end="\n"):
        if isinstance(text, str):
            text = text.encode()
        if add_padding:
            text = add_padding_to_text(text)
        os.write(self.fd, text+end.encode())

    def read(self, number_characters):
        return os.read(self.fd, number_characters)


class FileDestriptors:
    def __init__(self):
        # All of them are in the format (read_ptr, write_ptr)
        self.stdin = self.create_pipe()
        self.stdout = self.create_pipe()
        self.stderr = self.create_pipe()

    def __del__(self):
        for file in self.stdin+self.stdout+self.stderr:
            os.close(file)

    def get_child(self):
        # Get the file destriptors for the child process
        return {"stdin": self.stdin[0], "stdout": self.stdout[1],
                "stderr": self.stderr[1]}

    def get_parent(self):
        return {"stdin": self.stdin[1], "stdout": self.stdout[0],
                "stderr": self.stderr[0]}

    def create_pipe(self):
        # Returns (read_ptr, write_ptr)
        r_ptr, w_ptr = os.pipe()
        return FileDestriptor(r_ptr), FileDestriptor(w_ptr)


class Terminal:
    def __init__(self):
        self.process = FinishedProcess()
        self.file_ptrs = FileDestriptors()

    def run(self, command, callback=None):
        self.stop_process()
        file_ptrs = self.file_ptrs.get_child()
        self.process = subprocess.Popen(command, close_fds=False, shell=True,
                                        **file_ptrs)
        # Wait for the proccess to end
        while self.process.poll() is None:
            if callback is not None:
                callback()
            sleep(0.02)
        exit_code = self.process.returncode
        return exit_code

    def stop_process(self):
        if self.process is not None:
            if self.process.pid is not None:
                subprocess.Popen(KILL_PROCESS%self.process.pid, shell=True)
            self.process = FinishedProcess()

    def stdout_write(self, text, **kwargs):
        self.file_ptrs.stdout[1].write(text, **kwargs)

    def stderr_write(self, text, **kwargs):
        self.file_ptrs.stderr[1].write(text, **kwargs)


class Buffer:
    def __init__(self):
        self.lock = Lock()
        with self.lock:
            self.data = ""

    def write(self, data, add_padding=False):
        if add_padding:
            data = add_padding_to_text(data)+"\n"
        with self.lock:
            self.data += data

    def read_all(self):
        with self.lock:
            data = self.data
            self.data = ""
        return data

    def reset(self):
        with self.lock:
            self.data = ""


class TkTerminal(Terminal):
    def __init__(self):
        super().__init__()
        self.ptrs = self.file_ptrs.get_parent()
        self.closed = False
        self.should_clear_screen = False

        self.tk_stdout = Buffer()
        self.tk_stderr = Buffer()

        self.tk_thread = Thread(target=self.tk_init, daemon=True)
        self.tk_thread.start()

        Thread(target=self.tk_stdout_read, daemon=True).start()
        Thread(target=self.tk_stderr_read, daemon=True).start()

    def tk_init(self):
        self.root = BetterTk(titlebar_bg=BG_COLOUR, titlebar_fg=TITLEBAR_COLOUR,
                             titlebar_sep_colour=FG_COLOUR,
                             titlebar_size=TITLEBAR_SIZE)
        self.root.buttons["X"].config(command=self.tk_close)
        self.text = ScrolledText(self.root, bg=BG_COLOUR, fg=FG_COLOUR,
                                 font=FONT, height=HEIGHT, width=WIDTH,
                                 undo=False)
        self.text.pack(fill="both", expand=True)
        self.text.tag_config("error", foreground="red")
        self.text.bind("<Return>", self.tk_send_input)
        self.text.bind("<Key>", self.tk_check_read_ony)
        self.text.focus()

        self.tk_mainloop()
        self.root.mainloop()

    def tk_check_read_ony(self, event):
        disallow_write = "readonly" in self.text.tag_names("insert")
        disallow_backspace = "readonly" in self.text.tag_names("insert-1c")

        char = event.char
        state = self.text.get_state(event)
        if "Control" in state:
            return None

        # If the key isn't printable make it a word like:
        #     "Left"/"Right"/"BackSpace"
        if (not char.isprintable()) or (char == ""):
            char = event.keysym

        # Replace all of the words that can be expressed with 1 character
        if char in KEY_REPLACE_DICT:
            char = KEY_REPLACE_DICT[char]

        if disallow_write:
            if (len(char) == 1) or (char == "Tab") or (char == "Delete"):
                return "break"
        if disallow_backspace and (char == "BackSpace"):
            return "break"
        if self.text.tag_ranges("sel"):
            tags = self.text.tag_names("sel.first")
            if "readonly" in tags:
                return "break"

    def tk_mainloop(self):
        if self.should_clear_screen:
            self.text.delete("0.0", "end")
            self.should_clear_screen = False
        else:
            text = self.tk_stderr.read_all()
            if len(text) > 0:
                insert = self.text.index("insert")
                self.text.insert("end", text)
                self.text.tag_add("readonly", insert, "insert")
                self.text.tag_add("error", insert, "insert")

            text = self.tk_stdout.read_all()
            if len(text) > 0:
                insert = self.text.index("insert")
                self.text.insert("end", text)
                self.text.tag_add("readonly", insert, "insert")

        self.root.after(100, self.tk_mainloop)

    def tk_send_input(self, event):
        # Get the text and ranges
        text = self.text.get("0.0", "end")
        ranges = self.text.tag_ranges("readonly")
        for i in range(0, len(ranges), 2):
            start, end = str(ranges[i]), str(ranges[i+1])
            # For each range: remove it from text
            sub_text = self.text.get(start, end)
            try:
                idx = text.index(sub_text)
                text = text[:idx] + text[idx+len(sub_text):]
            except ValueError:
                pass
        self.ptrs["stdin"].write(text.lstrip("\n").encode())
        self.text.mark_set("insert", "end")
        self.text.tag_add("readonly", "0.0", "end-1c")
        self.text.insert("insert", "\n")
        return "break"

    def tk_stdout_read(self):
        while not self.closed:
            data = self.ptrs["stdout"].read(1).decode()
            self.tk_stdout.write(data)

    def tk_stderr_read(self):
        while not self.closed:
            self.tk_stderr.write(self.ptrs["stderr"].read(1).decode())

    def tk_close(self):
        self.closed = True
        super().stop_process()
        self.root.close()

    def stdout_write(self, text, **kwargs):
        self.tk_stdout.write(text, **kwargs)

    def stderr_write(self, text, **kwargs):
        self.tk_stdout.write(text, **kwargs)

    def run(self, command, callback=None):
        if self.closed:
            return Exception("Terminal closed by user")
        return super().run(command, callback=callback)

    def clear(self):
        if self.closed:
            return Exception("Terminal closed by user")
        self.should_clear_screen = True
        while self.should_clear_screen:
            sleep(0.3)


if __name__ == "__main__":
    terminal = TkTerminal()
    terminal.run("exe.exe")
