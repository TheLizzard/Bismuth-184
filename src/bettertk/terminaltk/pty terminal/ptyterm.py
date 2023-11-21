from __future__ import annotations
from threading import Thread, Lock
from subprocess import Popen
import pty, fcntl, termios
from tkinter import font
from time import sleep
import tkinter as tk
import ctypes
import os


UINT_2:type = ctypes.c_ushort
class WinSize(ctypes.Structure):
    _fields_ = (("height", UINT_2),
                ("width", UINT_2),
                ("xpix", UINT_2),
                ("ypix", UINT_2))


class PtyPeekaboo:
    __slots__ = "fd", "buffer", "closed"

    def __init__(self, fd:int) -> Peekaboo:
        self.closed:bool = False
        self.buffer:bytes = b""
        self.fd:int = fd

    def write(self, data:bytes) -> None:
        assert not self.closed, "PtyPipeClosed"
        while len(data) > 0:
            written_length:int = os.write(self.fd, data)
            data:bytes = data[written_length:]

    def close(self) -> None:
        assert not self.closed, "PtyPipeClosed"
        self.closed:bool = True
        os.close(self.fd)

    def read(self, length:int) -> bytes:
        return self._read(length, delete=True)

    def peek(self, length:int) -> bytes:
        return self._read(length, delete=False)

    def _read(self, length:int, *, delete:bool) -> bytes:
        assert not self.closed, "PtyPipeClosed"
        extra_length_needed:int = length-len(self.buffer)
        if extra_length_needed > 0:
            self.buffer += os.read(self.fd, extra_length_needed)
        data:bytes = self.buffer[:length]
        if delete:
            self.buffer:bytes = self.buffer[length:]
        return data

    def fileno(self) -> int:
        return self.fd

    def resize(self, width:int, height:int) -> None:
        assert not self.closed, "PtyPipeClosed"
        winsize:WinSize = WinSize(width=width, height=height, xpix=0, ypix=0)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, bytes(winsize))


CHUNK_SIZE:int = 1024
ST:str = "\x1b\\"
BEL:str = "\x07"
BS:str = "\b"
CR:str = "\r"
FF = NP = "\f"
NL = LF = "\n"
SP = " "
TAB = "\t"
VT = "\v"

INT_TO_COLOUR = {0:"black",
                 1:"red",
                 2:"green",
                 3:"yellow",
                 4:"blue",
                 5:"magenta",
                 6:"cyan",
                 7:"white"}


class TerminalScreen:
    __slots__ = "text", "queue", "cursor_tags", "width", "height"

    def __init__(self, text:tk.Text, size:(int,int)) -> None:
        assert isinstance(text, tk.Text), "TypeError"
        self.text:tk.Text = text
        self.text.config(width=size[0], height=size[1])
        self.text.bind("<KeyPress>", self.key_pressed)
        self.config_tags()
        self.queue:list[tuple[bool,str]] = []
        self.resize(*size)
        self.apply_queue()

    def config_tags(self) -> None:
        # Font magic
        kwargs = font.nametofont(self.text.cget("font")).actual()
        kwargs["size"] = kwargs["size"]+2
        self.text.config(font=font.Font(self.text, **kwargs))
        bold = font.Font(self.text, **{**kwargs, "weight":"bold"})
        italic = font.Font(self.text, **{**kwargs, "slant":"italic"})
        # Set up other stuff
        self.cursor_tags:list[str] = []
        self.text.mark_set("termcursor", "1.0")
        # Tags
        for number, colour in INT_TO_COLOUR.items():
            self.text.tag_config(f"BG{number}", background=colour)
            self.text.tag_config(f"FG{number}", foreground=colour)
        self.text.tag_config("UNDERLINED", underline=True)
        self.text.tag_config("ITALIC", font=italic)
        self.text.tag_config("BOLD", font=bold)

    # Not thread-safe
    def resize(self, width:int, height=int) -> None:
        self.width:int = width
        self.height:int = height

    def write(self, data:str, is_ansi:bool) -> None:
        self.queue.append((is_ansi, data))

    # Inside tkinter's thread
    def apply_queue(self) -> None:
        #print(len(self.queue))
        while len(self.queue) > 0:
            self.handle_event(*self.queue.pop(0))
        self.text.after(100, self.apply_queue)

    def handle_event(self, is_ansi:bool, data:str) -> None:
        if not is_ansi:
            self.insert(data)
        elif data == "\r":
            self.text.mark_set("termcursor", "termcursor linestart")
        elif data == "\n":
            self.insert_newline()
        elif data.startswith("FG") or data.startswith("BG"):
            self.cursor_tags.append(data)
        elif data in ("BOLD", "ITALIC", "UNDERLINED"):
            self.cursor_tags.append(data)
        elif data == "RESET_COLOUR":
            self.cursor_tags.clear()

        elif data.startswith("ERRASE"):
            data:str = data.removeprefix("ERRASE")
            if (data[0] == "K") and (data[1] != "?"):
                data:int = int(data[1:])
                if (data == 0) or (data == 2):
                    self.text.delete("termcursor", "termcursor lineend")
                if (data == 1) or (data == 2):
                    chars:int = int(self.text.index("termcursor").split(".")[1])
                    self.text.delete("termcursor linestart", "termcursor")
                    self.text.insert("termcursor", " "*chars)
                if data not in (0, 1, 2):
                    print(f"[DEBUG] Unhandled ANSI: ERRASEK{data!r}")
            elif (data[0] == "J") and (data[1] != "?"):
                data:int = int(data[1:])
                if data == 0:
                    self.text.delete("termcursor", "end")
                elif (data == 2) or (data == 3):
                    line, char = self.get_cursor()
                    self.text.delete("1.0", "end")
                    if (line != 1) or (char != 1):
                        self.assure(line=line, char=char)
                else:
                    print(f"[DEBUG] Unhandled ANSI: ERRASEJ{data!r}")
            else:
                print(f"[DEBUG] Unhandled ANSI: ERRASE{data!r}")

        elif data.startswith("CURSOR_MOVE"):
            data:str = data.removeprefix("CURSOR_MOVE")
            row, column = data.split(";")
            self.assure(line=int(row), char=int(column)-1)

        elif data.startswith("INSERT_BLANK_CHARS"):
            chars:int = int(data.removeprefix("INSERT_BLANK_CHARS"))
            if self.text.compare("termcursor", "!=", "termcursor lineend"):
                idx:str = self.text.index("termcursor")
                self.text.insert("termcursor", " "*chars)
                self.text.mark_set("termcursor", idx)

        elif data.startswith("CURSOR_UP"):
            n:int = int(data.removeprefix("CURSOR_UP"))
            line, char = self.get_cursor()
            self.assure(line=line-n, char=char)

        elif data.startswith("CURSOR_DOWN"):
            n:int = int(data.removeprefix("CURSOR_DOWN"))
            line, char = self.get_cursor()
            self.assure(line=line+n, char=char)

        elif data.startswith("CURSOR_RIGHT"):
            n:int = int(data.removeprefix("CURSOR_RIGHT"))
            line, char = self.get_cursor()
            self.assure(line=line, char=char+n)

        elif data.startswith("CURSOR_LEFT"):
            n:int = int(data.removeprefix("CURSOR_LEFT"))
            line, char = self.get_cursor()
            self.assure(line=line, char=char-n)

        else:
            print(f"[DEBUG] Unhandled ANSI: {data!r}")

    def key_pressed(self, event:tk.Event) -> str:
        print(f"[DEBUG]: {event}")
        return "break"

    def get_cursor(self) -> tuple[int,int]:
        line, column = self.text.index("termcursor").split(".")
        return int(line), int(column)

    def assure(self, *, line:int, char:int) -> None:
        line, char = max(0, line), max(0, char)
        cline, cchar = self.text.index(f"{line}.{char}").split(".")
        cline, cchar = int(cline), int(cchar)
        if cline < line:
            self.text.insert("end", "\n"*(line-cline))
            crow:int = 0
        if cchar < char:
            self.text.insert(f"{line}.{char}", " "*(char-cchar))

    def insert(self, data:str) -> None:
        prevdata:str = self.text.get("termcursor", f"termcursor +{len(data)}c")
        self.text.insert("termcursor", data, self.cursor_tags)
        chars:int = (prevdata+"\n").find("\n")
        self.text.delete("termcursor", f"termcursor +{chars}c")

    def insert_newline(self) -> None:
        if text.compare("termcursor +1l", "==", "end"):
            self.text.insert("termcursor lineend", "\n")
        self.text.mark_set("termcursor", f"termcursor +1l linestart")


class PtyTerminal:
    __slots__ = "_master_pty", "_proc", "_screen", "_size", "_buffer"

    def __init__(self, master:tk.Text, cmd:tuple[str], size:(int,int)=(80,24)):
        self._screen:TerminalScreen = TerminalScreen(master, size)
        self._buffer:str = ""
        master_fd, slave_fd = pty.openpty()
        self._master_pty:PtyPeekaboo = PtyPeekaboo(master_fd)
        self.resize(*size)
        self._proc:Popen = Popen(cmd, stdin=slave_fd, stdout=slave_fd,
                                 stderr=slave_fd, close_fds=True,
                                 # https://stackoverflow.com/q/41542960/11106801
                                 start_new_session=True,
                                 # Force programs to use colour
                                 env=os.environ|dict(TERM="xterm-256color"))
        os.close(slave_fd) # We shouldn't keep slave_fd
        self._master_pty.peek(1) # Wait for the process to start
        Thread(target=self._read_pty, daemon=True).start()

    def close(self) -> None:
        self._master_pty.close()

    def write(self, data:bytes) -> None:
        self._master_pty.write(data)

    def resize(self, width:int, height:int) -> None:
        self._master_pty.resize(width=width, height=height)
        self._screen.resize(width=width, height=height)
        self._size:(int,int) = (width, height)

    def _read_pty(self) -> None:
        while True:
            try:
                raw_data:bytes = self._master_pty.read(CHUNK_SIZE)
                data:str = raw_data.decode("utf-8", "backslashreplace")
            except OSError:
                data:str = ""
            if len(data) == 0:
                break
            self._handle_stdout(data)
        print("DEAD")

    def _handle_stdout(self, data:str) -> None:
        assert isinstance(data, str), "TypeError"
        assert len(data) > 0, "ValueError"
        data:str = self._buffer + data
        for string, is_ansi, rest in self._split_ansi_data(data):
            if len(string) == 0:
                continue
            self._screen.write(string, is_ansi)
        self._buffer:str = rest

    def _split_ansi_data(self, data:str) -> Iterable[(str,str)]:
        assert isinstance(data, str), "TypeError"
        while len(data) > 0:
            idx:int = PtyTerminal.find_first_in_str(data, "\x1b", "\r", "\n")
            if idx != 0:
                output, data = data[:idx], data[idx:]
                yield output, False, data
            if data[:1] == "\r":
                data:str = data[1:]
                yield "\r", True, data
            if data[:1] == "\n":
                data:str = data[1:]
                yield "\n", True, data
            if data.startswith("\x1b"):
                ansi, ansi_length = self._get_ansi(data)
                if ansi_length == 0:
                    return
                if ansi_length == 1:
                    data:str = "\\x1b"+data[1:]
                    continue
                if ansi.startswith("\x1b"):
                    data:str = ansi+data[ansi_length:]
                    continue
                data:str = data[ansi_length:]
                yield ansi, True, data

    @staticmethod
    def find_first_in_str(string:str, *search:tuple[str]) -> int:
        """
        Return the idx of the first s in search that is found in string.
        Returns len(string) on fail.
        """
        curr_min:int = len(string)
        for s in search:
            idx:int = string.find(s)
            if idx != -1:
                curr_min:int = min(curr_min, idx)
        return curr_min

    @staticmethod
    def _get_ansi(data:str) -> (str, int):
        """
        Returns the ANSI operation and the size of the data consumed.
        Size of 0 means: wait - ask me again after more data comes
        Size of 1 means: can't handle this, don't send it again.

        If the ANSI operation startswith("\x1b"):
            it means that the data is split into 2 ANSI sequences and
            the returned string is the 2 sequences
        """
        assert isinstance(data, str), "TypeError"
        assert len(data) > 0, "ValueError"
        assert data[0] == "\x1b", "ValueError"
        if len(data) == 1:
            return None, 0
        if data[1:3] in (" F", " G", " L", " M", " N"):
            return None, 1
        if data[1:3] in ("#3", "#4", "#5", "#6", "#8", "%@", "%G"):
            return None, 1
        if data[1] in "()*+-./69Flmno|}~":
            return None, 1
        if data[1] == "c":
            return "\x1b[m]\x1b[H\x1b[2J", 2
        if data[1] in "DEHMNOPVWXZ_\\":
            return None, 1
        if data[1] in "=>":
            return "", 2
        if data[1] == "7":
            return "SAVE_CURSOR", 2
        if data[1] == "8":
            return "RESTORE_CURSOR", 2
        if data[1] == "\\":
            return None, 0
        # PM = ESC ^
        # PM PRIVATE_MESSAGE Pt ST
        if data[1] == "^":
            # private message
            idx:int = data.find(ST)
            if idx == -1:
                return None, 0
            private_message:str = data[2:idx] # Ignored lke xterm
            return None, 1
        # OSC = ESC ]
        # OSC Ps ; Pt (?:BEL|ST)
        if data[1] == "]":
            # Work out the end of the escape sequence
            idx1:int = data.find(BEL)
            idx2:int = data.find(ST)
            if idx1 == idx2 == -1:
                return None, 0
            if idx1 == -1:
                idx:int = idx2
            elif idx2 == -1:
                idx:int = idx1
            else:
                idx:int = min(idx1, idx2)
            size:int = idx+1
            ps_pt:str = data[2:idx]
            if ";" not in ps_pt:
                return None, 1
            ps, pt = ps_pt.split(";", 1)
            if ps == "0":
                return "TITLE_ICON_CHANGE"+pt, size
            if ps == "1":
                return "ICON_CHANGE"+pt, size
            if ps == "2":
                return "TITLE_CHANGE"+pt, size
            return None, 1
        # CSI = ESC [
        if data[1] == "[":
            data:str = data[2:]
            if len(data) == 0:
                return None, 0
            if data[0] in "u#>":
                return None, 1
            if data == "?":
                return None, 1
            args, size = PtyTerminal._parse_args(data)
            size += 2
            if args is None:
                return None, 0
            if len(args) == 0:
                return None, 0
            if args[-1] == "@":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "INSERT_BLANK_CHARS"+args[0], size
            if args[-1] == " @":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "SHIFT_SCREEN_LEFT"+args[0], size
            if args[-1] == "A":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "CURSOR_UP"+args[0], size
            if args[-1] == " A":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "SHIFT_SCREEN_RIGHT"+args[0], size
            if args[-1] == "B":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "CURSOR_DOWN"+args[0], size
            if args[-1] == "C":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "CURSOR_RIGHT"+args[0], size
            if args[-1] == "D":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "CURSOR_LEFT"+args[0], size
            if args[-1] == "E":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "CURSOR_NEXT_LINE"+args[0], size
            if args[-1] == "F":
                args = tuple(filter(bool, args))
                if len(args) == 1:
                    args = ("1",)+args
                if len(args) != 2:
                    return None, 1
                return "CURSOR_PREV_LINE"+args[0], size
            if args[-1] in "GILMP#P#Q#RXZ^`abcdefginpqr":
                return None, 1
            if args[-1] == "H":
                if len(args) == 1:
                    args = ("1","1")+args
                if len(args) == 2:
                    args = (args[0], "1", args[1])
                if args[0] == "":
                    args = ("1", *args[1:])
                if len(args) != 3:
                    return None, 1
                return "CURSOR_MOVE"+";".join(args[:2]), size
            if args[-1] == "J":
                if args[0] == "":
                    args = ("0", "J")
                if len(args) == 3:
                    args = ("?"+args[0], None)
                if len(args) != 2:
                    return None, 1
                return "ERRASEJ"+args[0], size
            if args[-1] == "K":
                if args[0] == "":
                    args = ("0", "K")
                if len(args) == 3:
                    args = ("?"+args[0], None)
                if len(args) != 2:
                    return None, 1
                return "ERRASEK"+args[0], size
            if args[-1] == "S":
                if len(args) == 1:
                    args = ("1",)+args
                elif args[0] == "?":
                    return None, 1
                if len(args) != 2:
                    return None, 1
                return "SCROLL_UP_LINES"+args[0], size
            if args[-1] == "T":
                if len(args) == 1:
                    args = ("1",)+args
                elif args[0] == ">":
                    return None, 1
                if len(args) != 2:
                    return None, 1
                return "SCROLL_DOWN_LINES"+args[0], size
            if args[-1] == "h":
                if (args[0] != "?") or (len(args) != 3):
                    return None, 1
                if args[1] == "1":
                    # Application Cursor Keys - used by `less`
                    return "", size
                if args[1] == "1049":
                    return "SAVE_SCREEN_STATE_RESET_STATE", size
                if args[1] == "2004":
                    return "PASTE_BREAK1", size
            if args[-1] == "l":
                if (args[0] != "?") or (len(args) != 3):
                    return None, 1
                if args[1] == "1":
                    # Application Cursor Keys - used by `less`
                    return "", size
                if args[1] == "1049":
                    return "RESTORE_SCREEN_STATE", size
                if args[1] == "2004":
                    return "PASTE_BREAK0", size
            if args[-1] == "t":
                if len(args) != 4:
                    return None, 1
                if args[1] == "0":
                    if args[0] == "22":
                        # Save icon + window title in the stack
                        return "", size
                    if args[0] == "23":
                        # Pop and set icon + window title in the stack
                        return "", size
                elif args[1] == "4":
                    _, width, height, _ = args
                    return f"RESIZE_WINDOW_PIX{width};{height}", size
                elif args[1] == "8":
                    _, width, height, _ = args
                    return f"RESIZE_WINDOW_CHR{width};{height}", size
            if args[-1] == "m":
                if len(args) == 1:
                    return "RESET_COLOUR", size
                if (args[0] in "0") and (len(args) == 2):
                    return "RESET_COLOUR", size
                if args[0].isdigit() and (len(args) == 2):
                    digit:int = int(args[0])
                    if digit == 1:
                        return f"BOLD", size
                    if digit == 2:
                        return f"FAINT", size
                    if digit == 3:
                        return f"ITALIC", size
                    if digit == 4:
                        return f"UNDERLINED", size
                    if 30 <= digit <= 37:
                        return f"FG{digit-30}", size
                    if 40 <= digit <= 47:
                        return f"BG{digit-40}", size
                if args == ("01", "31", "m"):
                    return f"\x1b[1m\x1b[31m", size
        return None, 1

    @staticmethod
    def _parse_args(data:str) -> (tuple[str], int):
        size:int = 0
        args:list[str] = []
        if data[:1] == "?":
            size += 1
            args.append("?")
            data:str = data[1:]
        while True:
            arg:str = ""
            while len(data) > 0:
                size += 1
                char, data = data[:1], data[1:]
                if char not in "0123456789":
                    break
                arg += char
            if (len(args) != "") or (len(args) != 2):
                args.append(arg)
            if char != ";":
                break
        if char in "0123456789;":
            return None, 0
        if char in " #>":
            if len(data) == 0:
                return None, 0
            char += data[0]
            size += 1
        args.append(char)
        return tuple(args), size


from os.path import dirname
cmd = ["g++", f"{dirname(__file__)}/test.cpp"]
cmd = ["echo", "-e", "abc\ndef\r\\x1b[Ax"]
#cmd = ["python3", "/media/thelizzard/C36D-8837/pokemon/hoster.py", "--https"]
#cmd = ["echo", "\\x1b[\\n"]
#cmd = ["bash"]


root = tk.Tk()
text = tk.Text(root, bg="black", fg="white", insertbackground="white")
text.pack(fill="both", expand=True)

pty_terminal = PtyTerminal(text, cmd)

root.mainloop()


# pty_terminal.resize(width=50, height=24)
#pty_terminal.write(b"less '/home/thelizzard/Downloads/pty terminal/test.cpp'\n")
#pty_terminal.write(b"q")
#pty_terminal.write(b"clear\n")
#pty_terminal.write(b"a")
#sleep(1)
#pty_terminal.write(b"\b")
#sleep(1)
#pty_terminal.write(b"\nexit\n")


"""
[bash]
PASTE_BREAK = \x1b[?2004h \x1b[?2004l
TITLE SET = \x1b]0; TITLE TEXT \x07
PROMPT = \x1b[01;32m GREEN FG \x1b[00m WHITE FG \x1b[01;34m BLUE FG \x1b[00m WHITE FG

[bash]
WITH PASTE_BREAK:
    TITLE SET PROMPT ^C
\r
WITH PASTE_BREAK:
\r\r\n
WITH PASTE_BREAK:
    TITLE SET PROMPT clear \r\n
\r exit \r\n \x1b[H\x1b[2J\x1b[3J
WITH PASTE_BREAK:
    TITLE SET PROMPT exit \r\n
\r exit \r\n
"""


"""
Worked Example:
  # https://github.com/lubyagin/rubash/blob/master/linux.py

For win:
  # https://stackoverflow.com/a/13256908/11106801
  # https://learn.microsoft.com/en-us/windows/console/console-functions

Run bash in interactive mode:
  # https://stackoverflow.com/q/41542960/11106801

Half worked example:
  # https://stackoverflow.com/q/11165521/11106801

DOCS:
  # /usr/lib/python3.10/pty.py
  # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
  # https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797
  # http://www.manmrk.net/tutorials/ISPF/XE/xehelp/html/HID00000594.htm

ANSI escape sequences regex:
  # https://github.com/getcuia/stransi/blob/main/src/stransi/ansi.py
"""