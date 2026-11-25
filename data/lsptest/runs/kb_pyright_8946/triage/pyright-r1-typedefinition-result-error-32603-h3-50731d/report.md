# [pyright 1.1.380] typeDefinition fails with an internal error (-32603) after close and reopen

Draft for the author (not filed). Group `pyright-r1-typedefinition-result-error-32603-h3-50731d`, signature `pyright|r1_history|typeDefinition:result->error:-32603`, case family `H3`.

## Server

- pyright 1.1.380; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.380/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.380; node v24.3.0
- project `pyright_8946` (case), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.380 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open repro.py`
3. textDocument/didChange: `change repro.py (5, 11)-(5, 19) "datetim"`
4. textDocument/didClose: `close repro.py`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `repro.py` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/typeDefinition` on `repro.py` line 6, column 16 (LSP position {line: 5, character: 15}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.380/node_modules/pyright/dist/typeshed-fallback/stdlib/datetime.pyi",
  0,
  0,
  0,
  0
 ]
]
```

Actual:

```json
[
 "error",
 -32603
]
```

Project file `repro.py` (line-reduced: other lines blanked):

```
   5 | if TYPE_CHECKING:
   6 |     import datetime
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/kb_pyright_8946/triage/pyright-r1-typedefinition-result-error-32603-h3-50731d/repro.json
```

## Evidence and reduction

- representative 7b994d0b8763-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 4 -> 3 (6 probes, 46.602 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: repro.py: 2/15 non-blank lines kept (3 probes, confirmed 3/3)
- group: 1 violation(s) in 1 run(s), projects pyright_8946, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#6490](https://github.com/microsoft/pyright/issues/6490) bound methods of a TypedDict don't retain type information (closed, 2023-11-18, 2 comments)
- [microsoft/pyright#6183](https://github.com/microsoft/pyright/issues/6183) Pyright failing to match recursive (nested?) generic protocol (closed, 2023-10-17, 4 comments)
- [microsoft/pyright#1914](https://github.com/microsoft/pyright/issues/1914) `Error: Debug Failure. False expression` for mypy/config_parser.py:107:46 (closed, 2021-05-27, 11 comments)
- [microsoft/pyright#1047](https://github.com/microsoft/pyright/issues/1047) dataclasses.replace does not type correctly (closed, 2020-09-20, 9 comments)
- [microsoft/pyright#9969](https://github.com/microsoft/pyright/issues/9969) False error being identified in async code (closed, 2025-02-22, 6 comments)
- [microsoft/pyright#9239](https://github.com/microsoft/pyright/issues/9239) A required argument overriding an optional argument in the `ParamSpec` is incorrectly marked as optional when this argument is introduced by referencing `__init__`. (closed, 2024-10-16, 6 comments)
- [microsoft/pyright#4706](https://github.com/microsoft/pyright/issues/4706) Regression with default match pattern for Never type on 1.1.296 (closed, 2023-02-28, 26 comments)
- [microsoft/pyright#6514](https://github.com/microsoft/pyright/issues/6514) False negative with dict literal on strict mode (closed, 2023-11-21, 6 comments)
- queries: `"Cannot read properties of undefined reading fileInfo" repo:microsoft/pyright is:issue`; `reopen in:title repo:microsoft/pyright is:issue`; `"type definition" "internal error" repo:microsoft/pyright is:issue`; `"type definition" reopen repo:microsoft/pyright is:issue`; `"type definition" stale repo:microsoft/pyright is:issue`

## Server log excerpt (last confirming replay)

```
[pyright-1.1.380-tr50731d-replay-history-20260923-114843-bab976] textDocument/typeDefinition -> error -32603: Request textDocument/typeDefinition failed with message: Cannot read properties of undefined (reading 'fileInfo')
```
