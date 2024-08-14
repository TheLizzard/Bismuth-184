"""
This is a bunch of classes and functions to make dealing with SharedMemory
easier if its structure is well-typed.

Internally all sizes are in bits but externally the user should only ever use
the Bit and Byte classes for sizes.

================================================================================
=================== unused (too complicated to not have bugs) ==================
================================================================================
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
    _ModifyBlock
    INSIDE(resize lock)
        sub 1 master_watchers

_ModifyBlock:
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

================================================================================
================== /unused (too complicated to not have bugs) ==================
================================================================================
"""
from __future__ import annotations


class Multipliable(type):
    def __mul__(self, other:int) -> _Arr:
        assert isinstance(other, int), "Can only multiply with ints"
        return _Arr(self, other)

    def __rmul__(self, other:int) -> _Arr:
        return self.__mul__(other)

    def __repr__(Cls:type) -> str:
        return f"<{Cls.__name__}>"


class Size:
    __slots__ = "value"

    def __init__(self, value:int) -> Size:
        self.value:int = value

    def __repr__(self) -> str:
        return f"Size({self.value} bits)"


class _Arr:
    __slots__ = "t", "n"

    def __init__(self, t:type, n:int) -> _Arr:
        self.t:type = t
        self.n:int = n

    def __mul__(self, other:int) -> _Arr:
        assert isinstance(other, int), "Can only multiply with ints"
        return _Arr(self, n)

    def __rmul__(self, other:int) -> _Arr:
        return self.__mul__(other)

    def __repr__(self) -> str:
        return f"Array[{self.n}]<{self.t!r}>"

    def sizeof(self) -> Size:
        return Size(sizeof(self.t).value*self.n)


class _Sizable(metaclass=Multipliable):
    pass

class Bit(_Sizable):
    _size_ = 1

class Byte(_Sizable):
    _size_ = 8

Ascii:type = type("Ascii", (Byte,), {})
Int:type = type("Int", (object,), {})
UInt:type = type("UInt", (object,), {})
Padding:type = type("Padding", (object,), {})
BitArray:type = type("BitArray", (object,), {})
ByteArray:type = type("ByteArray", (object,), {})
BASE_TYPES:tuple[type] = (Ascii, Int, UInt, BitArray, ByteArray, Padding)


Field:type = tuple[str,Size,type]
Fields:type = list[Field]

class _StructMeta(Multipliable):
    def __new__(Class:type, name:str, bases:tuple[object],
                dct:dict) -> _StructMeta:
        if name == "Struct":
            return super().__new__(Class, name, bases, dct)
        if "_fields_" not in dct:
            raise TypeError("You must override _fields_ if inheriting " \
                            "from Struct")
        dct["_fields_"] = _StructMeta.check(dct["_fields_"])
        return super().__new__(Class, name, bases, dct)

    @staticmethod
    def check(fields:Fields) -> Fields:
        err:TypeError = TypeError("Invalid _fields_ attribute")
        if not isinstance(fields, list|tuple):
            raise err
        new_fields:Fields = []
        for field in fields:
            if (not isinstance(field, list|tuple)):
                raise err
            if len(field) != 3:
                raise err
            name, size, T = field
            if not isinstance(size, _StructMeta|_Arr):
                if size == 0:
                    continue
                raise err
            if not isinstance(name, str):
                raise err
            if not T in BASE_TYPES:
                if not isinstance(T, _StructMeta):
                    raise err
            s:int = sizeof(size).value
            if (s&7) != 0:
                padding:int = ((s+7)>>3)*8-s
                new_fields.append(("", padding*Bit, Padding))
            new_fields.append((name, size, T))
        return new_fields


class Struct(metaclass=_StructMeta):
    __slots__ = "memview"
    _fields_ = None

    def __init__(self, memview:memoryview) -> Struct:
        self.memview:memoryview = memview

    @classmethod
    def size(Class:type[Struct]) -> Size:
        assert issubclass(Class, Struct), "TypeError"
        assert Class != Struct, "TypeError"
        output:int = 0
        for field in Class._fields_:
            name, size, t = field
            output += sizeof(size).value
        return Size(output)


def sizeof(t:type) -> Size:
    if isinstance(t, type):
        if issubclass(t, Struct):
            return t.size()
        if issubclass(t, _Sizable):
            return Size(t._size_)
    if isinstance(t, _Arr):
        return t.sizeof()
    if t == 0:
        return Size(0)
    raise RuntimeError(f"Unexpected input type {t}")


num_records:int = 1024*80
chunk_size:int = 256
num_chunks:int = int(50*1024*1024/chunk_size)

class Location(Struct):
    _fields_ = [
                 ("val", 4*Byte, UInt),
               ]

class Record(Struct):
    _fields_ = [
                 ("type", 1*Byte, UInt),
                 ("name", 55*Ascii, Ascii),
                 ("start", Location, Location),
               ]

class Header(Struct):
    _fields_ = [
                 ("version", 4*Byte, UInt),
                 ("watchers", 2*Byte, UInt),
                 ("req_resize", 1*Byte, UInt),
                 ("chunk_size", 4*Byte, UInt),
                 ("num_chunks", 8*Byte, UInt),
                 ("num_records", 4*Byte, UInt),
                 ("next_free_p", Location, Location),
               ]

class Chunk(Struct):
    _fields_ = [
                 ("next", Location, Location),
                 ("data", chunk_size*Byte, ByteArray),
               ]

class TLFS(Struct):
    _fields_ = [
                 ("header", Header, Header),
                 ("record_locks", num_records*Bit, BitArray),
                 ("record_taken", num_records*Bit, BitArray),
                 ("records", num_records*Record, Record),
                 ("chunks", num_chunks*Chunk, Chunk),
               ]


if __name__ == "__main__":
    data:bytearray = bytearray(5*1024*1024)
    memview:memoryview = memoryview(data)

    filesystem:TLFS = TLFS(memview)
    print(repr(TLFS), sizeof(TLFS))