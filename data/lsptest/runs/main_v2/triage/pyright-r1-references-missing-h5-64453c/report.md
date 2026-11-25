# [pyright 1.1.414] references misses entries after file rename round trip

Draft for the author (not filed). Group `pyright-r1-references-missing-h5-64453c`, signature `pyright|r1_history|references:missing`, case family `H5`.

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
6. Query `textDocument/references` on `scrapy/utils/versions.py` line 10, column 10 (LSP position {line: 9, character: 9}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_warnings.pyi",
  12,
  8,
  12,
  18
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/_py_warnings.py",
  442,
  33,
  442,
  43
 ],
 [
  "scrapy/commands/__init__.py",
  65,
  16,
  65,
  26
 ],
 [
  "scrapy/commands/__init__.py",
  72,
  12,
  72,
  22
 ],
 [
  "scrapy/commands/__init__.py",
  98,
  12,
  98,
  22
 ],
 [
  "scrapy/contracts/__init__.py",
  180,
  20,
  180,
  30
 ],
 [
  "scrapy/core/downloader/__init__.py",
  80,
  16,
  80,
  26
 ],
 [
  "scrapy/core/downloader/__init__.py",
  96,
  12,
  96,
  22
 ],
 [
  "scrapy/core/downloader/__init__.py",
  105,
  12,
  105,
  22
 ],
 [
  "scrapy/core/downloader/__init__.py",
  153,
  8,
  153,
  18
 ],
 [
  "scrapy/core/downloader/__init__.py",
  172,
  12,
  172,
  22
 ],
 [
  "scrapy/core/downloader/__init__.py",
  214,
  12,
  214,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  209,
  12,
  209,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  299,
  12,
  299,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  308,
  12,
  308,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  329,
  8,
  329,
  18
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  110,
  24,
  110,
  34
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  136,
  16,
  136,
  26
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  147,
  12,
  1
... (8994 characters)
```

Actual:

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/_warnings.pyi",
  12,
  8,
  12,
  18
 ],
 [
  "scrapy/commands/__init__.py",
  65,
  16,
  65,
  26
 ],
 [
  "scrapy/commands/__init__.py",
  72,
  12,
  72,
  22
 ],
 [
  "scrapy/commands/__init__.py",
  98,
  12,
  98,
  22
 ],
 [
  "scrapy/contracts/__init__.py",
  180,
  20,
  180,
  30
 ],
 [
  "scrapy/core/downloader/__init__.py",
  80,
  16,
  80,
  26
 ],
 [
  "scrapy/core/downloader/__init__.py",
  96,
  12,
  96,
  22
 ],
 [
  "scrapy/core/downloader/__init__.py",
  105,
  12,
  105,
  22
 ],
 [
  "scrapy/core/downloader/__init__.py",
  153,
  8,
  153,
  18
 ],
 [
  "scrapy/core/downloader/__init__.py",
  172,
  12,
  172,
  22
 ],
 [
  "scrapy/core/downloader/__init__.py",
  214,
  12,
  214,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  209,
  12,
  209,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  299,
  12,
  299,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  308,
  12,
  308,
  22
 ],
 [
  "scrapy/core/downloader/contextfactory.py",
  329,
  8,
  329,
  18
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  110,
  24,
  110,
  34
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  136,
  16,
  136,
  26
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  147,
  12,
  147,
  22
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  175,
  20,
  175,
  30
 ],
 [
  "scrapy/core/downloader/handlers/__init__.py",
  18
... (8844 characters)
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-references-missing-h5-64453c/repro.json
```

## Evidence and reduction

- representative 08417dd958ba-v03: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 2 (7 probes, 109.348 s, reduced ops confirmed 3/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects scrapy/scrapy@91d87364637c, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#375](https://github.com/microsoft/pyright/issues/375) rename symbol only seems to apply to open files (closed, 2019-11-28, 7 comments)
- [microsoft/pyright#3075](https://github.com/microsoft/pyright/issues/3075) Lazy analysis for LSP (closed, 2022-02-18, 6 comments)
- [microsoft/pyright#10086](https://github.com/microsoft/pyright/issues/10086) Pyright LSP Returns Incomplete References Without Explicit didOpen for All Files (closed, 2025-03-14, 5 comments)
- [microsoft/pyright#10715](https://github.com/microsoft/pyright/issues/10715) @overload function gives incorrect revealed type for Pylance but not for pyright/mypy (closed, 2025-07-16, 38 comments)
- [microsoft/pyright#10053](https://github.com/microsoft/pyright/issues/10053) Django BooleanField default value error (closed, 2025-03-10, 5 comments)
- [microsoft/pyright#8693](https://github.com/microsoft/pyright/issues/8693) Provide diagnostics for missing brackets. (closed, 2024-08-08, 2 comments)
- [microsoft/pyright#395](https://github.com/microsoft/pyright/issues/395)  1.1.8 not work when using multi-root workspace (closed, 2019-12-06, 21 comments)
- queries: `"rename file" in:title repo:microsoft/pyright is:issue`; `references missing repo:microsoft/pyright is:issue`; `references "rename file" repo:microsoft/pyright is:issue`; `references stale repo:microsoft/pyright is:issue`
