# [pyright 1.1.414] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `pyright-r3-definitionconsistency-lost-d-a4eaed`, signature `pyright|r3_routes|definitionConsistency:lost`, case family `d`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `D4Vinci/Scrapling@08f107b1240f` (corpus, commit 08f107b1240fd72847b0f5e10426c7e6cc16e67e), language python

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `tests/parser/test_attributes_handler.py` at line 305, column 20 (LSP position {line: 304, character: 19}) gives the expected set; didOpen `scrapling/__init__.py` and `textDocument/definition` at the reference line 24, column 17 (LSP position {line: 23, character: 16}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "scrapling/parser.py",
  76,
  6,
  76,
  14
 ]
]
```

Actual:

```json
[]
```

Project file `scrapling/__init__.py`:

```
   1 | __author__ = "Karim Shoair (karim.shoair@pm.me)"
   2 | __version__ = "0.4.15"
   3 | __copyright__ = "Copyright (c) 2024 Karim Shoair"
     ...
   5 | from typing import Any, TYPE_CHECKING
     ...
   7 | if TYPE_CHECKING:
   8 |     from scrapling.parser import Selector, Selectors
   9 |     from scrapling.core.custom_types import AttributesHandler, TextHandler
  10 |     from scrapling.fetchers import Fetcher, AsyncFetcher, StealthyFetcher, DynamicFetcher
     ...
  13 | # Lazy import mapping
  14 | _LAZY_IMPORTS = {
  15 |     "Fetcher": ("scrapling.fetchers", "Fetcher"),
  16 |     "Selector": ("scrapling.parser", "Selector"),
  17 |     "Selectors": ("scrapling.parser", "Selectors"),
  18 |     "AttributesHandler": ("scrapling.core.custom_types", "AttributesHandler"),
  19 |     "TextHandler": ("scrapling.core.custom_types", "TextHandler"),
  20 |     "AsyncFetcher": ("scrapling.fetchers", "AsyncFetcher"),
  21 |     "StealthyFetcher": ("scrapling.fetchers", "StealthyFetcher"),
  22 |     "DynamicFetcher": ("scrapling.fetchers", "DynamicFetcher"),
  23 | }
  24 | __all__ = ["Selector", "Fetcher", "AsyncFetcher", "StealthyFetcher", "DynamicFetcher"]
     ...
  27 | def __getattr__(name: str) -> Any:
  28 |     if name in _LAZY_IMPORTS:
  29 |         module_path, class_name = _LAZY_IMPORTS[name]
  30 |         module = __import__(module_path, fromlist=[class_name])
  31 |         return getattr(module, class_name)
  32 |     else:
  33 |         raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
     ...
  36 | def __dir__() -> list[str]:
  37 |     """Support for dir() and autocomplete."""
  38 |     return sorted(__all__ + ["fetchers", "parser", "cli", "core", "__author__", "__version__", "__copyright__"])
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r3-definitionconsistency-lost-d-a4eaed/repro.json
```

## Evidence and reduction

- representative 0f7d1b71b1a8-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects D4Vinci/Scrapling@08f107b1240f, browser-use/browser-use@d8110c5ff87c, hiyouga/LlamaFactory@97b32d3133b5, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#795](https://github.com/microsoft/pyright/issues/795) Go To Definition jumps to source rather than typeshed stubs (closed, 2020-07-06, 13 comments)
- [microsoft/pyright#6041](https://github.com/microsoft/pyright/issues/6041) Is it possible to implement Go to definition inside Doc-strings or comments? (closed, 2023-09-29, 3 comments)
- [microsoft/pyright#3201](https://github.com/microsoft/pyright/issues/3201) Wrong behavior going to definition on 3rd party libraries (closed, 2022-03-15, 6 comments)
- [microsoft/pyright#11470](https://github.com/microsoft/pyright/issues/11470) Pyright is incorrectly handling overload functions (closed, 2026-05-28, 3 comments)
- [microsoft/pyright#10845](https://github.com/microsoft/pyright/issues/10845) Methods of a variadic generic class become uncallable when specified with TypeVarTuple and a suffix (closed, 2025-08-25, 1 comments)
- [microsoft/pyright#3968](https://github.com/microsoft/pyright/issues/3968) Pyright reports reportMissingSuperCall in a class that is not a subclass (closed, 2022-09-20, 8 comments)
- [microsoft/pyright#3013](https://github.com/microsoft/pyright/issues/3013) Strict Setting for Return Types (closed, 2022-02-09, 22 comments)
- [microsoft/pyright#6237](https://github.com/microsoft/pyright/issues/6237) reportUnsupportedDunderAll does not consider submodule names in __all__ (closed, 2023-10-26, 6 comments)
- queries: `"go to definition" in:title repo:microsoft/pyright is:issue`; `definition missing repo:microsoft/pyright is:issue`; `definition "go to definition" repo:microsoft/pyright is:issue`; `definition inconsistent repo:microsoft/pyright is:issue`
