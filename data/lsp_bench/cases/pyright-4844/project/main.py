from __future__ import annotations

from typing import Protocol
from typing_extensions import Self

class Negatable(Protocol):
    def __neg__(self) -> Self: ...

def f(x: Negatable) -> None: ...

f(0)  # This fails.
f(int(0))
f(0)  # This passes.
