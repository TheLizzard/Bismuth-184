"""
This is a filesystem a bit like tmpfs on Linux but should also work under
Windows.

It hasn't been implemented yet
"""
from __future__ import annotations
from multiprocessing.shared_memory import SharedMemory as _SharedMemory

try:
    from .os_tools import lock_file, unlock_file
except ImportError:
    from os_tools import lock_file, unlock_file


class SharedMemory(_SharedMemory):
    def __init__(self, name:str, *, create:bool, size:int) -> SharedMemory:
        super().__init__(name=name, create=create, size=size)

    @classmethod
    def new(Class:type, *, size:int) -> SharedMemory:
        # > The requested number of bytes when creating a new shared memory
        return SharedMemory(name=None, create=True, size=size)

    @classmethod
    def open(Class:type, *, name:str) -> SharedMemory:
        # > When attaching to an existing shared memory block,
        # > the size parameter is ignored.
        return SharedMemory(name=name, create=False, size=0)

    def close(self, *, delete:bool) -> None:
        super().close()
        if delete:
            super().unlink()


class _TmpFsBase:
    __slots__ = "mem", "block_locks"

    def __init__(self, name:str) -> _TmpFsBase:
        pass