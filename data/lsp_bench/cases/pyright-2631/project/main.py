from typing import Union
from dataclasses import dataclass, field


@dataclass
class Foo:
    foo: str


@dataclass
class Bar:
    bar: str
    baz: dict[str, str] = field(default_factory=dict)


FooBar = Union[Foo, Bar]


def do_stuff(foobar: FooBar) -> None:
    while foobar:
        if isinstance(foobar, Foo):
            pass
        elif foobar.bar == "bar" and "baz" in foobar.baz:
            return
