# [pyright 1.1.414] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `pyright-r3-definitionconsistency-lost-d-a4eaed`, signature `pyright|r3_routes|definitionConsistency:lost`, case family `d`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `Alishahryar1/free-claude-code@1f8b1fd7d054` (corpus, commit 1f8b1fd7d05473652416376cb7acbb8dbf466ea9), language python

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/free_claude_code/providers/vertex/client.py` at line 43, column 14 (LSP position {line: 42, character: 13}) gives the expected set; didOpen `src/free_claude_code/providers/vertex/__init__.py` and `textDocument/definition` at the reference line 5, column 20 (LSP position {line: 4, character: 19}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/free_claude_code/providers/vertex/client.py",
  42,
  6,
  42,
  20
 ]
]
```

Actual:

```json
[]
```

Project file `src/free_claude_code/providers/vertex/__init__.py`:

```
   1 | """Google Vertex AI OpenAI-compatible adapter."""
     ...
   3 | from .client import VertexProvider
     ...
   5 | __all__ = ["VertexProvider"]
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r3-definitionconsistency-lost-d-a4eaed/repro.json
```

## Evidence and reduction

- representative 0af68d3ab9f4-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Alishahryar1/free-claude-code@1f8b1fd7d054, scrapy/scrapy@91d87364637c, virattt/ai-hedge-fund@7d897a002c26, timings settled, seeds 1

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
