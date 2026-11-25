# [pyright 1.1.414] references adds entries after configuration toggle a->b->a

Draft for the author (not filed). Group `pyright-r1-references-extra-h4-a63d47`, signature `pyright|r1_history|references:extra`, case family `H4`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `usestrix/strix@56f7d45388e6` (corpus, commit 56f7d45388e6b0abe3f5dcfd09e8dba35c727b24), language python

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. workspace/didChangeConfiguration: `set_config {"python": {"analysis": {"diagnosticMode": "workspace"}}}`
3. workspace/didChangeConfiguration: `set_config {"python": {"analysis": {"diagnosticMode": "openFilesOnly"}}}`
4. Timing: wait until the server is idle after every step.
5. textDocument/didOpen `strix/interface/tui/backend/live_view.py`, `strix/report/state.py`, `tests/test_finish_coverage_gate.py` (the query step opens every target file that is not open), then wait until the server is idle.
6. Query `textDocument/references` on `tests/test_finish_coverage_gate.py` line 3, column 29 (LSP position {line: 2, character: 28}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/__future__.pyi",
  19,
  0,
  19,
  11
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/__future__.pyi",
  34,
  5,
  34,
  16
 ],
 [
  "/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/__future__.py",
  144,
  0,
  144,
  11
 ],
 [
  "/opt/homebrew/lib/python3.14/site-packages/markdown_it/token.py",
  0,
  23,
  0,
  34
 ],
 [
  "strix/agents/factory.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/agents/prompt.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/config/codex.py",
  10,
  23,
  10,
  34
 ],
 [
  "strix/config/loader.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/config/models.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/config/settings.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/config/tool_call_ids.py",
  11,
  23,
  11,
  34
 ],
 [
  "strix/config/tool_call_limits.py",
  10,
  23,
  10,
  34
 ],
 [
  "strix/core/agents.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/core/execution.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/core/hooks.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/core/inputs.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/core/paths.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/core/runner.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/core/sessions.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/interface/auth_cli.py",
  7,
  23,
  7,
  34
 ],
 [
  "strix/interface/cli_args.py",
  2,
  23,
  2,
  34
 ],
 [
  "strix/interface/clou
... (6711 characters)
```

Actual:

```json
[
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/__future__.pyi",
  19,
  0,
  19,
  11
 ],
 [
  "<servers>/pyright-1.1.414/node_modules/pyright/dist/typeshed-fallback/stdlib/__future__.pyi",
  34,
  5,
  34,
  16
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_api.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_auth.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_client.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_config.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_content.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_decoders.py",
  6,
  23,
  6,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_exceptions.py",
  33,
  23,
  33,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_main.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_models.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_multipart.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_status_codes.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_transports/asgi.py",
  0,
  23,
  0,
  34
 ],
 [
  "~/Library/Python/3.14/lib/python/site-packages/httpx/_tr
... (19356 characters)
```

Project file `tests/test_finish_coverage_gate.py`:

```
   1 | """finish_scan confronts the root agent with the coverage the runtime can see."""
     ...
   3 | from __future__ import annotations
     ...
   5 | from typing import TYPE_CHECKING
     ...
   7 | import pytest
     ...
   9 | from strix.tools.coverage.tools import _record_impl, hydrate_coverage_from_disk
  10 | from strix.tools.finish.tool import _coverage_summary
     ...
  13 | if TYPE_CHECKING:
  14 |     from pathlib import Path
     ...
  17 | _GRAPH = {
  18 |     "statuses": {"agent-1": "completed"},
  19 |     "names": {"agent-1": "injection-tester"},
  20 |     "metadata": {"agent-1": {"skills": ["sql_injection", "xss"]}},
  21 | }
     ...
  24 | @pytest.fixture(autouse=True)
  25 | def _empty_ledger(tmp_path: Path) -> None:
  26 |     hydrate_coverage_from_disk(tmp_path)
     ...
  29 | def _record(risk_area: str) -> None:
  30 |     _record_impl(
  31 |         surface="POST /api/orders/{id}",
  32 |         risk_area=risk_area,
  33 |         outcome="no_issue_found",
  34 |         evidence="Parameters fuzzed; no anomalies.",
  35 |         agent_id="agent-1",
  36 |         agent_name="injection-tester",
  37 |     )
     ...
  40 | def test_unrecorded_risk_class_is_reported_back_to_the_root_agent() -> None:
  41 |     _record("SQL injection")
     ...
  43 |     summary = _coverage_summary(_GRAPH)
     ...
  45 |     assert summary["coverage_recorded"] == 1
  46 |     assert len(summary["coverage_gaps"]) == 1
  47 |     assert "xss" in summary["coverage_gaps"][0]
  48 |     assert "unexamined" in summary["coverage_gap_warning"]
     ...
  51 | def test_fully_accounted_coverage_raises_no_gap_warning() -> None:
  52 |     _record("SQL injection")
  53 |     _record("cross-site scripting")
     ...
  55 |     summary = _coverage_summary(_GRAPH)
     ...
  57 |     assert "coverage_gaps" not in summary
  58 |     assert "coverage_gap_warning" not in summary
     ...
  61 | def test_an_empty_ledger_still_warns_first() -> None:
  62 |     summary = _coverage_summary(_GRAPH)
     ...
  64 |     assert summary["coverage_recorded"] == 0
  65 |     assert "No coverage was recorded" in summary["coverage_warning"]
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r1-references-extra-h4-a63d47/repro.json
```

## Evidence and reduction

- representative 754b6ab9087f-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 2 (7 probes, 142.394 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects usestrix/strix@56f7d45388e6, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#10279](https://github.com/microsoft/pyright/issues/10279) Unknown Send type in generator with yield from (closed, 2025-04-08, 4 comments)
- [microsoft/pyright#10414](https://github.com/microsoft/pyright/issues/10414) "Type is partially unknown" on typed functions when using `--verifytypes`, even with `--ignoreexternal` (closed, 2025-05-05, 5 comments)
- [microsoft/pyright#10715](https://github.com/microsoft/pyright/issues/10715) @overload function gives incorrect revealed type for Pylance but not for pyright/mypy (closed, 2025-07-16, 38 comments)
- [microsoft/pyright#10053](https://github.com/microsoft/pyright/issues/10053) Django BooleanField default value error (closed, 2025-03-10, 5 comments)
- [microsoft/pyright#9304](https://github.com/microsoft/pyright/issues/9304) Ignores configuation (closed, 2024-10-24, 1 comments)
- [microsoft/pyright#6776](https://github.com/microsoft/pyright/issues/6776) False negative with `Class1 | Class2` union syntax prior to Python 3.10, when `__future__.annotations` is imported (closed, 2023-12-18, 9 comments)
- queries: `"configuration change" in:title repo:microsoft/pyright is:issue`; `references extra repo:microsoft/pyright is:issue`; `references "configuration change" repo:microsoft/pyright is:issue`; `references stale repo:microsoft/pyright is:issue`
