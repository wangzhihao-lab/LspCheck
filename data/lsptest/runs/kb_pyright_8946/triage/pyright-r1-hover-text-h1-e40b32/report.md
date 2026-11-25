# [pyright 1.1.380] hover shows a different text after edit then inverse

Draft for the author (not filed). Group `pyright-r1-hover-text-h1-e40b32`, signature `pyright|r1_history|hover:text`, case family `H1`.

## Server

- pyright 1.1.380; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.380/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.380; node v24.3.0
- project `pyright_8946` (case), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.380 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open repro.py`
3. textDocument/didChange: `change repro.py (0, 11)-(0, 11) "("`
4. textDocument/didChange: `change repro.py (0, 11)-(0, 12) ""`
5. Timing: wait until the server is idle after every step.
6. Query `textDocument/hover` on `repro.py` line 19, column 23 (LSP position {line: 18, character: 22}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "(variable) po: Pool",
 [
  18,
  21,
  18,
  23
 ]
]
```

Actual:

```json
[
 "(variable) po: Unknown",
 [
  18,
  21,
  18,
  23
 ]
]
```

Project file `repro.py` (line-reduced: other lines blanked):

```
   1 | from __future__ import annotations
     ...
   9 | from multiprocessing import Pool
     ...
  13 | def execute_shell_commands(
     ...
  17 | ) -> list[tuple[int, datetime.date]]:
  18 |     with Pool(workers) as po:
  19 |         exit_codes = po.map(os.system, [cmd(d) for d in dates])
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/kb_pyright_8946/triage/pyright-r1-hover-text-h1-e40b32/repro.json
```

## Evidence and reduction

- representative 7b994d0b8763-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 20.21 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: repro.py: 6/15 non-blank lines kept (15 probes, confirmed 3/3)
- group: 1 violation(s) in 1 run(s), projects pyright_8946, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#10103](https://github.com/microsoft/pyright/issues/10103) override with Any after narrowing undoes the narrowing (closed, 2025-03-17, 1 comments)
- [microsoft/pyright#8946](https://github.com/microsoft/pyright/issues/8946) Type error after undo (closed, 2024-09-10, 4 comments)
- [microsoft/pyright#11317](https://github.com/microsoft/pyright/issues/11317) LSP: Slow semantic completion for built in types (closed, 2026-03-06, 2 comments)
- [microsoft/pyright#10534](https://github.com/microsoft/pyright/issues/10534) How do I wrap functions in a class with a __call__ method while preserving both types and docstrings? (closed, 2025-06-03, 3 comments)
- [microsoft/pyright#1118](https://github.com/microsoft/pyright/issues/1118) reportUnusedVariable ignore pattern (closed, 2020-10-23, 116 comments)
- [microsoft/pyright#10229](https://github.com/microsoft/pyright/issues/10229) Variance check is inconsistent (closed, 2025-03-31, 3 comments)
- [microsoft/pyright#9605](https://github.com/microsoft/pyright/issues/9605) 2 different overloads are incorrectly considered equivalent (closed, 2024-12-19, 5 comments)
- [microsoft/pyright#4513](https://github.com/microsoft/pyright/issues/4513) Type of "xstate" could not be determined because it refers to itself (closed, 2023-01-23, 11 comments)
- queries: `undo in:title repo:microsoft/pyright is:issue`; `hover wrong repo:microsoft/pyright is:issue`; `hover undo repo:microsoft/pyright is:issue`; `hover stale repo:microsoft/pyright is:issue`
