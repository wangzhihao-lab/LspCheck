# [pyright 1.1.414] signatureHelp changes its answer after edit inside a workspace window

Draft for the author (not filed). Group `pyright-r1-signaturehelp-changed-h9-846c6c`, signature `pyright|r1_history|signatureHelp:changed`, case family `H9`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `ultralytics/yolov5@402e17ddf820` (corpus, commit 402e17ddf820996f51a191cbb798376e1144f069), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open models/common.py`
3. Timing: wait until the server is idle after every step.
4. textDocument/didOpen `models/yolo.py`, `utils/activations.py`, `utils/dataloaders.py` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/signatureHelp` on `utils/dataloaders.py` line 345, column 80 (LSP position {line: 344, character: 79}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"(im: Unknown, new_shape: Unknown = (640, 640), color: Unknown = (114, 114, 114), auto: bool = True, scaleFill: bool = False, scaleup: bool = True, stride: int = 32) -> tuple[Unknown, tuple[float | Unknown, float | Unknown] | tuple[Unknown, Unknown], tuple[Any | float | Unknown, Any | float | Unknown]]"
```

Actual:

```json
"(im: Unknown, new_shape: Unknown = (640, 640), color: Unknown = (114, 114, 114), auto: bool = True, scaleFill: bool = False, scaleup: bool = True, stride: int = 32) -> Unknown"
```

Project file `utils/dataloaders.py`:

```
 342 |         if self.transforms:
 343 |             im = self.transforms(im0)  # transforms
 344 |         else:
 345 |             im = letterbox(im0, self.img_size, stride=self.stride, auto=self.auto)[0]  # padded resize
 346 |             im = im.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
 347 |             im = np.ascontiguousarray(im)  # contiguous
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-signaturehelp-changed-h9-846c6c/repro.json
```

## Evidence and reduction

- representative ed216fc8dca5-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 17 -> 1 (11 probes, 197.446 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ultralytics/yolov5@402e17ddf820, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#4813](https://github.com/microsoft/pyright/issues/4813) ParamSpec-based signature change works with functions but not classes (closed, 2023-03-21, 11 comments)
- [microsoft/pyright#2758](https://github.com/microsoft/pyright/issues/2758) reportGeneralTypeIssues when using pep612 `ParamSpec` (closed, 2021-12-23, 14 comments)
- queries: `"signature help" wrong repo:microsoft/pyright is:issue`; `"signature help" stale repo:microsoft/pyright is:issue`
