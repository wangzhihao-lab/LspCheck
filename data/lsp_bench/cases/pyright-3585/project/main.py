from dataclasses import dataclass
from typing import Protocol

class P1(Protocol):
    x: int

class P2(Protocol):
    y: P1

@dataclass
class A:
    x: int

@dataclass
class B:
    y: A

y: P1 = A(3)
x: P2 = B(A(3))
