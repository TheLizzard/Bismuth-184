"""
This is a bunch of classes and functions to make dealing with SharedMemory
easier if its structure is well-typed.

Internally all sizes are in bits but externally the user should only ever use
the Bit and Byte classes for sizes.
"""
from __future__ import annotations


class Struct:
    __slots__ = "memview"

    def __init__(self, memview:memoryview) -> Struct:
        self.memview:memoryview = memview

    @classmethod
    def size(Class:type[Struct]) -> int:
        assert issubclass(Class, Struct), "TypeError"
        output:int = 0
        for field in Class._fields_:
            name, size, t = field
            assert isinstance(size, _Size), "Don't use ints for sizes"
            output += size
        return output


class _Size:
    __slots__ = "value"

    def __init__(self, value:int) -> _Size:
        self.value:int = value

    def __radd__(self, other:int) -> _Size:
        assert other == 0, "don't use ints for sizes"
        return self

    def __add__(self, other:_Size) -> _Size:
        assert isinstance(other, _Size), "don't use ints for sizes"
        return _Size(self.value+other.value)

    def __rmul__(self, other:int) -> _Size:
        assert isinstance(other, int), "don't use ints for sizes"
        return _Size(self.value*other)

    def __repr__(self) -> str:
        return f"Size({self.value} bits)"


bit:_Size = _Size(1)
byte:_Size = _Size(8)
ascii:_Size = byte


def sizeof(t:type) -> int:
    assert isinstance(t, type), "TypeError"
    if issubclass(t, Struct):
        return t.size()
    raise RuntimeError(f"Unexpected input type {t}")


class Header(Struct):
    _fields_ = [
                 ("type", 1*byte, byte),
                 ("loc", 8*byte, int),
                 ("size", 8*byte, int),
                 ("real_size", 8*byte, int),
                 ("name", 231*ascii, ascii),
               ]


class TLFS(Struct):
    _fields_ = [
                 ("headers", 10*sizeof(Header), Header),
               ]


if __name__ == "__main__":
    data:bytearray = bytearray(5*1024*1024)
    memview:memoryview = memoryview(data)

    filesystem:TLFS = TLFS(memview)