from tkinter import filedialog
from functools import partial
from text import Text
import tkinter as tk
import subprocess
import traceback
import platform
import time
import sys
import os



FILE_TYPES = (("C++ file", "*.cpp"),
              ("Text file", "*.txt"),
              ("All types", "*"))

STARTING_TEXT = """
#include <iostream>

using namespace std;

int main(){
    cout << "Hello World!\\n";
    return 0;
}
"""
STARTING_TEXT = STARTING_TEXT[1:-1]
DEFAULT_ARGS = ()

WIDTH = 120


def get_os_bits() -> int:
    return 8 * struct.calcsize("P")

def get_os() -> int:
    os = platform.system()
    result = os.lower()
    if result in ("windows", "linux"):
        return result
    else:
        raise OSError("Can't recognise the OS type.")

OS = get_os()
PATH = os.path.dirname(os.path.realpath(__file__))
if OS == "windows":
    BASIC_RUN_COMMAND = PATH+"\\__pycache__\\ccarotmodule.exe"
    COMPILE_COMMAND = ["g++", "-O3", "-w", None, "-o", BASIC_RUN_COMMAND]
    RUN_COMMAND = "\""+BASIC_RUN_COMMAND+"\""
    RUN_COMMAND_WITHARGS = BASIC_RUN_COMMAND
    CLEAR_SCREEN = partial(os.system, "cls")

if OS == "linux":
    BASIC_RUN_COMMAND = PATH+"/__pycache__/./ccarotmodule"
    # Add "-m32" flag for 32 bit
    COMPILE_COMMAND = ["g++", "-O3", "-w", None, "-o", BASIC_RUN_COMMAND.replace("./", "")]
    RUN_COMMAND = "\""+BASIC_RUN_COMMAND+"\""
    RUN_COMMAND_WITHARGS = BASIC_RUN_COMMAND
    CLEAR_SCREEN = partial(os.system, "clear")


class GUI:
    def __init__(self, **kwargs):
        self.root = tk.Tk()
        self.root.resizable(False, False)

        self.set_up_input(**kwargs)

        self.saved_text = "Unsaved_work"
        self.file_name = None

    def set_up_input(self, **kwargs):
        font = ("DejaVu Sans Mono", 10)
        self.text = Text(self.root, font=font, **kwargs)
        self.text.grid(row=1, column=1, sticky="news")

        self.text.bind("<Control-s>", self.save)
        self.text.bind("<Control-S>", self.save)
        self.text.bind("<Control-Shift-s>", self.saveas)
        self.text.bind("<Control-Shift-S>", self.saveas)
        self.text.bind("<Control-o>", self.open)
        self.text.bind("<Control-O>", self.open)

        self.text.bind("<F5>", self.run)
        self.text.bind("<Shift-F5>", self.run_with_command)

        self.text.insert("end", STARTING_TEXT)

    def run_with_command(self, event=None):
        global DEFAULT_ARGS
        input_box = Question("What should the args be?")
        input_box.set(DEFAULT_ARGS)
        input_box.wait()
        inputs = input_box.get()
        input_box.destroy()
        if inputs is None:
            return None
        DEFAULT_ARGS = tuple(inputs)
        self.run(event, inputs)

    def run(self, event=None, args=None):
        CLEAR_SCREEN()
        out = sys.stdout
        err = sys.stderr

        # Check if the file is saved
        if self.saved_text != self.text.get("0.0", "end").rstrip():
            err.write("You need to first save the file.\n")
            return None
        if self.file_name is None:
            err.write("You need to first save the file.\n")
            return None

        # Create the compile instuction
        command = list(COMPILE_COMMAND)
        command[command.index(None)] = self.file_name

        out.write(self.add_padding("Compiling the program")+"\n")

        try:
            error = self._run(command)

            if error == 0:
                out.write(self.add_padding("Running the program")+"\n")
                # Run the program if compiled
                if args is None:
                    command = RUN_COMMAND
                else:
                    command = [RUN_COMMAND_WITHARGS]
                    command.extend(args)
                self._run(command, shell=True)

                out.write(self.add_padding("Done")+"\n")

            self.process.kill()
        except Exception as error:
            self.process.kill()
            raise error

    def _run(self, command, shell=False):
        print(command)
        self.process = subprocess.Popen(command, shell=shell)
        while self.process.poll() is None:
            time.sleep(0.2)

        errorcode = self.process.returncode
        msg = "The process finished with exit code: %d"%errorcode
        sys.stdout.write(self.add_padding(msg)+"\n")
        return errorcode

    def add_padding(self, text):
        text = " %s "%text
        length = len(text)
        p1 = "="*int((WIDTH-length)/2+0.5)
        p2 = "="*int((WIDTH-length)/2)
        return p1+text+p2

    def save(self, event=None):
        if self.file_name is None:
            self.saveas()
        else:
            self._save(self.file_name)

    def open(self, event=None):
        file = filedialog.askopenfilename(filetypes=FILE_TYPES)
        if (file != "") and (file != ()):
            self.file_name = file
            self._open(file)

    def _open(self, filename):
        with open(filename, "r") as file:
            text = file.read().rstrip()
            self.saved_text = text
            self.text.delete("0.0", "end")
            self.text.insert("end", text)
            self.text.see("end")
        self.root.title(os.path.basename(filename))

    def saveas(self, event=None):
        file = filedialog.asksaveasfilename(filetypes=FILE_TYPES,
                                            defaultextension=FILE_TYPES[0][1])
        if file != "":
            self.file_name = file
            self.save(file)

    def _save(self, filename):
        text = self.text.get("0.0", "end")
        with open(filename, "w") as file:
            file.write(text)
            self.saved_text = text.rstrip()
        self.root.title(os.path.basename(filename))

    def mainloop(self):
        self.root.mainloop()


class Question:
    def __init__(self, question):
        self.force_quit = False
        self.input_boxes = []
        self.root = tk.Toplevel()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.label = tk.Label(self.root, text=question)
        self.answer_frame = tk.Frame(self.root)
        self.done_button = tk.Button(self.root, text="Done", command=self.done)
        self.cancel_button = tk.Button(self.root, text="Cancel",
                                       command=self.on_closing)

        self.label.grid(row=1, column=1, columnspan=2, sticky="news")
        self.answer_frame.grid(row=2, column=1, columnspan=2, sticky="news")
        self.done_button.grid(row=3, column=1, sticky="news")
        self.cancel_button.grid(row=3, column=2, sticky="news")

        self.add_input_box()

    def on_closing(self):
        self.force_quit = True
        self.root.quit()
        self.root.destroy()

    def done(self):
        self.root.quit()

    def minus(self, entry):
        if len(self.input_boxes) == 1:
            return None
        del self.input_boxes[self.get_number_from_entry(entry)]
        self.regrid()

    def plus(self, entry):
        self.add_input_box(self.get_number_from_entry(entry)+1)

    def add_input_box(self, pos="last"):
        entry = tk.Entry(self.answer_frame)
        entry.focus()

        command = partial(self.minus, entry)
        button_min = tk.Button(self.answer_frame, text=" - ", command=command)

        command = partial(self.plus, entry)
        buton_plus = tk.Button(self.answer_frame, text=" + ", command=command)

        if pos == "last":
            number = len(self.input_boxes)
            entry.grid(row=number, column=1, sticky="news")
            button_min.grid(row=number, column=2, sticky="news")
            buton_plus.grid(row=number, column=3, sticky="news")
            self.input_boxes.append((entry, button_min, buton_plus))
        else:
            self.input_boxes.insert(pos, (entry, button_min, buton_plus))
            self.regrid()

    def regrid(self):
        for child in self.answer_frame.winfo_children():
            child.grid_forget()
        for i, (entry, button_min, buton_plus) in enumerate(self.input_boxes):
            entry.grid(row=i, column=1, sticky="news")
            button_min.grid(row=i, column=2, sticky="news")
            buton_plus.grid(row=i, column=3, sticky="news")

    def get_number_from_entry(self, target_entry):
        for i, (entry, _, _) in enumerate(self.input_boxes):
            if target_entry == entry:
                return i
        raise IndexError("Entry not found!")

    def wait(self):
        self.root.mainloop()

    def get(self):
        if self.force_quit:
            return None
        output = []
        for entry, _, _ in self.input_boxes:
            output.append(entry.get())
        return output

    def set(self, values):
        for value in values:
            self.add_input_box()
            entry, _, _ = self.input_boxes[len(self.input_boxes)-1]
            entry.insert("end", value)
        self.minus(self.input_boxes[0][0])

    def destroy(self):
        if not self.force_quit:
            self.root.destroy()


if __name__ == "__main__":
    gui = GUI(height=40, width=80)
    gui.mainloop()
