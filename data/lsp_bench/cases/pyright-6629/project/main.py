from dataclasses import dataclass
from typing import Union


FooBar = Union["Foo","Bar"]

@dataclass
class _Base0:
    def __invert__(self) -> bool:
        ...
    def __add__(self, other: FooBar) -> FooBar:
        ...

@dataclass
class _Base1(_Base0):
    v: FooBar # Union["Foo","Bar"]

@dataclass
class Foo(_Base0): pass

@dataclass
class Bar(_Base1): pass


def check(w: FooBar):
    match w:
        case Bar(v):
            print(v + v)          # ok
            print(v.__invert__()) # ok
            print(~v)             # Operator "~" not supported for type "FooBar" when expected type is "object
        case _:
            pass
