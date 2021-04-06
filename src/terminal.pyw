from signal import CTRL_C_EVENT, SIGTERM, CTRL_BREAK_EVENT, SIGINT, SIGABRT, SIGBREAK
#ping 8.8.8.8 -n 20

from _tkinter import TclError
from threading import Lock
from time import sleep
import tkinter as tk
import sys
import os

from _terminal.pseudoconsole import Console
from _terminal.tag_negator import Range

from basiceditor.text import ScrolledText
from constants.settings import settings
from constants.bettertk import BetterTk


class ConsoleText(ScrolledText):
    def move_insert(self, drow, dcolumn):
        current_row, current_column = super().index("insert").split(".")
        self._moveto_insert(int(current_row)+drow, int(current_column)+dcolumn)

    def moveto_insert(self, row, column):
        see_row = int(super().index("@0,0").split(".")[0]) - 1
        self._moveto_insert(row+see_row, column)

    def _moveto_insert(self, row, column):
        # Try going to `(row, column)`
        super().mark_set("insert", "%i.%i" % (row, column))

        # See where we got up to as in the row
        current_row = int(super().index("insert").split(".")[0])
        # Calculate the number of new lines needed to reach `row`
        number_of_newlines_needed = row - current_row
        # If the number is +ve and not 0
        if number_of_newlines_needed > 0:
            # Add the new lines
            super().insert("insert lineend", "\n"*number_of_newlines_needed)

        # See where we got up to as in the column
        current_column = int(super().index("insert").split(".")[1])
        # Calculate the number of new lines needed to reach `column`
        number_of_spaces_needed = column - current_column
        # If the number is +ve and not 0
        if number_of_spaces_needed > 0:
            # Add the spaces
            super().insert("insert lineend", " "*number_of_spaces_needed)

        # We should be in the correct place so we don't need this:
        # super().mark_set("insert", "%i.%i" % (row, column))


WIDTH = settings.terminal.width.get()
HEIGHT = settings.terminal.height.get()

FONT = settings.terminal.font.get()
BG_COLOUR = settings.terminal.bg.get()
FG_COLOUR = settings.terminal.fg.get()
TITLEBAR_COLOUR = settings.terminal.titlebar_colour.get()
TITLEBAR_SIZE = settings.terminal.titlebar_size.get()
NOTACTIVETITLE_BG = settings.terminal.notactivetitle_bg.get()


DO_NOT_WRITE_STDIN = ("Control_L", "Control_R", "Win_L", "Win_R", "Alt_L",
                      "Alt_R", "Caps_Lock", "Escape", "Shift_L", "Shift_R",
                      "Num_Lock")


STR_TO_CHR_DICT = {"Return": "\r",
                   "BackSpace": "\b",
                   "Bell": "\a",
                   "Tab": "\t",

                   "Home": "<esc>[1~",
                   "Insert": "\x1b[2~",
                   "Delete": "\x1b[3~",
                   "End": "\x1b[4~",
                   "Prior": "\x1b[5~",
                   "Next": "\x1b[6~",
                   "Home": "\x1b[7~",
                   "Up": "\x1b[A",
                   "Down": "\x1b[B",
                   "Right": "\x1b[C",
                   "Left": "\x1b[D",
                   "Clear": "\x1b[G"}


class Terminal(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bd=0, highlightthickness=0)
        self.console = Console(WIDTH, HEIGHT)
        self.err_code = None
        self.running = False
        self.closed = False
        self.stdout_buffer = ""

        self.tk_init()
        self.console.stdout_callback = self.print_on_screen

    def print_on_screen(self, data):
        try:
            self._print_on_screen(data)
        except tk.TclError:
            pass

    def _print_on_screen(self, data):
        data = data.decode()
        ######################################## print("Recieving:", repr(data))
        self.stdout_buffer += data
        buffer_repr = repr(self.stdout_buffer)[1:-1]
        # Backspace
        if self.stdout_buffer == "\b":
            self.text.move_insert(0, -1)
            # self.text.mark_set("insert", "insert-1c")
            self.stdout_buffer = ""
        # Go to the front of the line
        elif self.stdout_buffer == "\r":
            self.text.mark_set("insert", "insert linestart")
            self.stdout_buffer = ""
        # Tab
        elif self.stdout_buffer == "\x09":
            self.text.insert("insert", "\t")
            self.stdout_buffer = ""
        # Escape
        elif data == "\x1b":
            if self.stdout_buffer != "\x1b":
                print("1Couldn't handle \"%s\"" % buffer_repr[0:-4])
                self.stdout_buffer = "\x1b"
            return None
        # Go down 1 line
        elif self.stdout_buffer == "\n":
            self.text.move_insert(1, 0)
            self.stdout_buffer = ""
        elif self.stdout_buffer.startswith("\x1b"):
            data = self.stdout_buffer.lstrip("\x1b")
            if len(data) < 2:
                return None
            escape_char, *data = data
            data = "".join(data)
            number, control, add_data = self.split_ansi(data)
            if control is None:
                return None
            if escape_char == "]":
                ######################### Needs Work ###########################
                if add_data[-1:] == "\a":
                    number = number[0]
                    # `if number == 0`  # Set Icon and Window Title
                    # `if number == 2`  # Window Title
                    if number == 0:
                        ico = add_data[:-1]
                        # Set the icon to `ico`. `ico` is a filepath to *.exe
                        # or *.ico or ...
                    if (number == 2) or (number == 0):
                        title = add_data[:-1]
                        # Set the title to whatever is in `title`
                    if (number != 0) and (number != 2):
                        print("5Couldn't handle \"%s\"" % buffer_repr)
                    self.stdout_buffer = ""
            elif control == "m":
                ######################### Needs Work ###########################
                # Controls the colour/display modes
                self.stdout_buffer = ""
            elif control == "X":
                ######################### Needs Work ###########################
                # No idea what it does
                self.stdout_buffer = ""
            elif control == "H":
                # Move the cursor to (row, column)
                if isinstance(number, int):
                    number = (number, 1)
                row, column = number
                self.text.moveto_insert(row, column-1)
                # self.text.mark_set("insert", "%i.%i" % (row, column + 1))
                self.stdout_buffer = ""
            elif control == "A":
                # Up arrow
                self.text.move_insert(-number, 0)
                # self.text.mark_set("insert", "insert-%il" % number)
                self.stdout_buffer = ""
            elif control == "B":
                # Down arrow
                self.text.move_insert(number, 0)
                # self.text.mark_set("insert", "insert+%il" % number)
                self.stdout_buffer = ""
            elif control == "C":
                # Right arrow
                self.text.move_insert(0, number)
                # self.text.mark_set("insert", "insert+%ic" % number)
                self.stdout_buffer = ""
            elif control == "D":
                # Left arrow
                self.text.move_insert(0, -number)
                # self.text.mark_set("insert", "insert-%ic" % number)
                self.stdout_buffer = ""
            elif control[0] == "l":
                # if (number == 25) and (control == "l"): # Hide the cursor
                self.stdout_buffer = ""
            elif control[0] == "?":
                # if (number == 25) and (control == "?h"): # Shows the cursor
                self.stdout_buffer = ""
            elif control == "J":
                # Erase in Display
                if data[0] not in "0123":
                    number = 0
                if number == 0:
                    self.text.delete("insert", "end")
                elif number == 1:
                    self.text.delete("0.0", "insert")
                elif number == 2:
                    self.text.delete("0.0", "end")
                elif number == 3:
                    self.text.delete("0.0", "end")
                else:
                    print("2Couldn't handle \"%s\"" % buffer_repr)
                self.stdout_buffer = ""
            elif control == "K":
                # Erase in Line
                if data[0] not in "0123":
                    number = 0
                if number == 0:
                    self.text.delete("insert", "insert lineend")
                elif number == 1:
                    self.text.delete("insert", "insert linestart")
                elif number == 2:
                    self.text.delete("insert linestart", "insert lineend")
                else:
                    print("2Couldn't handle \"%s\"" % buffer_repr)
                self.stdout_buffer = ""
            else:
                print("3Couldn't handle \"%s\"" % buffer_repr)
                self.stdout_buffer = ""
        elif self.stdout_buffer.isprintable():
            next_char = self.text.get("insert", "insert+1c")
            if next_char == "\n":
                if data == "\n":
                    self.text.delete("insert", "insert+1c")
            elif next_char != "":
                self.text.delete("insert", "insert+1c")
            self.text.insert("insert", data)
            self.text.see("insert")
            self.stdout_buffer = ""
        else:
            print("4Couldn't handle \"%s\"" % buffer_repr)
        insert_col = int(self.text.index("insert").split(".")[1])
        while int(self.text.index("insert").split(".")[1]) > insert_col and \
              self.text.get("insert lineend", "insert lineend+1c") == " ":
            self.text.delete("insert", "insert+1c")

    @staticmethod
    def split_ansi(data):
        # Returns `(number, control, add_data)`
        # Make sure that there is enough data
        if len(data) == 0:
            return None, None, None
        if data[0] == "?":
            data = data[1:]
            control_addon = "?"
            if len(data) == 0:
                return None, None, None
        else:
            control_addon = ""
        data = list(data)
        number = Terminal.get_number_from_ansi(data)
        if len(data) == 0:
            return number, None, None
        return number, control_addon+data[0], "".join(data[1:])

    @staticmethod
    def get_number_from_ansi(data:list):
        # Get the number from the ansi sequece
        # NOTE CHANGES `data`
        number = ""
        while (len(data) != 0) and (data[0] in "0123456789"):
            number += data.pop(0)
        if number == "":
            number = "1"
        number = int(number)
        if (len(data) != 0) and (data[0] == ";"):
            data.pop(0)
            return (number, Terminal.get_number_from_ansi(data))
        return number

    def tk_init(self):
        self.text = ConsoleText(self, bg=BG_COLOUR, fg=FG_COLOUR, font=FONT,
                                height=HEIGHT, width=WIDTH, undo=False,
                                call_init=False)
        self.text.pack(fill="both", expand=True)
        # The interupts
        self.text.bind("<Control-Shift-KeyPress-C>", self.send_interupt)
        self.text.bind("<Control-Delete>", self.send_kill_proc)
        # Writting to stdin
        self.text.bind("<Key>", self.write_to_proc)
        self.text.bind("<Return>", self.write_to_proc)
        self.text.bind("<BackSpace>", self.write_to_proc, add=True)
        self.text.bind("<Delete>", self.write_to_proc, add=True)
        self.text.init()
        self.text.focus()

        # Clicking on the terminal isn't supported right now.
        self.text.bind("<Button-1>", self.return_break)
        self.text.bind("<ButtonRelease-1>", self.return_break)
        self.text.bind("<Motion>", self.return_break)

    def return_break(self, event):
        return "break"

    def send_interupt(self, event):
        self.console.write(b"\x03")

    def send_kill_proc(self, event):
        self.console.close_proc()

    def get_char_from_event(self, event):
        char = event.char
        state = self.text.get_state(event)
        if ("Control" in state) or ("Alt" in state):
            return ""

        if (not char.isprintable()) or (char == ""):
            char = self.str_to_char(event.keysym)

        return char

    def str_to_char(self, char):
        # Turns "BackSpace" into "\b".
        # Turns "\n" into "\r"
        if char == "Return":
            return "\r"
        if char in DO_NOT_WRITE_STDIN:
            return ""
        if char in STR_TO_CHR_DICT:
            return STR_TO_CHR_DICT[char]
        print("Unable to write:", repr(char))
        return ""

    def write_to_proc(self, event):
        char = self.get_char_from_event(event)
        if char == "":
            return "break"
        ########################################## print("Sending:", repr(char))
        self.console.write(char.encode())
        return "break"

    def close(self):
        self.forver_cmd_running = False
        self.stop_proc()
        self.console.close_console()
        self.running = False
        self.closed = True

    def run(self, command: str):
        self.running = True
        self.stop_proc()
        self.console.run(command)
        self.text.after(100, self.check_proc_done)

    def check_proc_done(self):
        err_code = self.console.poll()
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

    def focus_force(self):
        self.text.focus_force()

    def focus(self):
        self.focus_force()

    def stop_proc(self):
        self.console.close_proc()


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
