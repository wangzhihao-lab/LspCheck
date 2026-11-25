# [pyright 1.1.414] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `pyright-r3-definitionconsistency-extra-d-3d112f`, signature `pyright|r3_routes|definitionConsistency:extra`, case family `d`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `browser-use/browser-use@d8110c5ff87c` (corpus, commit d8110c5ff87ccba887aaa726cdb780f2f84bef8d), language python

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `browser_use/browser/watchdogs/aboutblank_watchdog.py` at line 50, column 12 (LSP position {line: 49, character: 11}) gives the expected set; didOpen `browser_use/browser/watchdogs/aboutblank_watchdog.py` and `textDocument/definition` at the reference line 40, column 6 (LSP position {line: 39, character: 5}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "browser_use/browser/watchdogs/aboutblank_watchdog.py",
  39,
  1,
  39,
  10
 ]
]
```

Actual:

```json
[
 [
  "browser_use/browser/watchdogs/aboutblank_watchdog.py",
  39,
  1,
  39,
  10
 ],
 [
  "browser_use/browser/watchdogs/aboutblank_watchdog.py",
  44,
  7,
  44,
  16
 ],
 [
  "browser_use/browser/watchdogs/aboutblank_watchdog.py",
  49,
  7,
  49,
  16
 ]
]
```

Project file `browser_use/browser/watchdogs/aboutblank_watchdog.py`:

```
  37 | 		AboutBlankDVDScreensaverShownEvent,
  38 | 	]
     ...
  40 | 	_stopping: bool = PrivateAttr(default=False)
     ...
  42 | 	async def on_BrowserStopEvent(self, event: BrowserStopEvent) -> None:
  43 | 		"""Handle browser stop request - stop creating new tabs."""
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r3-definitionconsistency-extra-d-3d112f/repro.json
```

## Evidence and reduction

- representative 96ea95edb4ad-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects browser-use/browser-use@d8110c5ff87c, timings settled, seeds 2

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

## Server log excerpt (last confirming replay)

```
[pyright-1.1.414-tr3d112f-r3-replay-baseline-20260925-174310-fb851c] window/logMessage type 1: venv .venv subdirectory not found in venv path temp/lsptest_runs/pyright-1.1.414-tr3d112f-r3-replay-baseline-20260925-174310-fb851c/ws.
[pyright-1.1.414-tr3d112f-r3-replay-baseline-20260925-174310-fb851c] window/logMessage type 1: venv .venv subdirectory not found in venv path temp/lsptest_runs/pyright-1.1.414-tr3d112f-r3-replay-baseline-20260925-174310-fb851c/ws.
[pyright-1.1.414-tr3d112f-r3-replay-control-20260925-174313-e175ce] window/logMessage type 1: venv .venv subdirectory not found in venv path temp/lsptest_runs/pyright-1.1.414-tr3d112f-r3-replay-control-20260925-174313-e175ce/ws.
[pyright-1.1.414-tr3d112f-r3-replay-control-20260925-174313-e175ce] window/logMessage type 1: venv .venv subdirectory not found in venv path temp/lsptest_runs/pyright-1.1.414-tr3d112f-r3-replay-control-20260925-174313-e175ce/ws.
```
