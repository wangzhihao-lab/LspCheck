# [pyright 1.1.414] references adds entries after edit inside a workspace window

Draft for the author (not filed). Group `pyright-r1-references-extra-h9-37c1a2`, signature `pyright|r1_history|references:extra`, case family `H9`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `scrapy/scrapy@91d87364637c` (corpus, commit 91d87364637c1b18fd5bb21d1ed3bb356cf9b6fc), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open scrapy/utils/misc.py`
3. Timing: wait until the server is idle after every step.
4. textDocument/didOpen `scrapy/utils/versions.py`, `tests/test_feedexport.py`, `tests/test_pipelines.py` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/references` on `tests/test_feedexport.py` line 840, column 34 (LSP position {line: 839, character: 33}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/typing.pyi",
  151,
  6,
  151,
  9
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/typing.py",
  587,
  6,
  587,
  9
 ],
 [
  "docs/_ext/scrapydocs.py",
  3,
  19,
  3,
  22
 ],
 [
  "docs/_ext/scrapydocs.py",
  63,
  5,
  63,
  8
 ],
 [
  "docs/_ext/scrapydocs.py",
  90,
  31,
  90,
  34
 ],
 [
  "docs/_ext/scrapydocs.py",
  114,
  49,
  114,
  52
 ],
 [
  "docs/_ext/scrapydocs.py",
  127,
  51,
  127,
  54
 ],
 [
  "docs/_ext/scrapydocs.py",
  133,
  16,
  133,
  19
 ],
 [
  "docs/_ext/scrapydocs.py",
  133,
  27,
  133,
  30
 ],
 [
  "docs/_ext/scrapydocs.py",
  141,
  16,
  141,
  19
 ],
 [
  "docs/_ext/scrapydocs.py",
  141,
  27,
  141,
  30
 ],
 [
  "docs/_ext/scrapydocs.py",
  149,
  16,
  149,
  19
 ],
 [
  "docs/_ext/scrapydocs.py",
  149,
  27,
  149,
  30
 ],
 [
  "docs/_ext/scrapydocs.py",
  155,
  36,
  155,
  39
 ],
 [
  "docs/_ext/scrapyfixautodoc.py",
  5,
  19,
  5,
  22
 ],
 [
  "docs/_ext/scrapyfixautodoc.py",
  18,
  36,
  18,
  39
 ],
 [
  "extras/upgrade-ci-pins.py",
  7,
  19,
  7,
  22
 ],
 [
  "extras/upgrade-ci-pins.py",
  97,
  26,
  97,
  29
 ],
 [
  "scrapy/commands/__init__.py",
  14,
  34,
  14,
  37
 ],
 [
  "scrapy/commands/__init__.py",
  53,
  41,
  53,
  44
 ],
 [
  "scrapy/commands/__init__.py",
  250,
  63,
  250,
  66
 ],
 [
  "scrapy/commands/bench.py",
  5,
  34,
  5,
  37
 ],
 [
  "scrapy/c
... (106134 characters)
```

Actual:

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/typing.pyi",
  151,
  6,
  151,
  9
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/typing.py",
  587,
  6,
  587,
  9
 ],
 [
  "docs/_ext/scrapydocs.py",
  3,
  19,
  3,
  22
 ],
 [
  "docs/_ext/scrapydocs.py",
  63,
  5,
  63,
  8
 ],
 [
  "docs/_ext/scrapydocs.py",
  90,
  31,
  90,
  34
 ],
 [
  "docs/_ext/scrapydocs.py",
  114,
  49,
  114,
  52
 ],
 [
  "docs/_ext/scrapydocs.py",
  127,
  51,
  127,
  54
 ],
 [
  "docs/_ext/scrapydocs.py",
  133,
  16,
  133,
  19
 ],
 [
  "docs/_ext/scrapydocs.py",
  133,
  27,
  133,
  30
 ],
 [
  "docs/_ext/scrapydocs.py",
  141,
  16,
  141,
  19
 ],
 [
  "docs/_ext/scrapydocs.py",
  141,
  27,
  141,
  30
 ],
 [
  "docs/_ext/scrapydocs.py",
  149,
  16,
  149,
  19
 ],
 [
  "docs/_ext/scrapydocs.py",
  149,
  27,
  149,
  30
 ],
 [
  "docs/_ext/scrapydocs.py",
  155,
  36,
  155,
  39
 ],
 [
  "docs/_ext/scrapyfixautodoc.py",
  5,
  19,
  5,
  22
 ],
 [
  "docs/_ext/scrapyfixautodoc.py",
  18,
  36,
  18,
  39
 ],
 [
  "extras/upgrade-ci-pins.py",
  7,
  19,
  7,
  22
 ],
 [
  "extras/upgrade-ci-pins.py",
  97,
  26,
  97,
  29
 ],
 [
  "scrapy/commands/__init__.py",
  14,
  34,
  14,
  37
 ],
 [
  "scrapy/commands/__init__.py",
  53,
  41,
  53,
  44
 ],
 [
  "scrapy/commands/__init__.py",
  250,
  63,
  250,
  66
 ],
 [
  "scrapy/commands/bench.py",
  5,
  34,
  5,
  37
 ],
 [
  "scrapy/c
... (106246 characters)
```

Project file `tests/test_feedexport.py`:

```
 837 |         }
     ...
 839 |         for fmt, expected in formats.items():
 840 |             settings: dict[str, Any] = {
 841 |                 "FEEDS": {
 842 |                     self._random_temp_filename(): {"format": fmt},
 843 |                 },
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-references-extra-h9-37c1a2/repro.json
```

## Evidence and reduction

- representative 08417dd958ba-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 14 -> 1 (13 probes, 180.612 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects scrapy/scrapy@91d87364637c, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#10279](https://github.com/microsoft/pyright/issues/10279) Unknown Send type in generator with yield from (closed, 2025-04-08, 4 comments)
- [microsoft/pyright#10414](https://github.com/microsoft/pyright/issues/10414) "Type is partially unknown" on typed functions when using `--verifytypes`, even with `--ignoreexternal` (closed, 2025-05-05, 5 comments)
- [microsoft/pyright#10715](https://github.com/microsoft/pyright/issues/10715) @overload function gives incorrect revealed type for Pylance but not for pyright/mypy (closed, 2025-07-16, 38 comments)
- [microsoft/pyright#10053](https://github.com/microsoft/pyright/issues/10053) Django BooleanField default value error (closed, 2025-03-10, 5 comments)
- [microsoft/pyright#9304](https://github.com/microsoft/pyright/issues/9304) Ignores configuation (closed, 2024-10-24, 1 comments)
- queries: `references extra repo:microsoft/pyright is:issue`; `references stale repo:microsoft/pyright is:issue`
