# [pyright 1.1.414] hover shows a different text after file rename round trip

Draft for the author (not filed). Group `pyright-r1-hover-text-h5-f24c4e`, signature `pyright|r1_history|hover:text`, case family `H5`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `scrapy/scrapy@91d87364637c` (corpus, commit 91d87364637c1b18fd5bb21d1ed3bb356cf9b6fc), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename scrapy/utils/versions.py -> scrapy/utils/versions_rt.py`
3. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename scrapy/utils/versions_rt.py -> scrapy/utils/versions.py`
4. Timing: wait until the server is idle after every step.
5. textDocument/didOpen `scrapy/utils/versions.py`, `tests/test_feedexport.py`, `tests/test_pipelines.py` (the query step opens every target file that is not open), then wait until the server is idle.
6. Query `textDocument/hover` on `scrapy/utils/versions.py` line 7, column 12 (LSP position {line: 6, character: 11}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "(function) def warn( message: str, category: type[Warning] | None = None, stacklevel: int = 1, source: Any | None = None, *, skip_file_prefixes: tuple[str, ...] = () ) -> None --- Issue a warning, or maybe ignore it or raise an exception.",
 [
  6,
  9,
  6,
  13
 ]
]
```

Actual:

```json
[
 "(function) def warn( message: str, category: type[Warning] | None = None, stacklevel: int = 1, source: Any | None = None, *, skip_file_prefixes: tuple[str, ...] = () ) -> None",
 [
  6,
  9,
  6,
  13
 ]
]
```

Project file `scrapy/utils/versions.py`:

```
   1 | # pragma: no file cover
   2 | import warnings
     ...
   4 | from scrapy.exceptions import ScrapyDeprecationWarning
   5 | from scrapy.utils._versions import get_versions
     ...
   7 | warnings.warn(
   8 |     "The scrapy.utils.versions module is deprecated.",
   9 |     ScrapyDeprecationWarning,
  10 |     stacklevel=2,
  11 | )
     ...
  13 | __all__ = [
  14 |     "get_versions",
  15 | ]
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-hover-text-h5-f24c4e/repro.json
```

## Evidence and reduction

- representative 08417dd958ba-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 2 (7 probes, 107.32 s, reduced ops confirmed 3/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects scrapy/scrapy@91d87364637c, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#375](https://github.com/microsoft/pyright/issues/375) rename symbol only seems to apply to open files (closed, 2019-11-28, 7 comments)
- [microsoft/pyright#11317](https://github.com/microsoft/pyright/issues/11317) LSP: Slow semantic completion for built in types (closed, 2026-03-06, 2 comments)
- [microsoft/pyright#10534](https://github.com/microsoft/pyright/issues/10534) How do I wrap functions in a class with a __call__ method while preserving both types and docstrings? (closed, 2025-06-03, 3 comments)
- [microsoft/pyright#1118](https://github.com/microsoft/pyright/issues/1118) reportUnusedVariable ignore pattern (closed, 2020-10-23, 116 comments)
- [microsoft/pyright#10229](https://github.com/microsoft/pyright/issues/10229) Variance check is inconsistent (closed, 2025-03-31, 3 comments)
- [microsoft/pyright#9605](https://github.com/microsoft/pyright/issues/9605) 2 different overloads are incorrectly considered equivalent (closed, 2024-12-19, 5 comments)
- [microsoft/pyright#4513](https://github.com/microsoft/pyright/issues/4513) Type of "xstate" could not be determined because it refers to itself (closed, 2023-01-23, 11 comments)
- [microsoft/pyright#588](https://github.com/microsoft/pyright/issues/588) separate X.pyi file does not get imported besides X.py (closed, 2020-03-26, 6 comments)
- queries: `"rename file" in:title repo:microsoft/pyright is:issue`; `hover wrong repo:microsoft/pyright is:issue`; `hover "rename file" repo:microsoft/pyright is:issue`; `hover stale repo:microsoft/pyright is:issue`
