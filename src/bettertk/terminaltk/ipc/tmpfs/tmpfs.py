"""
This is a filesystem a bit like tmpfs on Linux but should also work under
Windows.


=================== unused (too complicated to not have bugs) ==================
CreateNew:
    STATIC_ASSERT(INSIDE(name lock))
        create shmem
        write shmem file
        CREATE(all block locks)
Connect:
    if no EXISTS(name lock):
        CREATE(name lock)
    INSIDE(name lock)
        TRY_OPEN
            open shmem file
            get shmem name
            open shmem name
        EXCEPT
            CreateNew
        add 1 refcount
Disconnect:
    INSIDE(name lock)
        sub 1 refcount
        if no refcount:
            DELETE(shmem name)
            DELETE(shmem file)
            DELETE(all block locks)
ReConnect:
    Disconnect
    Connect
CreateFile/ModifyFile/DeleteFile/DeleteFolder/CreateFolder:
    INSIDE(name lock) --- for resize (DONT remove) ---
    INSIDE(resize lock)
        if req_resize:
            ReConnect
            TRY_AGAIN
        add 1 master_watchers
    --- Actual block modification ---
    INSIDE(block lock)
        --- Aquire the record lock ---
        if watchers:
            OPEN(record lock)
        else:
            CREATE(record lock)
        add 1 watcher
    AQUIRE(record lock)
    --- Make sure to check record (is?) taken or free ---
    RecordModification
    --- Release record lock ---
    INSIDE(block lock)
        sub 1 watcher
        if watchers:
            RELASE(record lock)
        else:
            RELASE(record lock)
            DELETE(record lock)
    INSIDE(resize lock)
        sub 1 master_watchers
OnResize:
    INSIDE(resize lock)
        if req_resize:
            ReConnect
            STOP
        set req_resize
    INSIDE(name lock)
        forever:
            wait for no master_watchers
            INSIDE(resize lock)
                if no master_watchers:
                    break
            sleep(0.05)
        CreateNew
        COPY_DATA(new shmem)
    ReConnect
================== /unused (too complicated to not have bugs) ==================
"""
from __future__ import annotations
from multiprocessing.shared_memory import SharedMemory as _SharedMemory

try:
    from .os_tools import lock_file, unlock_file, NamedSemaphore
    from .rstruct import *
except ImportError:
    from os_tools import lock_file, unlock_file, NamedSemaphore
    from rstruct import *


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


CHARS_PER_FILE:int = 60
WORD_SIZE:int = 32
VERSION:int = 1


class Header(Struct):
    _fields_ = [
                 ("version_maj", 2*BYTE, UInt),
                 ("version_min", 2*BYTE, UInt),
                 ("watchers",    2*BYTE, UInt),
                 ("req_resize",  1*BYTE, UInt),
                 ("chunk_size",  4*BYTE, UInt),
                 ("num_chunks",  8*BYTE, UInt),
                 ("num_records", 4*BYTE, UInt),
               ]


def _build(records:int, chunk_s:int, chunks:int|str, name_len:int=60,
           word_size:int=32) -> type[TTLS]:
    """
    TheLizzard Temporary File System (TTFS) is a filesystem that works a bit
    like tmpfs but uses a shared memory region instead. Every process that
    connects to it has the responsibility of its upkeep.

    records:int    The number of spaces for files (max number of files)
    chunk_s:int    The size of each chunk in bytes
    chunks:int     The number of chunks available for files
    name_len:int   The maximum length of the file name (must not end in \x00)
    word_size:int  The number of bits used to encode locations/sizes

    Implications:
        chunk_s*chunks == the total space for files
        largest file size in bytes <= 2**word_size
        chunks < 2**word_size
    No point in:
        records > chunks

    How it works:
        TTFS has a single header, a list of records and a list of chunks.
        The header holds information about the version, type, and state of
        the TTFS.
        Records have a one-to-one relationship with items (an item is a single
        file/folder/symlink).
        Chunks form a linked list per item holding its data. The linked list
        terminates with a pointer to -1
    """

    if chunks == "calculate":
        chunks:int = int(2*1024*records/chunk_s)

    if chunks >= 2**word_size:
        raise ValueError("Can't access all of the chunks with this small " \
                         "of a word size")

    ITEM_SIZE = LOCATION = word_size*BIT

    class Record(Struct):
        _fields_ = [
                     ("type", 1*BYTE, UInt),
                     ("size", ITEM_SIZE, UInt),
                     ("start", LOCATION, UInt),
                     ("taken", 1*BIT, BitArray),
                     ("writer_sem", BYTE_ALIGN, UInt),
                     ("name", name_len*BYTE, ByteString),
                   ]

    class Chunk(Struct):
        _fields_ = [
                     ("next", LOCATION, UInt),
                     ("data", chunk_s*BYTE, ByteArray),
                   ]

    class TTFS(Struct):
        _fields_ = [
                     ("header", Header, Header),
                     ("records", records*Record, Array(records,Record)),
                     ("chunks", chunks*Chunk, Array(chunks,Chunk)),
                     ("next_free_p", LOCATION, UInt),
                   ]
    return TTFS


def _open(mem:memoryview) -> TTFS:
    header:Header = Header(mem, force_no_chk=True)
    if header.version != VERSION:
        raise RuntimeError("Version error")
    return _build(records=header.num_records, chunk_s=header.chunk_size,
                  chunks=header.num_chunks, name_len=CHARS_PER_FILE,
                  word_size=WORD_SIZE)(mem)

def _new_default() -> TTFS:
    return _build(records=1<<16, chunk_s=256, chunks="calculate")


class _TmpFsBase:
    __slots__ = "mem", "block_locks"

    def __init__(self, name:str) -> _TmpFsBase:
        pass


if __name__ == "__main__":
    TTFS:type = _new_default()
    s:int = sizeof(TTFS).to_bytes()
    mem:memoryview = memoryview(bytearray(s))
    fs:TTFS = TTFS(mem)