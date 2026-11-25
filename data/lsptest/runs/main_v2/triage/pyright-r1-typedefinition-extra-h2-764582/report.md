# [pyright 1.1.414] typeDefinition adds entries after delete a line, retype it in k chunks

Draft for the author (not filed). Group `pyright-r1-typedefinition-extra-h2-764582`, signature `pyright|r1_history|typeDefinition:extra`, case family `H2`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `soimort/you-get@049548f3f3f3` (corpus, commit 049548f3f3f35e67ba8d3181c71fdc71d11cf260), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open setup.py`
3. textDocument/didOpen: `open src/you_get/extractors/bilibili.py`
4. textDocument/didOpen: `open src/you_get/extractors/iqiyi.py`
5. textDocument/didChange: `change setup.py (28, 0)-(29, 0) ""`
6. Timing: wait until the server is idle after every step.
7. Query `textDocument/typeDefinition` on `src/you_get/extractors/iqiyi.py` line 138, column 87 (LSP position {line: 137, character: 86}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/types.pyi",
  712,
  6,
  712,
  14
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/types.py",
  69,
  4,
  69,
  12
 ]
]
```

Actual:

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  486,
  6,
  486,
  9
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/types.pyi",
  712,
  6,
  712,
  14
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/types.py",
  69,
  4,
  69,
  12
 ]
]
```

Project file `src/you_get/extractors/iqiyi.py`:

```
 135 |                       r1(r'vid=([^&]+)', self.url) or \
 136 |                       r1(r'data-player-videoid="([^"]+)"', html) or r1(r'vid=(\w+?)\&', html) or r1(r'param\[\'vid\'\]\s*=\s*"(.+?)"', html)
 137 |             self.vid = (tvid, videoid)
 138 |             info_u = 'http://pcw-api.iqiyi.com/video/video/playervideoinfo?tvid=' + tvid
 139 |             json_res = get_content(info_u)
 140 |             self.title = json.loads(json_res)['data']['vn']
 141 |         tvid, videoid = self.vid
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-typedefinition-extra-h2-764582/repro.json
```

## Evidence and reduction

- representative de1a4347e97f-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 7 -> 4 (4 probes, 76.957 s, reduced ops confirmed 3/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects soimort/you-get@049548f3f3f3, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#3860](https://github.com/microsoft/pyright/issues/3860) Errors while using Protocol classes from `typing_extensions` (closed, 2022-08-23, 6 comments)
- [microsoft/pyright#10755](https://github.com/microsoft/pyright/issues/10755) PEP-728 arguments rejected from `typing_extensions.TypedDict` (closed, 2025-07-29, 2 comments)
- [microsoft/pyright#10493](https://github.com/microsoft/pyright/issues/10493) Follow-up on #10482, backwards incomaptible change to type narrowing with TypedDict (closed, 2025-05-22, 2 comments)
- [microsoft/pyright#10832](https://github.com/microsoft/pyright/issues/10832) 1.1.404 performance regression with scipy-stubs (closed, 2025-08-20, 37 comments)
- [microsoft/pyright#8646](https://github.com/microsoft/pyright/issues/8646) Converting `TypedDict` to another `TypedDict`, Pyright doesn't handle it correctly. (closed, 2024-08-03, 3 comments)
- [microsoft/pyright#8848](https://github.com/microsoft/pyright/issues/8848) overriding metaclass doesn't work (closed, 2024-08-28, 1 comments)
- [microsoft/pyright#1047](https://github.com/microsoft/pyright/issues/1047) dataclasses.replace does not type correctly (closed, 2020-09-20, 9 comments)
- [microsoft/pyright#9878](https://github.com/microsoft/pyright/issues/9878) Adding __slots__ to a function-like Protocol breaks support for function assigment to the Protocol (closed, 2025-02-11, 3 comments)
- queries: `"while typing" in:title repo:microsoft/pyright is:issue`; `"type definition" extra repo:microsoft/pyright is:issue`; `"type definition" "while typing" repo:microsoft/pyright is:issue`; `"type definition" stale repo:microsoft/pyright is:issue`
