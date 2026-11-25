# [pyright 1.1.380] hover shows a different text after delete a line, retype it in k chunks

Draft for the author (not filed). Group `pyright-r1-hover-text-h2-fb2ed0`, signature `pyright|r1_history|hover:text`, case family `H2`.

## Server

- pyright 1.1.380; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.380/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.380; node v24.3.0
- project `pyright_8946` (case), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.380 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open repro.py`
3. textDocument/didChange: `change repro.py (5, 0)-(6, 0) ""`
4. textDocument/didChange: `change repro.py (5, 0)-(5, 0) "    import datetime\n"`
5. Timing: wait until the server is idle after every step.
6. Query `textDocument/hover` on `repro.py` line 15, column 6 (LSP position {line: 14, character: 5}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "(parameter) cmd: (date) -> str",
 [
  14,
  4,
  14,
  7
 ]
]
```

Actual:

```json
[
 "(parameter) cmd: (Unknown) -> str",
 [
  14,
  4,
  14,
  7
 ]
]
```

Project file `repro.py` (line-reduced: other lines blanked):

```
   5 | if TYPE_CHECKING:
   6 |     import datetime
     ...
  10 | from typing import Callable
     ...
  13 | def execute_shell_commands(
     ...
  15 |     cmd: Callable[[datetime.date], str],
     ...
  17 | ) -> list[tuple[int, datetime.date]]:
     ...
  20 |         return [ret for ret in zip(exit_codes, dates) if ret[0] != 0]
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/kb_pyright_8946/triage/pyright-r1-hover-text-h2-fb2ed0/repro.json
```

## Evidence and reduction

- representative db23e5877dcf-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 3 (10 probes, 90.527 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: repro.py: 7/15 non-blank lines kept (10 probes, confirmed 3/3)
- group: 1 violation(s) in 1 run(s), projects pyright_8946, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#3860](https://github.com/microsoft/pyright/issues/3860) Errors while using Protocol classes from `typing_extensions` (closed, 2022-08-23, 6 comments)
- [microsoft/pyright#11317](https://github.com/microsoft/pyright/issues/11317) LSP: Slow semantic completion for built in types (closed, 2026-03-06, 2 comments)
- [microsoft/pyright#10534](https://github.com/microsoft/pyright/issues/10534) How do I wrap functions in a class with a __call__ method while preserving both types and docstrings? (closed, 2025-06-03, 3 comments)
- [microsoft/pyright#1118](https://github.com/microsoft/pyright/issues/1118) reportUnusedVariable ignore pattern (closed, 2020-10-23, 116 comments)
- [microsoft/pyright#10229](https://github.com/microsoft/pyright/issues/10229) Variance check is inconsistent (closed, 2025-03-31, 3 comments)
- [microsoft/pyright#9605](https://github.com/microsoft/pyright/issues/9605) 2 different overloads are incorrectly considered equivalent (closed, 2024-12-19, 5 comments)
- [microsoft/pyright#9687](https://github.com/microsoft/pyright/issues/9687) Pyright produces phantom int type from recursive type alias that includes float (closed, 2025-01-10, 2 comments)
- [microsoft/pyright#6764](https://github.com/microsoft/pyright/issues/6764) False positive of "reportUnnecessaryComparison" with condition inside loop (closed, 2023-12-17, 5 comments)
- queries: `"while typing" in:title repo:microsoft/pyright is:issue`; `hover wrong repo:microsoft/pyright is:issue`; `hover "while typing" repo:microsoft/pyright is:issue`; `hover stale repo:microsoft/pyright is:issue`
