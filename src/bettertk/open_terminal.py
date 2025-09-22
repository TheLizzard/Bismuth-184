import sys
import os

from terminaltk.terminaltk import TerminalTk


assert len(sys.argv) != 1, "IndexError: sys.argv[1]"
# __name__:str = "RUN_FROM_COMMANDLINE_ARGS" # delme
term:TerminalTk = TerminalTk(className="TerminalTk")
if os.path.isdir(sys.argv[1]):
    folder:str = sys.argv[1]
    term.queue(["cd", folder])
    term.queue(["echo", f' Starting "bash" '.center(80,"=")])
    term.queue(["bash"])
else:
    file:str = sys.argv[1]
    fname:str = os.path.split(file)[-1]
    term.queue(["echo", f' Starting "{fname}" '.center(80,"=")])
    term.queue([file])
term.queue(term.quit)
term.mainloop()
term.close()