# [pyright 1.1.380] typeDefinition changes its answer after edit then inverse

Draft for the author (not filed). Group `pyright-r1-typedefinition-changed-h1-c18cce`, signature `pyright|r1_history|typeDefinition:changed`, case family `H1`.

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
6. Query `textDocument/typeDefinition` on `repro.py` line 19, column 23 (LSP position {line: 18, character: 22}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.380/node_modules/pyright/dist/typeshed-fallback/stdlib/multiprocessing/pool.pyi",
  46,
  6,
  46,
  10
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/multiprocessing/pool.py",
  172,
  6,
  172,
  10
 ]
]
```

Actual:

```json
[
 [
  "repro.py",
  17,
  26,
  17,
  28
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/kb_pyright_8946/triage/pyright-r1-typedefinition-changed-h1-c18cce/repro.json
```

## Evidence and reduction

- representative 7b994d0b8763-v03: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 18.753 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: repro.py: 6/15 non-blank lines kept (15 probes, confirmed 3/3)
- group: 1 violation(s) in 1 run(s), projects pyright_8946, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#10103](https://github.com/microsoft/pyright/issues/10103) override with Any after narrowing undoes the narrowing (closed, 2025-03-17, 1 comments)
- [microsoft/pyright#8946](https://github.com/microsoft/pyright/issues/8946) Type error after undo (closed, 2024-09-10, 4 comments)
- [microsoft/pyright#10354](https://github.com/microsoft/pyright/issues/10354) Support for static hints on std `replace()`  functions (closed, 2025-04-20, 4 comments)
- [microsoft/pyright#10502](https://github.com/microsoft/pyright/issues/10502) User invisible decorators should not trigger Protocol type conflicts. (closed, 2025-05-24, 1 comments)
- [microsoft/pyright#10386](https://github.com/microsoft/pyright/issues/10386) Wrongly suggesting missing implementations of a subclassed dataclass protocol. (closed, 2025-04-28, 5 comments)
- [microsoft/pyright#10606](https://github.com/microsoft/pyright/issues/10606) Django's `TextChoices` is being treated as a tuple rather than a string in the latest version (closed, 2025-06-13, 5 comments)
- [microsoft/pyright#10324](https://github.com/microsoft/pyright/issues/10324) False positive from matching wrong type (`type[Protocol]` rather than `type[_ProtocolMeta]`). (closed, 2025-04-15, 2 comments)
- [microsoft/pyright#8035](https://github.com/microsoft/pyright/issues/8035) Pyright looses literal information on loops/generators? (closed, 2024-05-31, 5 comments)
- queries: `undo in:title repo:microsoft/pyright is:issue`; `"type definition" wrong repo:microsoft/pyright is:issue`; `"type definition" undo repo:microsoft/pyright is:issue`; `"type definition" stale repo:microsoft/pyright is:issue`
