import functools
from typing import Callable, Generic, TypeVar, Union

from typing_extensions import ParamSpec

_TResult = TypeVar("_TResult")
_P = ParamSpec("_P")


class TailCall(Generic[_P]):
    def __init__(self, *args: _P.args, **kw: _P.kwargs):
        self.args = args
        self.kw = kw


TailCallResult = Union[_TResult, TailCall[_P]]


def tailrec(fn: Callable[_P, TailCallResult[_TResult, _P]]) -> Callable[_P, _TResult]:
    def trampoline(bouncer: TailCallResult[_TResult, _P]) -> _TResult:
        while isinstance(bouncer, TailCall):
            args, kw = bouncer.args, bouncer.kw
            bouncer = fn(*args, **kw)

        return bouncer

    @functools.wraps(fn)
    def wrapper(*args: _P.args, **kw: _P.kwargs) -> _TResult:
        return trampoline(fn(*args, **kw))

    return wrapper
