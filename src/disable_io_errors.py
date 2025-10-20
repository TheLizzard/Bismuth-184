"""
This module allows you to disable IOErrors comming from
  print/stdout/stderr writes when the underlying file
  descriptors are closed.
"""
from __future__ import annotations
import sys


def no_io_error(func:Callable) -> Callable:
    can_write:bool = True
    def inner(*args:tuple[object], **kwargs:dict[str:object]) -> object:
        nonlocal can_write
        if can_write:
            try:
                return func(*args, **kwargs)
            except (IOError, BrokenPipeError):
                can_write = False
    return inner

FileObject:type = "FileObject"
def my_print(*args:tuple[object], sep:str=" ", end:str="\n", flush:bool=False,
             file:FileObject=None) -> None:
    file:FileObject = file or sys.stdout
    data:str = sep.join(map(str, args)) + end
    file.write(data)
    if flush:
        file.flush()


if isinstance(__builtins__, dict):
    __builtins__["print"] = my_print
else:
    __builtins__.print = my_print


_sys_stdout_write:Callable = sys.stdout.write
_sys_stdout_flush:Callable = sys.stdout.flush
_sys_stderr_write:Callable = sys.stderr.write
_sys_stderr_flush:Callable = sys.stderr.flush

def enable() -> None:
    sys.stdout.write = no_io_error(sys.stdout.write)
    sys.stdout.flush = no_io_error(sys.stdout.flush)
    sys.stderr.write = no_io_error(sys.stderr.write)
    sys.stderr.flush = no_io_error(sys.stderr.flush)

def disable() -> None:
    sys.stdout.write = _sys_stdout_write
    sys.stdout.flush = _sys_stdout_flush
    sys.stderr.write = _sys_stderr_write
    sys.stderr.flush = _sys_stderr_flush
