from signal import CTRL_C_EVENT, SIGTERM, CTRL_BREAK_EVENT, SIGINT, SIGABRT, SIGBREAK
#ping 8.8.8.8 -n 20

from _tkinter import TclError
from threading import Lock
from time import sleep
import tkinter as tk
import sys
import os

from _terminal.basic_terminal import BasicTerminal
from _terminal.tag_negator import Range

from basiceditor.text import ScrolledText, KEY_REPLACE_DICT
from constants.settings import settings
from constants.bettertk import BetterTk


FONT = settings.terminal.font.get()
HEIGHT = settings.terminal.height.get()
WIDTH = settings.terminal.width.get()
BG_COLOUR = settings.terminal.bg.get()
FG_COLOUR = settings.terminal.fg.get()
TITLEBAR_COLOUR = settings.terminal.titlebar_colour.get()
TITLEBAR_SIZE = settings.terminal.titlebar_size.get()
NOTACTIVETITLE_BG = settings.terminal.notactivetitle_bg.get()

WAIT_NEXT_LOOP = settings.terminal.wait_next_loop_ms.get()
WAIT_STDIN_READ = settings.terminal.wait_stdin_read_ms.get()
KILL_PROCESS = settings.terminal.kill_proc.get()


class Buffer:
    def __init__(self):
        self.data = []

    def write(self, data, flag):
        if len(data) != 0:
            self.data.append((data.decode().replace("\r", ""), flag))

    def read_all(self):
        result, self.data = self.data, []
        return result

    def reset(self):
        self.data.clear()


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


class Terminal(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bd=0, highlightthickness=0)
        self.term = BasicTerminal(KILL_PROCESS, callback=self.update)
        self.fds = self.term.get_std_parent()
        self.stdin_working = Lock()
        self.err_code = None
        self.running = False
        self.closed = False

        self.output_buffer = Buffer()

        self.tk_init()

    def tk_init(self):
        self.text = ScrolledText(self, bg=BG_COLOUR, fg=FG_COLOUR, font=FONT,
                                 height=HEIGHT, width=WIDTH, undo=False,
                                 call_init=False)
        self.text.pack(fill="both", expand=True)
        self.text.tag_config("readonly", foreground="white")
        self.text.tag_config("error", foreground="red")
        self.text.bind("<Key>", self.check_stdin_read_ony)
        # self.text.bind("<Control-Shift-KeyPress-C>", self.send_interupt)
        self.text.bind("<Control-Delete>", self.send_kill_proc)
        self.text.bind("<BackSpace>", self.check_stdin_read_ony, add=True)
        self.text.bind("<Delete>", self.check_stdin_read_ony, add=True)
        self.text.bind("<Return>", self.tk_send_to_stdin)
        self.text.init()
        self.text.focus()

        self.tk_mainloop()

    def send_interupt(self, event): # Not working
        from ctypes import WinError
        print("sending ctrl-c")
        if self.term.pid is not None:
            try:
                # CTRL_BREAK_EVENT # SIGINT # CTRL_C_EVENT
                os.kill(self.term.pid, CTRL_BREAK_EVENT)
            except Exception as error:
                print(WinError())
                print(error)

    def send_kill_proc(self, event):
        if self.term.pid is not None:
            self.term.proc.send_signal(SIGTERM)
            # os.kill(self.term.pid, SIGTERM)

    def check_stdin_read_ony(self, event):
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
        for text, flag in self.output_buffer.read_all():
            end = self.text.index("end-1c")
            self.text.insert("end", text)
            self.text.tag_add("readonly", end, "end-1c")
            if flag == "e":
                self.text.tag_add("error", end, "end-1c")
            self.text.see("insert")

        self.text.after(WAIT_NEXT_LOOP, self.tk_mainloop)

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
                    break
                mark_for_readonly_range.append((start, end))

            if text[-1:] == "\n":
                self.fds["stdin"].write(text.encode())
                for start, end in mark_for_readonly_range:
                    self.text.tag_add("readonly", start, end)
                    self.text.tag_remove("sent_for_checking", "0.0", "end")

    def tk_send_to_stdin(self, event):
        self.text.mark_set("insert", "end")
        # First handle the "\n" comming in
        self.text.insert("insert", "\n")
        self.text.see_insert()
        if self.term.std._in.is_waiting(WAIT_STDIN_READ):
            self._tk_send_to_stdin()
        return "break"

    def stdout_stderr_read(self):
        if self.running:
            self.text.after(1, self.stdout_stderr_read)
        stdout_data = self.fds["stdout"].read(1024)
        stderr_data = self.fds["stderr"].read(1024)
        self.output_buffer.write(stdout_data, flag="o")
        self.output_buffer.write(stderr_data, flag="e")

    def close(self):
        self.forver_cmd_running = False
        self.term.stop_process()
        self.running = False
        self.closed = True

    def run(self, command: str):
        self.running = True
        self.text.after(1, self.stdout_stderr_read)
        self.output_buffer.reset()
        self.term.stop_process()
        self.term.run_no_wait(command)
        self.text.after(100, self.check_proc_done)

    def check_proc_done(self):
        err_code = self.term.poll()
        if err_code is None:
            self.text.after(100, self.check_proc_done)
        else:
            self.text.event_generate("<<FinishedProcess>>", when="tail")
            self.running = False
            self.err_code = err_code

    def clear(self):
        self.text.delete("0.0", "end")

    def get_exit_code(self):
        return self.err_code

    def stdout_write(self, text, add_padding=False, end="\n"):
        self.term.stdout_write(text, add_padding=add_padding, end=end)

    def stderr_write(self, text, add_padding=False, end="\n"):
        self.term.stderr_write(text, add_padding=add_padding, end=end)

    def focus_force(self):
        self.text.focus_force()

    def focus(self):
        self.focus_force()

    def stop_process(self):
        self.term.stop_process()


class TerminalWindow:
    def __init__(self, master=None, _class=tk.Tk):
        if _class == tk.Tk:
            self.root = BetterTk(titlebar_bg=BG_COLOUR,
                                 titlebar_fg=TITLEBAR_COLOUR,
                                 titlebar_sep_colour=FG_COLOUR, _class=_class,
                                 titlebar_size=TITLEBAR_SIZE,
                                 notactivetitle_bg=NOTACTIVETITLE_BG)
        else:
            self.root = BetterTk(master=master, titlebar_bg=BG_COLOUR,
                                 titlebar_fg=TITLEBAR_COLOUR,
                                 titlebar_sep_colour=FG_COLOUR, _class=_class,
                                 titlebar_size=TITLEBAR_SIZE,
                                 notactivetitle_bg=NOTACTIVETITLE_BG)
        self.root.title("Terminal")
        self.root.iconbitmap("logo/logo2.ico")
        self.root.buttons["X"].config(command=self.close)

        self.term = Terminal(self.root)
        self.term.pack(fill="both", expand=True)

    def close(self):
        self.term.close()
        self.root.close()

    def clear(self):
        self.term.clear()

    def run(self, command):
        self.term.run(command)

    def get_exit_code(self):
        return self.term.get_exit_code()

    def stdout_write(self, text, add_padding=False, end="\n"):
        self.term.stdout_write(text, add_padding=add_padding, end=end)

    def stderr_write(self, text, add_padding=False, end="\n"):
        self.term.stderr_write(text, add_padding=add_padding, end=end)

    def mainloop(self):
        self.root.mainloop()

    def bind(self, sequence, function):
        return self.term.text.bind(sequence, function)

    def focus_force(self):
        self.root.focus_force()
        self.term.focus_force()

    def focus(self):
        self.focus_force()

    @property
    def closed(self):
        return self.term.closed

    @property
    def running(self):
        return self.term.running

    @property
    def err_code(self):
        return self.term.err_code

    def stop_process(self):
        self.term.stop_process()


if __name__ == "__main__":
    # ping 8.8.8.8 -n 20
    terminal = TerminalWindow()
    # terminal.run(r"compiled\ccarotmodule.exe")
    terminal.run("cmd")
    # terminal.close()
    # terminal.forever_cmd()
    terminal.mainloop()
