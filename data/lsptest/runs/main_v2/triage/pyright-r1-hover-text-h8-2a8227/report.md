# [pyright 1.1.414] hover shows a different text after query order

Draft for the author (not filed). Group `pyright-r1-hover-text-h8-2a8227`, signature `pyright|r1_history|hover:text`, case family `H8`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `soimort/you-get@049548f3f3f3` (corpus, commit 049548f3f3f35e67ba8d3181c71fdc71d11cf260), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/you_get/extractors/pixnet.py`
3. textDocument/didOpen: `open src/you_get/extractors/suntv.py`
4. textDocument/didChange: `change src/you_get/extractors/suntv.py (29, 0)-(29, 0) "        size = 0\n"`
5. request: `request src/you_get/extractors/pixnet.py completion at (49, 65)`
6. Timing: wait until the server is idle after every step.
7. textDocument/didOpen `src/you_get/extractors/ifeng.py` (the query step opens every target file that is not open), then wait until the server is idle.
8. Query `textDocument/hover` on `src/you_get/extractors/ifeng.py` line 12, column 29 (LSP position {line: 11, character: 28}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "(parameter) title: Unknown | None",
 [
  11,
  26,
  11,
  31
 ]
]
```

Actual:

```json
[
 "(parameter) title: str | Any | None",
 [
  11,
  26,
  11,
  31
 ]
]
```

Project file `src/you_get/extractors/ifeng.py`:

```
   1 | #!/usr/bin/env python
     ...
   3 | __all__ = ['ifeng_download', 'ifeng_download_by_id']
     ...
   5 | from ..common import *
     ...
   7 | def ifeng_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
   8 |     assert r1(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', id), id
   9 |     url = 'http://vxml.ifengimg.com/video_info_new/%s/%s/%s.xml' % (id[-2], id[-2:], id)
  10 |     xml = get_html(url, 'utf-8')
  11 |     title = r1(r'Name="([^"]+)"', xml)
  12 |     title = unescape_html(title)
  13 |     url = r1(r'VideoPlayUrl="([^"]+)"', xml)
  14 |     from random import randint
  15 |     r = randint(10, 19)
  16 |     url = url.replace('http://wideo.ifeng.com/', 'http://ips.ifeng.com/wideo.ifeng.com/')
  17 |     type, ext, size = url_info(url)
     ...
  19 |     print_info(site_info, title, ext, size)
  20 |     if not info_only:
  21 |         download_urls([url], title, ext, size, output_dir, merge = merge)
     ...
  23 | def ifeng_download(url, output_dir = '.', merge = True, info_only = False, **kwargs):
  24 | # old pattern /uuid.shtml
  25 | # now it could be #uuid
  26 |     id = r1(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', url)
  27 |     if id:
  28 |         return ifeng_download_by_id(id, None, output_dir = output_dir, merge = merge, info_only = info_only)
     ...
  30 |     html = get_content(url)
  31 |     uuid_pattern = r'"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"'
  32 |     id = r1(r'var vid="([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"', html)
  33 |     if id is None:
  34 |         video_pattern = r'"vid"\s*:\s*' + uuid_pattern
  35 |         id = match1(html, video_pattern)
  36 |     assert id, "can't find video info"
  37 |     return ifeng_download_by_id(id, None, output_dir = output_dir, merge = merge, info_only = info_only)
     ...
  39 | site_info = "ifeng.com"
  40 | download = ifeng_download
  41 | download_playlist = playlist_not_supported('ifeng')
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-hover-text-h8-2a8227/repro.json
```

## Evidence and reduction

- representative 95c1b8d86026-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 13 -> 4 (25 probes, 257.814 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects soimort/you-get@049548f3f3f3, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#11581](https://github.com/microsoft/pyright/issues/11581) Helping hand from order of messages: causes and consequences (open, 2026-08-02, 0 comments)
- [microsoft/pyright#11644](https://github.com/microsoft/pyright/issues/11644) Order-dependent overload resolution failure due to memorised Protocol conformance check on generic class (open, 2026-08-15, 4 comments)
- [microsoft/pyright#11549](https://github.com/microsoft/pyright/issues/11549) Order of additional overloads matters in subclass where it shouldnt [reportIncompatibleMethodOverride] (open, 2026-07-17, 0 comments)
- [microsoft/pyright#11303](https://github.com/microsoft/pyright/issues/11303) Type inference fails for application of higher-order generic function (open, 2026-03-02, 0 comments)
- [microsoft/pyright#10607](https://github.com/microsoft/pyright/issues/10607) Order dependent inference results with some protocols against numpy (open, 2025-06-14, 0 comments)
- [microsoft/pyright#11317](https://github.com/microsoft/pyright/issues/11317) LSP: Slow semantic completion for built in types (closed, 2026-03-06, 2 comments)
- [microsoft/pyright#10534](https://github.com/microsoft/pyright/issues/10534) How do I wrap functions in a class with a __call__ method while preserving both types and docstrings? (closed, 2025-06-03, 3 comments)
- [microsoft/pyright#1118](https://github.com/microsoft/pyright/issues/1118) reportUnusedVariable ignore pattern (closed, 2020-10-23, 116 comments)
- queries: `order in:title repo:microsoft/pyright is:issue`; `hover wrong repo:microsoft/pyright is:issue`; `hover order repo:microsoft/pyright is:issue`; `hover stale repo:microsoft/pyright is:issue`
