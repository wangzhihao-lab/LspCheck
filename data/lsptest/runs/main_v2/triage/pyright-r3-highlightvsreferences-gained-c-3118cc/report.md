# [pyright 1.1.414] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `pyright-r3-highlightvsreferences-gained-c-3118cc`, signature `pyright|r3_routes|highlightVsReferences:gained`, case family `c`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `scrapy/scrapy@91d87364637c` (corpus, commit 91d87364637c1b18fd5bb21d1ed3bb356cf9b6fc), language python

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `tests/utils/decorators.py` at line 70, column 28 (LSP position {line: 69, character: 27}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  34,
  32,
  34,
  36
 ],
 [
  34,
  41,
  34,
  45
 ],
 [
  35,
  57,
  35,
  61
 ],
 [
  43,
  9,
  43,
  13
 ],
 [
  43,
  18,
  43,
  22
 ],
 [
  45,
  18,
  45,
  22
 ],
 [
  69,
  25,
  69,
  29
 ]
]
```

Project file `tests/utils/decorators.py`:

```
   1 | from __future__ import annotations
     ...
   3 | from functools import wraps
   4 | from typing import TYPE_CHECKING, Any, ParamSpec
     ...
   6 | import pytest
   7 | from twisted.internet.defer import Deferred, inlineCallbacks
     ...
   9 | from scrapy.utils.defer import deferred_from_coro, deferred_to_future
  10 | from scrapy.utils.reactor import is_reactor_installed
     ...
  12 | if TYPE_CHECKING:
  13 |     from collections.abc import Awaitable, Callable, Generator
     ...
  16 | _P = ParamSpec("_P")
     ...
  19 | def inline_callbacks_test(
  20 |     f: Callable[_P, Generator[Deferred[Any], Any, None]],
  21 | ) -> Callable[_P, Awaitable[None]]:
  22 |     """Mark a test function written in a :func:`twisted.internet.defer.inlineCallbacks` style.
     ...
  24 |     This calls :func:`twisted.internet.defer.inlineCallbacks` and then:
     ...
  26 |     * with ``pytest-twisted`` this returns the resulting Deferred
  27 |     * with ``pytest-asyncio`` this converts the resulting Deferred into a
  28 |       coroutine
  29 |     """
     ...
  31 |     if not is_reactor_installed():
     ...
  33 |         @pytest.mark.asyncio
  34 |         @wraps(f)
  35 |         async def wrapper_coro(*args: _P.args, **kwargs: _P.kwargs) -> None:
  36 |             await deferred_to_future(inlineCallbacks(f)(*args, **kwargs))
     ...
  38 |         # Likely https://github.com/python/mypy/issues/17171
  39 |         return wrapper_coro  # type: ignore[no-any-return]
     ...
  41 |     @wraps(f)
  42 |     @inlineCallbacks
  43 |     def wrapper_dfd(
  44 |         *args: _P.args, **kwargs: _P.kwargs
  45 |     ) -> Generator[Deferred[Any], Any, None]:
  46 |         return f(*args, **kwargs)
     ...
  48 |     return wrapper_dfd
     ...
  51 | def coroutine_test(
  52 |     coro_f: Callable[_P, Awaitable[None]],
  53 | ) -> Callable[_P, Awaitable[None]]:
  54 |     """Mark a test function that returns a coroutine.
     ...
  56 |     * with ``pytest-twisted`` this converts a coroutine into a
  57 |       :class:`twisted.internet.defer.Deferred`
  58 |     * with ``pytest-asyncio`` this is a no-op
     ...
  60 |     In addition to handling asynchronous test functions this can also be used
  61 |     to mark "synchronous" test functions (they still need to be made
  62 |     ``async def``) that call code that needs a reactor or a running event loop,
  63 |     so that ``pytest-asyncio`` starts a loop for them too.
  64 |     """
     ...
  66 |     if not is_reactor_installed():
  67 |         return pytest.mark.asyncio(coro_f)
     ...
  69 |     @wraps(coro_f)
  70 |     def f(*coro_args: _P.args, **coro_kwargs: _P.kwargs) -> Deferred[None]:
  71 |         return deferred_from_coro(coro_f(*coro_args, **coro_kwargs))
     ...
  73 |     return f
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r3-highlightvsreferences-gained-c-3118cc/repro.json
```

## Evidence and reduction

- representative 2d8bb2d806d3-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects karpathy/nanochat@92d63d4e8bb4, scrapy/scrapy@91d87364637c, ultralytics/yolov5@402e17ddf820, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#10818](https://github.com/microsoft/pyright/issues/10818) why lsp progress keep showing find references (closed, 2025-08-19, 1 comments)
- [microsoft/pyright#10086](https://github.com/microsoft/pyright/issues/10086) Pyright LSP Returns Incomplete References Without Explicit didOpen for All Files (closed, 2025-03-14, 5 comments)
- [microsoft/pyright#9538](https://github.com/microsoft/pyright/issues/9538) Symlinks are not taken into account with "find references" (closed, 2024-12-03, 2 comments)
- [microsoft/pyright#8047](https://github.com/microsoft/pyright/issues/8047) Pyright runs forever on an identity function being called with a tuple containing two references of itself as argument (closed, 2024-06-02, 1 comments)
- [microsoft/pyright#7763](https://github.com/microsoft/pyright/issues/7763) Incorrect type when `Enum` member references other `Enum` member in initalization (closed, 2024-04-25, 2 comments)
- [microsoft/pyright#10087](https://github.com/microsoft/pyright/issues/10087) Currently no error when poping a Required key from a TypedDict & still return correct type. (closed, 2025-03-14, 3 comments)
- [microsoft/pyright#2035](https://github.com/microsoft/pyright/issues/2035) Explicitly choose a Pyright version when using it with the VS Code Python Extension (closed, 2021-06-26, 19 comments)
- [microsoft/pyright#9642](https://github.com/microsoft/pyright/issues/9642) Running pyright on a full workspace does not seem to report all existing errors. (closed, 2024-12-29, 13 comments)
- queries: `references in:title repo:microsoft/pyright is:issue`; `highlight unexpected repo:microsoft/pyright is:issue`; `highlight references repo:microsoft/pyright is:issue`; `highlight inconsistent repo:microsoft/pyright is:issue`
