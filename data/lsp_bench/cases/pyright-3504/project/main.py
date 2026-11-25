from typing import Any, Callable, Generic, TypeVar, overload

T = TypeVar("T")
T2 = TypeVar("T2")

class C:
    ...

class Gen(Generic[T]):
    @overload
    def method(self, v: Callable[[], int]) -> "Gen[int]":
        ...

    @overload
    def method(self, v: Callable[[], T2]) -> "Gen[T2]":
        ...

    def method(self, v: Any) -> Any:
        ...

    def method2(self: "Gen[list[C]]") -> Any:
        ...

g = (
    Gen[None]()
    .method(lambda: second_func())
    .method2()  # error here
)

def second_func() -> list[C]:
    ...
