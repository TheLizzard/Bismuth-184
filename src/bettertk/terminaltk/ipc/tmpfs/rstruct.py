"""
This is a bunch of classes and functions to make dealing with well-typed,
structured memoryviews easier.

Internally all sizes are in bits but externally the user should only ever use
the BIT and BYTE constants or their own classes that inherit from Struct.
"""
from __future__ import annotations
import functools


TEST:bool = False


class _Size:
    __slots__ = "n", "type"

    def __init__(self, type:object, n:int) -> _Size:
        self.type:object = type
        self.n:int = n

    def __bool__(self) -> bool:
        return bool(self.n)

    def __mul__(self, other:int) -> _Size:
        assert isinstance(other, int), "Can only multiply with ints"
        if self.type is None:
            return _Size(None, self.n*other)
        return _Size(self, other)

    def __add__(self, other:_Size|_Uncomputed) -> _Size:
        assert isinstance(other, _Size), f"Can't add {self} to {other}"
        if not (self.type is other.type is None):
            raise ValueError(f"Can't add {self} to {other}")
        return _Size(None, self.n+other.n)

    def __rmul__(self, other:int) -> _Size:
        return self.__mul__(other)

    def __radd__(self, other:_Size|_Uncomputed) -> _Size:
        return self.__add__(other)

    def __eq__(self, other:_Size) -> bool:
        if other in (ALIGN_BYTE, FILL_BYTES):
            return False
        if isinstance(other, int):
            if other == 0:
                if self.n == 0:
                    return True
                return (self.type is not None) and (sizeof(self.type) == 0)
        assert isinstance(other, _Size), "TypeError"
        return (self.n == other.n) and (self.type == other.type)

    def __repr__(self) -> str:
        if self.type is None:
            if self.n == 0:
                return f"Empty"
            if self.n&7 == 0:
                return f"Size({self.n>>3} bytes)"
            else:
                return f"Size({self.n} bits)"
        else:
            return f"Size[{self.n}]<{self.type!r}>"

    def _size(self) -> int:
        if self.type is None:
            return self.n
        else:
            return self.n*sizeof(self.type)._size()

    @classmethod
    def _from_bits(Cls:type, n:int) -> _Size:
        return _Size(type=None, n=n)

    def to_bytes(self) -> int:
        s:int = self._size()
        if (s&7) != 0:
            raise ValueError("Not byte aligned")
        return s>>3


BIT:Bits = _Size._from_bits(1)
BYTE:Bits = _Size._from_bits(8)
NO_SIZE:_Size = _Size._from_bits(0)


class Array:
    __slots__ = "n", "type"

    def __init__(self, n:int, _type:type) -> Array:
        assert isinstance(n, int), f"First argument must be an int, not {n=!r}"
        assert isinstance(_type, type), f"Invalid type={_type!r}"
        self.type:type = _type
        self.n:int = n

    def size(self) -> _Size:
        return self.n*self.type


class _Uncomputed:
    __slots__ = ()


class _UncomputedFill(_Uncomputed):
    __slots__ = ()

    def __repr__(self) -> str:
        return "Uncomputed(FILL)"


class _UncomputedAlign(_Uncomputed):
    __slots__ = "add", "side"

    def __init__(self, add:_Size=NO_SIZE, side:bool=True) -> _Uncomputed:
        self.side:bool = side
        self.add:_Size = add

    def __repr__(self) -> str:
        insides:str = f"???+{self.add!r}" if self.side else f"{self.add!r}+???"
        return f"Uncomputed({insides})"

    def __add__(self, other:_Size) -> _Uncomputed:
        if self.side and self.add:
            self._raise_no_point()
        return _Uncomputed(self.add+other, side=False)

    def __radd__(self, other:_Size) -> _Uncomputed:
        if (not self.side) and self.add:
            self._raise_no_point()
        return _Uncomputed(self.add+other, side=True)

    def __bool__(self) -> bool:
        return bool(self.add)


_padding_meta_dict = {"__repr__":lambda*a:"<Padding>"}
_PaddingMeta:type = type("PaddingMeta", (type,), _padding_meta_dict)
Padding:type = _PaddingMeta("Padding", (object,), {})

ALIGN_BYTE:_Uncomputed = _UncomputedAlign()
BYTE_ALIGN:_Uncomputed = ALIGN_BYTE
FILL_BYTES:_Uncomputed = _UncomputedFill()


def bv(x:int) -> str: return f"{x:b}"

class BitArray:
    __slots__ = "_mem", "_n", "_loffset", "_roffset"

    def __init__(self, mem:memoryview, *, loffset:int, roffset:int,
                 size:int) -> BitArray:
        assert (loffset>>3) == (roffset>>3) == 0, "InternalError"
        assert (size+loffset+roffset) == 8*len(mem), "InternalEror"
        self._loffset:int = loffset
        self._roffset:int = roffset
        self._mem:memoryview = mem
        self._n:int = size

    def __getitem__(self, key:int) -> bool:
        assert isinstance(key, int), "TypeError"
        assert 0 <= key < self._n, "IndexError"
        key += self._loffset
        return bool((self._mem[key>>3]) & (1<<(7-(key&7))))

    def __setitem__(self, key:int, value:int|bool) -> None:
        assert isinstance(key, int), "TypeError"
        assert 0 <= key < self._n, "IndexError"
        assert value in (0, 1), "ValueError"
        key += self._loffset
        if value:
            self._mem[key>>3] |= 1<<(7-(key&7))
        else:
            self._mem[key>>3] &= ~(1<<(7-(key&7)))

    def __repr__(self) -> str:
        return f"BitArray[{self._n}]"

    def __len__(self) -> int:
        return self._n


class _Array:
    __slots__ = "_mem", "_n", "_unit_size", "type"

    def __init__(self, mem:memoryview, T:Array, *, loffset:int, roffset:int,
                 size:int) -> ByteArray:
        self._n:int = T.n
        self._unit_size:int = sizeof(T.type)._size()
        assert (loffset>>3) == (roffset>>3) == 0, "InternalError"
        assert roffset == loffset == 0, "Must be byte aligned"
        assert (self._unit_size&7) == 0, "Must be byte aligned"
        assert (size&7) == 0, "Must be byte aligned"
        assert len(mem) == (size>>3), "SizingError"
        assert self._n*(self._unit_size>>3) == len(mem), "SizingError"
        self._mem:memoryview = mem
        self.type:type = T.type

    def __getitem__(self, key:int) -> object:
        assert isinstance(key, int), "TypeError"
        assert 0 <= key < self._n, "IndexError"
        start:int = key*(self._unit_size>>3)
        mem:memoryview = self._mem[start:start+(self._unit_size>>3)]
        return _init_type(self.type, mem, size=self._unit_size, loffset=0,
                          roffset=0)

    def __repr__(self) -> str:
        return f"Array[{self._n}]<{self.type}>"

    def __len__(self) -> int:
        return self._n


class ByteArray:
    __slots__ = "_mem", "_n"

    def __init__(self, mem:memoryview, *, loffset:int, roffset:int,
                 size:int) -> ByteArray:
        assert (loffset>>3) == (roffset>>3) == 0, "InternalError"
        assert (roffset-loffset)&7 == 0, "ByteArray size isn't byte aligned"
        assert loffset == 0, "ByteArray must be byte aligned"
        assert (size&7) == 0, "Must be byte aligned"
        assert (size>>3) == len(mem), "SizingError"
        self._mem:memoryview = mem
        self._n:int = (size>>3)

    def __getitem__(self, key:int) -> int:
        assert isinstance(key, int), "TypeError"
        assert 0 <= key < self._n, "IndexError"
        return self._mem[key]

    def __setitem__(self, key:int, value:int) -> None:
        assert isinstance(key, int), "TypeError"
        assert 0 <= key < self._n, "IndexError"
        assert 0 <= value <= 255, "ValueError"
        self._mem[key] = value

    def __repr__(self) -> str:
        return f"ByteArray[{self._n}]"

    def __len__(self) -> int:
        return self._n


class ByteString(ByteArray):
    __slots__ = ()

    def __init__(self, mem:memoryview, *, loffset:int, roffset:int,
                 size:int) -> ByteString:
        super().__init__(mem, loffset=loffset, roffset=roffset, size=size)

    @property
    def value(self) -> str:
        return bytes(self._mem).split(b"\x00", 1)[0].decode("utf-8")

    def get(self) -> str:
        return self.value

    def set(self, value:str) -> None:
        assert isinstance(value, str), "TypeError"
        assert not value.endswith("\x00"), "ValueError"
        assert len(value) <= len(self), "LengthError"
        data:bytes = value.encode("utf-8")+b"\x00"
        data:bytes = data[:len(self)]
        self._mem[:len(data)] = data


@functools.total_ordering
class UInt:
    __slots__ = "_mem", "_size", "_loffset", "_lmask", "_lunmask"

    def __init__(self, mem:memoryview, *, loffset:int, roffset:int,
                 size:int) -> Uint:
        assert roffset == 0, "The end of UInt must be byte aligned"
        self._loffset:int = loffset
        self._mem:memoryview = mem
        self._size:int = size
        self._lmask:int = (1<<(8-loffset))-1
        self._lunmask:int = ((1<<self._loffset)-1) << (8-self._loffset)

    @property
    def value(self) -> int:
        return ((self._mem[0]&self._lmask) << (self._size-8+self._loffset)) | \
               (int.from_bytes(self._mem[self._loffset!=0:], "big"))

    def get(self) -> int:
        return self.value

    def set(self, value:int) -> None:
        assert isinstance(value, int), "TypeError"
        assert 0 <= value <= (1<<self._size)-1, "OverflowError"
        value:bytes = value.to_bytes((self._size+7)>>3, "big")
        self._mem[0] = (self._mem[0]&self._lunmask) | value[0]
        self._mem[1:] = value[1:]

    def __eq__(self, other:int) -> bool:
        assert isinstance(other, int), "TypeError"
        return self.value == other

    def __lt__(self, other:int) -> bool:
        assert isinstance(other, int), "TypeError"
        return self.value < other

    @property
    def min_value(self) -> int:
        return 0

    @property
    def max_value(self) -> int:
        return (1<<self._size)-1


class Int(UInt):
    __slots__ = ()

    @property
    def value(self) -> int:
        value:int = super().value
        if value & (1<<(self._size-1)):
            return (1<<(self._size-1))-1-value
        return value

    def get(self) -> int:
        return self.value

    def set(self, value:int) -> None:
        if value < 0:
            return super().set((1<<(self._size-1))-1-value)
        else:
            assert value <= self.max_value, "OverflowError"
        return super().set(value)

    @property
    def min_value(self) -> int:
        return -(1<<(self._size-1))

    @property
    def max_value(self) -> int:
        return (1<<(self._size-1))-1


BASE_TYPES:tuple[type] = (Int, UInt, BitArray, ByteArray, ByteString, Padding)
EXPANDABLES:tuple[type] = (Padding, UInt, Int)
Field:type = tuple[str,_Size|_Uncomputed,type]
Fields:type = list[Field]


class _StructMeta(type):
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
        if not isinstance(fields, list|tuple):
            raise TypeError("Invalid _fields_ attribute")
        full_size:int = 0
        new_fields:Fields = []
        field_names:set[str] = set()
        for field in list(fields)+[("padding", ALIGN_BYTE, Padding)]:
            # Check field
            if (not isinstance(field, list|tuple)):
                raise TypeError(f"Invalid {field=!r}")
            if len(field) != 3:
                raise err
            name, size, T = field
            # Fix size if uncomputed
            if size == ALIGN_BYTE:
                size:_Size = ((8-full_size)&7)*BIT + size.add
            # Check name
            if not isinstance(name, str):
                raise TypeError(f"Invalid field {name=!r}")
            if name in field_names:
                raise TypeError(f"{name!r} is repeated")
            elif name.lower() not in ("padding", "pad", "_", ""):
                field_names.add(name)
            # Check type
            if T not in BASE_TYPES:
                if not isinstance(T, _StructMeta|Array):
                    raise TypeError(f"Invalid field type={T!r}")
            if T not in EXPANDABLES:
                if sizeof(T) not in (FILL_BYTES, sizeof(size)):
                    raise TypeError(f"Type size != given size for {name=!r}")
            # Check size
            if not isinstance(size, _StructMeta|_Size):
                raise TypeError(f"Invalid field {size=!r}")
            s:int = sizeof(size)._size()
            assert s >= 0, f"Why a negative size for field={name!r}"
            if (s == 0) and (T == Padding):
                continue # Drop 0 sized padding
            full_size += s
            new_fields.append((name, size, T))
        return new_fields

    def __mul__(self, other:int) -> _Size:
        assert isinstance(other, int), "Can only multiply with ints"
        return _Size(self, n=other)

    def __rmul__(self, other:int) -> _Size:
        return self.__mul__(other)

    def __repr__(Cls:type) -> str:
        return f"<class object {Cls.__name__}>"

    def __add__(self, other:object) -> _Size:
        raise ValueError(f"Can't add {self} to {other}")

    def __radd__(self, other:object) -> _Size:
        raise ValueError(f"Can't add {self} to {other}")


class Struct(metaclass=_StructMeta):
    __slots__ = "_mem", "_loffset", "_roffset"
    _fields_ = None

    def __init__(self, mem:memoryview, *, loffset:int=0, roffset:int=0,
                 force_no_chk:bool=False) -> Struct:
        self._mem, self._loffset, self._roffset = mem, loffset, roffset
        if not force_no_chk:
            real_size:int = self.__class__.size()._size() >> 3
            assert len(mem) == real_size, "SizeCheckError"

    def _attr_access(self, key:str, value:object=None, *, _set:bool) -> object:
        if not isinstance(key, str):
            raise TypeError("key should be a string")
        left:int = self._loffset
        for name, size, T in self._fields_:
            size:int = sizeof(size)._size()
            if name == key:
                right:int = left+size
                mem:memoryview = self._mem[left>>3:(right+7)>>3]
                assert len(mem) == (size+(left&7)+7)>>3, "InternalSizingError"
                ret:object =  _init_type(T, mem, size=size, loffset=left&7,
                                         roffset=(8-(right&7))&7)
                if _set:
                    if not hasattr(ret, "set"):
                        raise RuntimeError(f"Can't replace {ret!r}")
                    return ret.set(value)
                return ret
            left += size
        raise KeyError(f"Unknown {key=!r}")

    def __setattr__(self, key:str, value:object) -> None:
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._attr_access(key, value, _set=True)

    def __getattr__(self, key:str) -> Struct|BitArray|ByteArray|int:
        return self._attr_access(key, _set=False)

    @classmethod
    def size(Class:type[Struct]) -> _Size:
        assert issubclass(Class, Struct), "TypeError"
        assert Class != Struct, "TypeError"
        output:int = 0
        for name, size, T in Class._fields_:
            output += sizeof(size)._size()
        return _Size(None, output)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} object>"


def sizeof(t:type) -> _Size|_Uncomputed:
    if t == 0:
        return NO_SIZE
    if isinstance(t, _Size|_Uncomputed):
        return t
    if isinstance(t, type):
        if issubclass(t, Struct):
            return t.size()
        if issubclass(t, UInt|Int|Padding|ByteArray|BitArray|ByteString):
            return FILL_BYTES
    if isinstance(t, Array):
        return t.size()
    raise RuntimeError(f"Unexpected input type {t}")

def _init_type(T:type, memview:memoryview, *, loffset:int, roffset:int,
               size:int) -> T:
    kwargs:dict[str:int] = dict(loffset=loffset, roffset=roffset)
    if isinstance(T, type):
        if issubclass(T, Struct):
            return T(memview, **kwargs)
        if T in (BitArray, ByteArray, UInt, Int):
            return T(memview, size=size, **kwargs)
        if issubclass(T, Padding):
            raise RuntimeError("Padding is always inaccessible.")
    if isinstance(T, Array):
        return _Array(memview, T, size=size, **kwargs)
    raise NotImplementedError(f"Unreachable {T=}")


def _test_containers(get_states:Callable[object], n:int) -> None:
    assert isinstance(max_test_values, tuple|list), "TypeError"
    assert len(all_tests) == len(max_test_values), "ValueError"
    assert isinstance(all_tests, tuple|list), "TypeError"
    states = get_states()
    for t in range(n):
        test_idx = randint(0, len(all_tests)-1)
        idx:int = randint(0, len(all_tests[test_idx])-1)
        val:int = randint(0, max_test_values[test_idx])
        all_tests[test_idx][idx] = val
        states[test_idx][idx] = val
        r_state:str = states
        t_state:str = get_states()
        assert t_state == r_state, "TestFailed"
        if (t+1) % 100_000 == 0:
            print(f"[TEST]: containers {t+1}")


def _test_int(test_name:str, get_state:Callable[object], name:str) -> None:
    test = getattr(test_obj, test_name)
    for i in range(test.min_value, test.max_value+1):
        test.set(i)
        _test_containers(get_state, n=1_000_000)
        state = get_state()
        assert get_state() == state, "BadInfluence"
        assert test.value == i, "Test failed"
        if (i+test.min_value+1) % 5_000 == 0:
            print(f"[TEST]: {name} {i+test_obj.t4.min_value+1}")

def _test_bytestring() -> None:
    mem = memoryview(bytearray(10))
    mem[:1] = mem[-1:] = b"\xff"
    bs = ByteString(mem[1:-1], loffset=0, roffset=0, size=64)
    assert bs.value == "", "TestError"
    assert bs.value == bs.get(), "TestError"
    bs.set("abc")
    assert bs.value == "abc", "TestError"
    assert bs.value == bs.get(), "TestError"
    bs.set("12345678")
    assert bs.value == "12345678", "TestError"
    assert bs.value == bs.get(), "TestError"
    assert bytes(mem) == b"\xff12345678\xff", "TestError"


def _test() -> None:
    global all_tests, max_test_values, get_States, randint, seed, test_obj

    from random import randint, seed
    seed(43)

    class Test(Struct):
        _fields_ = [
                     ("t1", 4*BYTE, ByteArray),
                     ("",    2*BIT, Padding),
                     ("t2",  8*BIT, BitArray),
                     ("t3",  8*BIT, BitArray),
                     ("t4",  6*BIT, UInt),
                     ("t5",  2*BIT, BitArray),
                     ("t6",  6*BIT, Int),
                   ]
    memview:memoryview = memoryview(bytearray((sizeof(Test)._size()+7)>>3))
    test_obj = Test(memview, force_no_chk=True)

    all_tests = [test_obj.t1, test_obj.t2, test_obj.t3, test_obj.t5]
    max_test_values = [255,1,1,1]
    get_states = lambda: [[int(all_tests[j][i]) for i in range(len(test))]
                                           for j, test in enumerate(all_tests)]

    _test_bytestring()
    _test_containers(get_states, n=100_000)

    get_t3_state = lambda: [test_obj.t3[i] for i in range(len(test_obj.t3))]
    get_t5_state = lambda: [test_obj.t5[i] for i in range(len(test_obj.t5))]
    _test_int("t4", get_states, "uint")
    _test_int("t6", get_states, "int")


if (__name__ == "__main__") and TEST:
    test()


if __name__ == "__main__":
    class MyField(Struct):
        _fields_ = [
                     ("field1", BYTE,  Int),
                     ("field2", BYTE, UInt),
                   ]
    class Test(Struct):
        _fields_ = [
                     ("t1", 5*MyField, Array(5,MyField)),
                   ]
    data:bytearray = bytearray(sizeof(Test)._size()>>3)
    memview:memoryview = memoryview(data)
    test_obj:Test = Test(memview, force_no_chk=True)