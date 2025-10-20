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
    * int, float, bool, None
    * list, dict, tuple, set, frozenset, bytes, bytearray
    * complex, range, slice

This module defines `dumps` and `loads` functions like the json library. It
also defines `enc_dumps` and `enc_loads` which work with `bytes` instead of
`str` using the "utf-8" encoding.

Issues:
    * It detects circular references by catching `RecursionError`s in `dumps`
    * Not very memory efficient for a lot of objects with a lot of references
        but it's perfectly good enough for lists of ints/floats/strings but
        it should be compressable by zlib or gzip
    * It has the same speed restrictions as the built-in json library
    * It is very hard to read the encoded data as a human (too many \\s)
"""
from __future__ import annotations
from base64 import b64encode, b64decode
from typing import TypeVar, Callable
import json


T:type = TypeVar("T")
Serialiser:type = Callable[T,dict]
Deserialiser:type = Callable[dict,T]


class DoubleDict:
    def __init__(self) -> None:
        self.val:dict = {}
        self.rev:dict = {}
        self.get = self.val.get
        self.__getitem__ = self.val.get
        self.reverse_get = self.rev.get

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
        # Gets overwritten in `__init__`
        pass

    def get(self, key:object, *default:tuple[object]) -> object:
        # Gets overwritten in `__init__`
        pass

    def __getitem__(self, key:object) -> object:
        # Gets overwritten in `__init__`
        pass


def _dumps(obj:object, **kwargs:dict) -> str:
    if type(obj) in (str, bool, type(None), int, float, list, dict):
        return _dumps_builtin_types(obj, **kwargs)
    serialiser:Serialiser = _serialisers.get(type(obj), None)
    typename:str = _typenames.get(type(obj), None)
    data:dict = serialiser(obj, **kwargs)
    if not isinstance(data, dict):
        raise TypeError("Serialiser must return a dict")
    new:dict = {}
    for key, value in data.items():
        if isinstance(key, str) and key.endswith("class"):
            key:str = f"_{key}"
        new[key] = value
    return _dumps_builtin_types(new | {"class":typename})

def _dumps_builtin_types(obj:object, **kwargs:dict) -> str:
    if type(obj) in (str, bool, type(None), int, float):
        return json.dumps(obj)
    if type(obj) == list:
        output:str = "["
        for value in obj:
            output += _dumps(value, **kwargs) + ", "
        return output.removesuffix(", ")+"]"
    if type(obj) == dict:
        output:str = "{"
        for key, value in obj.items():
            if key != "class":
                key:str = _dumps(key, **kwargs)
            key:str = json.dumps(key)
            value:object = _dumps(value, **kwargs)
            output += f"{key}: {value}, "
        return output.removesuffix(", ")+"}"
    raise TypeError(f"Unknown type {obj.__class__.__name__}")

def _loads(obj:object, **kwargs:dict) -> object:
    if isinstance(obj, dict):
        new:dict = {}
        typename:str = None
        for key, value in obj.items():
            if key == "class":
                typename:str = value
                continue
            key:object = json.loads(key)
            key:object = _loads(key, **kwargs)
            value:object = _loads(value, **kwargs)
            if isinstance(key, str) and key.endswith("class"):
                key:str = key.removeprefix("_")
            new[key] = value
        if typename is None:
            raise ValueError("class missing from dict")
        return _load_object(new, typename, **kwargs)
    elif isinstance(obj, list):
        new:list = []
        for value in obj:
            value:object = _loads(value)
            if isinstance(value, dict) and ("class" in value):
                value:dict = _load_object(value)
            new.append(value)
        return new
    else:
        return obj

def _load_object(data:dict, typename:str, **kwargs:dict) -> object:
    if typename != "dict":
        T:type = _typenames.reverse_get(typename, None)
        if T is None:
            raise ValueError(f"Missing deserialiser for {typename}")
        return _deserialisers[T](data, **kwargs)
    return data


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
    def ident(x:object, **kwargs:dict) -> object:
        return x

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

    import signal
    register(signal.Signals, "signal.Signals", val_type_to_json(int),
             json_to_val_type(signal.Signals))


if __name__ == "__main__":
    class MyClass:
        def __init__(self, attr:object) -> MyClass:
            self.attr:object = attr

        def serialise(self, **kwargs:dict) -> dict:
            return {"attr":self.attr}

        def __repr__(self) -> str:
            return f"MyClass({self.attr!r})"

        @classmethod
        def deserialise(self, data:dict, **kwargs:dict) -> MyClass:
            return MyClass(data.pop("attr"))

    register(MyClass, "MyClass", MyClass.serialise, MyClass.deserialise)

    # data:object = [b"\x00", MyClass(5.6)]
    data:object = {"class":MyClass(b"abc")}
    # data:object = {1:1, "class":0}
    data:object = [i for i in range(10)]
    serialised:str = dumps(data)
    data:object = loads(serialised)
    print(repr(data))
