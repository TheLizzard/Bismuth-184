"""
A serialiser and deserialiser that works with any object that is registered
with it. It's built on top of JSON and isn't very memory efficient but
it has no security problems like pickle and can serialise any objects
not just the [list,dict,bool,null,int,float] in JSON.

This modules fixes the problem with `json` where multiple things get encoded
to the same result (because in JSON, dictionary keys must be strings):
    >>> json.dumps({None:0}) == json.dumps({"null":0})
    True
    >>> json.dumps({0:0}) == json.dumps({"0":0})
    True

To register a custom class use the `register` function which takes the type,
typename, serialiser and deserialiser. The typename must be unique for every
class registered and must correspond to a type.

Example with a custom class:
```python
class MyClass:
    def __init__(self, attr:object) -> MyClass:
        self.attr:object = attr
    def serialise(self, **kwargs:dict) -> dict:
        return {"attr":self.attr}
    @classmethod
    def deserialise(self, data:dict, **kwargs:dict) -> MyClass:
        return MyClass(data.pop("attr"))

register(MyClass, "MyClass", MyClass.serialise, MyClass.deserialise)
```

The classes registered on import are:
    * int, float, bool, None, Ellipsis
    * list, dict, tuple, set, frozenset, bytes, bytearray
    * complex, range, slice
    * signal.Signals

This module defines `dumps` and `loads` functions like the json library. It
also defines `enc_dumps` and `enc_loads` which work with `bytes` instead of
`str` using the "utf-8" encoding.

Issues:
    * It detects circular references by catching `RecursionError`s in `dumps`.
        This is a problem since https://github.com/python/cpython/issues/132744
    * Not very memory efficient for a lot of objects with a lot of references
        but it's perfectly good enough for lists of ints/floats/strings but
        it should be compressable by zlib or gzip
    * It has the same speed restrictions as the built-in json library
    * It is very hard to read the encoded data as a human (too many backslashes)
"""
from __future__ import annotations
from base64 import b64encode, b64decode
from typing import TypeVar, Callable
import json


T:type = TypeVar("T")
Serialiser:type = Callable[T,dict]
Deserialiser:type = Callable[dict,T]


class DoubleDict:
    __slots__ = "val", "rev"

    def __init__(self) -> None:
        self.val:dict = {}
        self.rev:dict = {}

    def __setitem__(self, key:object, value:object) -> None:
        self.val[key] = value
        self.rev[value] = key

    def pop(self, key:object) -> object:
        value:object = self.val.pop(key)
        self.rev.pop(value)
        return value

    def reverse_pop(self, value:object) -> object:
        key:object = self.rev.pop(value)
        self.val.pop(key)
        return key

    def reverse_get(self, key:object, *default:tuple[object]) -> object:
        return self.rev.get(key, *default)

    def get(self, key:object, *default:tuple[object]) -> object:
        return self.val.get(key, *default)

    def __getitem__(self, key:object) -> object:
        return self.val.get(key)


def _dumps(obj:object, **kwargs:dict) -> str:
    if type(obj) in (str, bool, type(None), int, float):
        return json.dumps(obj)
    elif type(obj) == list:
        # Serialise a list
        output:str = "["
        for value in obj:
            output += _dumps(value, **kwargs) + ", "
        return output.removesuffix(", ") + "]"
    else:
        # Get the correct serialiser
        serialiser:Serialiser = _serialisers.get(type(obj), None)
        if serialiser is None:
            raise TypeError(f"No serialisation method registered for "\
                            f"{type(obj).__qualname__}")
        # Get the typename and serialise the data
        typename:str = _typenames.get(type(obj), None)
        data:dict = serialiser(obj, **kwargs)
        if not isinstance(data, dict):
            raise TypeError("Serialiser must return a dict")
        # Serialise the dict output from the serialiser
        output:str = f'{{"class":{json.dumps(typename)}, '
        for key, value in data.items():
            new_key:str = json.dumps(_dumps(key, **kwargs))
            new_value:str = _dumps(value, **kwargs)
            output += f"{new_key}:{new_value}, "
        return output.removesuffix(", ") + "}"

def _loads(obj:object, **kwargs:dict) -> object:
    if isinstance(obj, dict):
        typename:str|None = obj.get("class", None)
        if typename is None:
            raise ValueError('"class" key missing')
        new:dict = {_loads(json.loads(key)):_loads(value, **kwargs)
                    for key, value in obj.items() if key != "class"}
        return _load_object(new, typename, **kwargs)
    elif isinstance(obj, list):
        return list(map(_loads, obj))
    else:
        return obj

def _load_object(data:dict, typename:str, **kwargs:dict) -> object:
    assert isinstance(typename, str), "TypeError"
    if typename == "dict":
        return data
    else:
        T:type = _typenames.reverse_get(typename, None)
        if T is None:
            raise ValueError(f"Missing deserialiser for {typename}")
        return _deserialisers[T](data, **kwargs)


def dumps(obj:object, **kwargs:dict) -> str:
    try:
        return _dumps(obj, **kwargs)
    except RecursionError:
        pass
    raise ValueError("Circular reference detected")

def enc_dumps(obj:object, **kwargs:dict) -> bytes:
    return dumps(obj, **kwargs).encode("utf-8")

def loads(data:str, **kwargs:dict) -> object:
    return _loads(json.loads(data), **kwargs)

def enc_loads(data:object, **kwargs:dict) -> bytes:
    return loads(data.decode("utf-8"), **kwargs)


_typenames:dict[type:str] = DoubleDict()
_serialisers:dict[type:Serialiser] = {}
_deserialisers:dict[type:Deserialiser] = {}
def register(T:type, name:str, serialiser:Serialiser,
             deserialiser:Deserialiser) -> None:
    assert isinstance(name, str), "typename must be a string"
    assert isinstance(T, type), "the first argument must be a type"
    assert callable(serialiser), "serialiser must be callable"
    assert callable(deserialiser), "deserialiser must be callable"
    if _typenames.reverse_get(T, name) != name:
        raise ValueError("2 Different types with same name")
    _typenames[T] = name
    _serialisers[T] = serialiser
    _deserialisers[T] = deserialiser


@lambda f: f()
def _register_builtins() -> None:
    def ident(obj:object) -> object:
        return obj

    def val_type_to_json(T:type) -> Serialiser:
        def inner(value:object, **kwargs:dict) -> dict:
            return {"v": T(value)}
        return inner
    def json_to_val_type(T:type) -> Deserialiser:
        def inner(data:dict, **kwargs:dict) -> T:
            return T(data["v"])
        return inner

    def complex_to_json(x:complex, **kwargs:dict) -> dict:
        return {"r": x.real, "i": x.imag}
    def json_to_complex(data:dict, **kwargs:dict) -> complex:
        return complex(data["r"], data["i"])

    def bytes_to_json(b:bytes, **kwargs) -> dict:
        return {"v": b64encode(b).decode("ascii")}
    def json_to_bytes(data:dict, **kwargs:dict) -> bytes:
        return b64decode(data["v"])

    def triplet_to_json(triplet:T, **kwargs:dict) -> dict:
        return {"v": [triplet.start, triplet.stop, triplet.step]}
    def json_to_triplet(T:type) -> Deserialiser:
        def inner(data:dict, **kwargs:dict) -> T:
            return T(*data["v"])
        return inner

    def ellipsis_to_json(ellipsis:Ellipsis, **kwargs:dict) -> dict:
        return {}
    def json_to_ellipsis(data:dict, **kwargs:dict) -> Ellipsis:
        return Ellipsis

    register(dict, "dict", ident, ident)
    register(set, "set", val_type_to_json(list), json_to_val_type(set))
    register(tuple, "tuple", val_type_to_json(list), json_to_val_type(tuple))
    register(bytearray, "bytearray", val_type_to_json(list),
             json_to_val_type(bytearray))
    register(frozenset, "frozenset", val_type_to_json(list),
             json_to_val_type(frozenset))
    register(bytes, "bytes", bytes_to_json, json_to_bytes)
    register(complex, "complex", complex_to_json, json_to_complex)
    register(range, "range", triplet_to_json, json_to_triplet(range))
    register(slice, "slice", triplet_to_json, json_to_triplet(slice))
    register(type(Ellipsis), "Ellipsis", ellipsis_to_json, json_to_ellipsis)

    import signal
    register(signal.Signals, "signal.Signals", val_type_to_json(int),
             json_to_val_type(signal.Signals))


if __name__ == "__main__":
    class MyClass:
        __slots__ = "attr"

        def __init__(self, attr:object) -> MyClass:
            self.attr:object = attr

        def serialise(self, **kwargs:dict) -> dict:
            return {"attr":self.attr}

        def __repr__(self) -> str:
            return f"MyClass({self.attr!r})"

        def __eq__(self, other:object) -> bool:
            return repr(self) == repr(other)

        @classmethod
        def deserialise(self, data:dict, **kwargs:dict) -> MyClass:
            return MyClass(data.pop("attr"))

    register(MyClass, "MyClass", MyClass.serialise, MyClass.deserialise)

    TESTS:list[object] = [
        # Test numbers
        1, 1.1, 1.0,
        # Test strings/bytes
        "Hello", "class", b"Hello world", b"class",
        # Test dictionaries
        {}, {"class":-1}, {"class":-1, "a":"b"}, {"a":"class",1:2}, {"a":"b"},
        # Test sets
        set(), {1}, {"a"}, {"class"}, {"a","class"},
        # Test lists
        [], [1], ["class"], [1,2,"class"], list(range(10)),
        # Test True, False, None, Ellipsis
        True, False, None, Ellipsis,
        # Test tuples
        (), ("a",), ("class",), ("a","b"), ("a","class"),
        # Test complex
        (1+0j), (0+5j),
        # Test range
        range(-1,5,1),
        # Test custom classes
        MyClass(5.6), MyClass("class"),
        # Test combinations of custom classes and other objects
        [b"\x00",MyClass(5.6)], [b"\x00",MyClass(b"abc")],
        {"class":MyClass(b"abc")},
    ]

    failed_any_tests:bool = False
    failed:bool = False
    for obj in TESTS:
        if failed: print("-"*20)
        failed:bool = False
        try:
            serialised:str = dumps(obj)
        except:
            print(f"Serialiser errored on {obj!r}")
            failed_any_tests:bool = True
            continue
        try:
            data:object = loads(serialised)
        except:
            print(f"Deserialiser errored on {obj!r}")
            failed_any_tests:bool = True
            continue
        if type(obj) != type(data):
            failed:bool = True
        elif obj != data:
            failed:bool = True
        if failed:
            failed_any_tests:bool = True
            print(f"Serialiser+Deserialiser didn't work on {obj!r}")
            print(f"Serialised data: {serialised!r}")
            print(f"Deserialised data: {data}")
    if failed_any_tests:
        print("-"*20)
        print("Tests: \x1b[91mFailed\x1b[0m")
    else:
        print("Tests: \x1b[92mPassed\x1b[0m")
