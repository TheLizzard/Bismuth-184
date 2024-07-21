import sys
import os

from terminaltk.terminaltk import TerminalTk

assert len(sys.argv) != 1, "IndexError: sys.argv[1]"
__name__:str = "RUN_FROM_COMMANDLINE_ARGS"
term:TerminalTk = TerminalTk(className="TerminalTk")
if os.path.isdir(sys.argv[1]):
    folder:str = sys.argv[1]
    term.queue(0, ["cd", folder], "")
    term.queue(1, ["bash"], f' Starting "bash" '.center(80,"=")+"\n")
else:
    file:str = sys.argv[1]
    fname:str = os.path.split(file)[-1]
    term.queue(0, [file], f' Starting "{fname}" '.center(80,"=")+"\n")
term.mainloop()