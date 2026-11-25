# [pyright 1.1.414] hover shows a different text after delete a line, retype it in k chunks

Draft for the author (not filed). Group `pyright-r1-hover-text-h2-fb2ed0`, signature `pyright|r1_history|hover:text`, case family `H2`.

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
7. Query `textDocument/hover` on `src/you_get/extractors/iqiyi.py` line 138, column 87 (LSP position {line: 137, character: 86}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "(variable) tvid: Unknown | None",
 [
  137,
  84,
  137,
  88
 ]
]
```

Actual:

```json
[
 "(variable) tvid: str | Any | None",
 [
  137,
  84,
  137,
  88
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-hover-text-h2-fb2ed0/repro.json
```

## Evidence and reduction

- representative de1a4347e97f-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 7 -> 4 (4 probes, 77.986 s, reduced ops confirmed 3/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects soimort/you-get@049548f3f3f3, timings settled, seeds 3

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
