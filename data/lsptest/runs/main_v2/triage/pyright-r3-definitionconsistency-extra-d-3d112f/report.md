# [pyright 1.1.414] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `pyright-r3-definitionconsistency-extra-d-3d112f`, signature `pyright|r3_routes|definitionConsistency:extra`, case family `d`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `FoundationAgents/OpenManus@3309bf4e416f` (corpus, commit 3309bf4e416fb1c74b008f3e86494439a31bad53), language python

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `app/agent/mcp.py` at line 117, column 41 (LSP position {line: 116, character: 40}) gives the expected set; didOpen `app/agent/mcp.py` and `textDocument/definition` at the reference line 33, column 11 (LSP position {line: 32, character: 10}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "app/agent/mcp.py",
  32,
  4,
  32,
  16
 ]
]
```

Actual:

```json
[
 [
  "app/agent/mcp.py",
  32,
  4,
  32,
  16
 ],
 [
  "app/agent/mcp.py",
  128,
  13,
  128,
  25
 ]
]
```

Project file `app/agent/mcp.py`:

```
  30 |     connection_type: str = "stdio"  # "stdio" or "sse"
     ...
  32 |     # Track tool schemas to detect changes
  33 |     tool_schemas: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
  34 |     _refresh_tools_interval: int = 5  # Refresh tools every N steps
     ...
  36 |     # Special tool names that should trigger termination
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r3-definitionconsistency-extra-d-3d112f/repro.json
```

## Evidence and reduction

- representative 177d4d657921-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects FoundationAgents/OpenManus@3309bf4e416f, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#795](https://github.com/microsoft/pyright/issues/795) Go To Definition jumps to source rather than typeshed stubs (closed, 2020-07-06, 13 comments)
- [microsoft/pyright#6041](https://github.com/microsoft/pyright/issues/6041) Is it possible to implement Go to definition inside Doc-strings or comments? (closed, 2023-09-29, 3 comments)
- [microsoft/pyright#3201](https://github.com/microsoft/pyright/issues/3201) Wrong behavior going to definition on 3rd party libraries (closed, 2022-03-15, 6 comments)
- [microsoft/pyright#10910](https://github.com/microsoft/pyright/issues/10910) Pyright fails on files that are too large (open, 2025-09-09, 9 comments)
- [microsoft/pyright#10252](https://github.com/microsoft/pyright/issues/10252) Pyright incorrectly reports incompatibleMethodOverride for property overriden with cached_property (closed, 2025-04-04, 2 comments)
- [microsoft/pyright#3013](https://github.com/microsoft/pyright/issues/3013) Strict Setting for Return Types (closed, 2022-02-09, 22 comments)
- [microsoft/pyright#10755](https://github.com/microsoft/pyright/issues/10755) PEP-728 arguments rejected from `typing_extensions.TypedDict` (closed, 2025-07-29, 2 comments)
- [microsoft/pyright#1118](https://github.com/microsoft/pyright/issues/1118) reportUnusedVariable ignore pattern (closed, 2020-10-23, 116 comments)
- queries: `"go to definition" in:title repo:microsoft/pyright is:issue`; `definition extra repo:microsoft/pyright is:issue`; `definition "go to definition" repo:microsoft/pyright is:issue`; `definition inconsistent repo:microsoft/pyright is:issue`
