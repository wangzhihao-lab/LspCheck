# [pyright 1.1.414] references adds entries after query order

Draft for the author (not filed). Group `pyright-r1-references-extra-h8-98dfb1`, signature `pyright|r1_history|references:extra`, case family `H8`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `D4Vinci/Scrapling@08f107b1240f` (corpus, commit 08f107b1240fd72847b0f5e10426c7e6cc16e67e), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open tests/fetchers/async/test_stealth.py`
3. Timing: send the steps 0 ms apart without waiting, then wait until idle.
4. textDocument/didOpen `scrapling/engines/_browsers/_types.py`, `tests/parser/test_attributes_handler.py` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/references` on `tests/parser/test_attributes_handler.py` line 192, column 21 (LSP position {line: 191, character: 20}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  2445,
  6,
  2445,
  15
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/annotationlib.py",
  78,
  18,
  78,
  27
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/annotationlib.py",
  100,
  14,
  100,
  23
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/annotationlib.py",
  519,
  14,
  519,
  23
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/annotationlib.py",
  1025,
  14,
  1025,
  23
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/pathlib/_os.py",
  181,
  11,
  181,
  20
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/pathlib/_os.py",
  209,
  10,
  209,
  19
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/pathlib/types.py",
  186,
  15,
  186,
  24
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/pathlib/types.py",
  192,
  15,
  192,
  24
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/pathlib/types.py",
  401,
  18,
  401,
  27
 ],
 [
  "/opt/home
... (4977 characters)
```

Actual:

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/builtins.pyi",
  2445,
  6,
  2445,
  15
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  204,
  22,
  204,
  31
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  223,
  22,
  223,
  31
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  247,
  14,
  247,
  23
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  256,
  14,
  256,
  23
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  265,
  14,
  265,
  23
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  268,
  14,
  268,
  23
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  316,
  32,
  316,
  41
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  399,
  19,
  399,
  28
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  557,
  26,
  557,
  35
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  558,
  22,
  558,
  31
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  641,
  18,
  641,
  27
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  657,
  18,
  657,
  27
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/typing_extensions.py",
  679,
  30,
  679,
  39
 ],
 [
  
... (13392 characters)
```

Project file `tests/parser/test_attributes_handler.py`:

```
 189 |             assert attrs["id"] == "new-id"
 190 |             # Reset
 191 |             attrs["id"] = original_id
 192 |         except (TypeError, AttributeError):
 193 |             # If modification is not allowed (read-only)
 194 |             assert attrs["id"] == original_id
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r1-references-extra-h8-98dfb1/repro.json
```

## Evidence and reduction

- representative 8e422004b584-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 10 -> 1 (9 probes, 36.762 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects D4Vinci/Scrapling@08f107b1240f, timings race0, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#11581](https://github.com/microsoft/pyright/issues/11581) Helping hand from order of messages: causes and consequences (open, 2026-08-02, 0 comments)
- [microsoft/pyright#11644](https://github.com/microsoft/pyright/issues/11644) Order-dependent overload resolution failure due to memorised Protocol conformance check on generic class (open, 2026-08-15, 4 comments)
- [microsoft/pyright#11549](https://github.com/microsoft/pyright/issues/11549) Order of additional overloads matters in subclass where it shouldnt [reportIncompatibleMethodOverride] (open, 2026-07-17, 0 comments)
- [microsoft/pyright#11303](https://github.com/microsoft/pyright/issues/11303) Type inference fails for application of higher-order generic function (open, 2026-03-02, 0 comments)
- [microsoft/pyright#10607](https://github.com/microsoft/pyright/issues/10607) Order dependent inference results with some protocols against numpy (open, 2025-06-14, 0 comments)
- [microsoft/pyright#10279](https://github.com/microsoft/pyright/issues/10279) Unknown Send type in generator with yield from (closed, 2025-04-08, 4 comments)
- [microsoft/pyright#10414](https://github.com/microsoft/pyright/issues/10414) "Type is partially unknown" on typed functions when using `--verifytypes`, even with `--ignoreexternal` (closed, 2025-05-05, 5 comments)
- [microsoft/pyright#10715](https://github.com/microsoft/pyright/issues/10715) @overload function gives incorrect revealed type for Pylance but not for pyright/mypy (closed, 2025-07-16, 38 comments)
- queries: `order in:title repo:microsoft/pyright is:issue`; `references extra repo:microsoft/pyright is:issue`; `references order repo:microsoft/pyright is:issue`; `references stale repo:microsoft/pyright is:issue`
