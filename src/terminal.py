from threading import Thread, Lock
from time import sleep
import subprocess
import sys
import os

from basiceditor.text import ScrolledText, KEY_REPLACE_DICT
from constants.settings import settings
from constants.tag_negator import Range
from constants.bettertk import BetterTk


FONT = settings.terminal.font.get()
HEIGHT = settings.terminal.height.get()
WIDTH = settings.terminal.width.get()
BG_COLOUR = settings.terminal.bg.get()
FG_COLOUR = settings.terminal.fg.get()
TITLEBAR_COLOUR = settings.terminal.titlebar_colour.get()
TITLEBAR_SIZE = settings.terminal.titlebar_size.get()

WAIT_NEXT_LOOP = settings.terminal.wait_next_loop_ms.get()
WAIT_STDIN_READ = settings.terminal.wait_stdin_read_ms.get()

KILL_PROCESS = "taskkill /f /pid %i /t"


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

    def write(self, text):
        if isinstance(text, str):
            text = text.encode()
        os.write(self.fd, text)

    def read(self, number_characters):
        data = os.read(self.fd, number_characters)
        return data


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
    def __init__(self, callback=None):
        self.process = FinishedProcess()
        self.file_ptrs = FileDestriptors()
        self.callback = callback

    def __del__(self):
        sleep(0.1)
        self.stop_process()

    def run(self, command):
        self.stop_process()
        file_ptrs = self.file_ptrs.get_child()
        self.process = subprocess.Popen(command, close_fds=False, shell=True,
                                        **file_ptrs)
        # Wait for the proccess to end
        while self.process.poll() is None:
            if self.callback is not None:
                self.callback()
            else:
                sleep(0.02)
        exit_code = self.process.returncode
        self.process = FinishedProcess() # Make sure we clean up
        return exit_code

    def stop_process(self):
        if self.process is not None:
            if not isinstance(self.process, FinishedProcess):
                subprocess.Popen(KILL_PROCESS%self.process.pid, shell=True)
                self.process = FinishedProcess()

    def stdout_write(self, text, add_padding=False, end="\n"):
        if add_padding:
            text = self.add_padding(text)
        self.file_ptrs.stdout[1].write(text+end)

    def stderr_write(self, text, add_padding=False, end="\n"):
        if add_padding:
            text = self.add_padding(text)
        self.file_ptrs.stderr[1].write(text+end)

    def forever_cmd(self):
        self.forver_cmd_running = True
        while self.forver_cmd_running:
            msg = "Running cmd.exe"
            self.stdout_write(msg, add_padding=True)
            error = self.run("cmd.exe")
            msg = "Process exit code: %s" % str(error)
            self.stdout_write(msg, add_padding=True)

    @staticmethod
    def add_padding(text):
        #return text
        text = " %s " % text
        length = len(text)
        p1 = "="*int((WIDTH-length)/2+0.5)
        p2 = "="*int((WIDTH-length)/2)
        return p1 + text + p2


class Buffer:
    def __init__(self):
        self.lock = Lock()
        self.reset()

    def write(self, data):
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


class STDINHandle:
    def __init__(self, read_handle, write_handle):
        self.handled_write = False
        self.working = Lock()
        self.write_handle = write_handle
        self.read_handle = read_handle

    def check_child_reading(self):
        with self.working:
            self.handled_write = True
            self.write_handle.write("\r")
            thread = Thread(target=self.try_read)
            thread.start()
            sleep(WAIT_STDIN_READ/1000)
            if self.handled_write:
                self.write_handle.write("\r"*10)
                return True
            return False

    def try_read(self):
        data = self.read_handle.read(1)
        self.handled_write = False

    def write(self, text):
        self.write_handle.write(text)


# ping 127.0.0.1 -n 16 > nul


class TkTerminal(Terminal):
    def __init__(self, callback=None):
        super().__init__(callback=callback)
        self.ptrs = self.file_ptrs.get_parent()
        self.improved_stdin_handle = STDINHandle(*self.file_ptrs.stdin)
        self.closed = False
        self.stdin_working = Lock()
        self.should_clear_screen = False
        self.set_up = False

        self.tk_stdout = Buffer()
        self.tk_stderr = Buffer()

        Thread(target=self.tk_init, daemon=True).start()

        Thread(target=self.tk_stdout_read, daemon=True).start()
        Thread(target=self.tk_stderr_read, daemon=True).start()

        while not self.set_up:
            sleep(0.1)
        del self.set_up

    def tk_init(self):
        self.root = BetterTk(titlebar_bg=BG_COLOUR, titlebar_fg=TITLEBAR_COLOUR,
                             titlebar_sep_colour=FG_COLOUR,
                             titlebar_size=TITLEBAR_SIZE)
        self.root.title("Terminal")
        self.root.buttons["X"].config(command=self.tk_close)

        self.text = ScrolledText(self.root, bg=BG_COLOUR, fg=FG_COLOUR,
                                 font=FONT, height=HEIGHT, width=WIDTH,
                                 undo=False, call_init=False)
        self.text.pack(fill="both", expand=True)
        self.text.tag_config("error", foreground="red")
        self.text.bind("<Key>", self.tk_check_read_ony)
        self.text.bind("<BackSpace>", self.tk_check_read_ony, add=True)
        self.text.bind("<Delete>", self.tk_check_read_ony, add=True)
        self.text.bind("<Return>", self.tk_send_to_stdin)
        self.text.init()
        self.text.focus()

        self.set_up = True

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

        # White listed:
        if char in ("Up", "Down", "Left", "Right"):
            return None

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
            text = self.remove_dead_chars(text)
            if "\r" in text:
                print(repr(text))
            if len(text) > 0:
                insert = self.text.index("insert")
                self.text.insert("end", text)
                self.text.tag_add("readonly", insert, "insert")
                self.text.tag_add("error", insert, "insert")
                self.text.see("insert")

            text = self.tk_stdout.read_all()
            text = self.remove_dead_chars(text)
            if "\r" in text:
                print(repr(text))
            if len(text) > 0:
                insert = self.text.index("insert")
                self.text.insert("end", text)
                self.text.tag_add("readonly", insert, "insert")
                self.text.see("insert")

        if self.closed:
            self.tk_close()
        else:
            self.root.after(WAIT_NEXT_LOOP, self.tk_mainloop)

    @staticmethod
    def remove_dead_chars(text):
        return text.replace("\r", "")

    def _tk_send_to_stdin(self):
        with self.stdin_working:
            mark_for_readonly_range = []
            text = ""
            # Get the ranges
            ranges_readonly = self.text.tag_ranges("readonly")
            ranges_sent = self.text.tag_ranges("sent_for_checking")
            _range = Range(self.text)

            # Subtract them from the whole thing:
            for i in range(0, len(ranges_readonly), 2):
                _range.subtract_range(ranges_readonly[i], ranges_readonly[i+1])
            for i in range(0, len(ranges_sent), 2):
                _range.subtract_range(ranges_sent[i], ranges_sent[i+1])

            for start, end in _range.tolist():
                text += self.text.get(start, end)
                if "\n" in text:
                    chars = text.index("\n")+1
                    end = start+"+%ic" % chars
                    mark_for_readonly_range.append((start, end))
                    self.text.tag_add("sent_for_checking", start, end)
                    text = text[:chars]
                    break;
                mark_for_readonly_range.append((start, end))

            if text[-1:] == "\n":
                self.improved_stdin_handle.write(text)
                for start, end in mark_for_readonly_range:
                    self.text.tag_add("readonly", start, end)
                    self.text.tag_remove("sent_for_checking", "0.0", "end")

    def tk_send_to_stdin(self, event):
        self.text.mark_set("insert", "end")
        # First handle the "\n" comming in
        self.text.insert("insert", "\n")
        if self.improved_stdin_handle.check_child_reading():
            self._tk_send_to_stdin()
        return "break"

    def tk_stdout_read(self):
        while not self.closed:
            data = self.ptrs["stdout"].read(1).decode()
            self.tk_stdout.write(data)

    def tk_stderr_read(self):
        while not self.closed:
            self.tk_stderr.write(self.ptrs["stderr"].read(1).decode())

    def tk_close(self):
        self.forver_cmd_running = False
        self.closed = True
        super().stop_process()
        self.root.close()

    def run(self, command):
        if self.closed:
            return Exception("Terminal closed by user")
        self.tk_stdout.reset()
        self.tk_stderr.reset()
        return super().run(command)

    def clear(self):
        if self.closed:
            return Exception("Terminal closed by user")
        self.should_clear_screen = True
        while self.should_clear_screen:
            sleep(0.3)

    def close(self):
        self.closed = True


if __name__ == "__main__":
    terminal = TkTerminal()
    terminal.run("cmd")
    #terminal.forever_cmd()
