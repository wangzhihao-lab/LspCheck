# [pyright 1.1.414] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `pyright-r3-highlightvsreferences-gained-c-3118cc`, signature `pyright|r3_routes|highlightVsReferences:gained`, case family `c`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `Panniantong/Agent-Reach@a19a171fa980` (corpus, commit a19a171fa980a0785849596492e0af4db800c82f), language python

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `agent_reach/channels/boss.py` at line 107, column 15 (LSP position {line: 106, character: 14}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  95,
  16,
  95,
  19
 ],
 [
  95,
  60,
  95,
  63
 ],
 [
  106,
  13,
  106,
  16
 ],
 [
  108,
  16,
  108,
  19
 ],
 [
  108,
  60,
  108,
  63
 ],
 [
  191,
  29,
  191,
  32
 ],
 [
  239,
  24,
  239,
  27
 ],
 [
  243,
  45,
  243,
  48
 ],
 [
  244,
  30,
  244,
  33
 ],
 [
  244,
  74,
  244,
  77
 ]
]
```

Project file `agent_reach/channels/boss.py`:

```
 104 | def _security_check_blocks_all(pages) -> bool:
 105 |     """现有 zhipin 页签是否全部停在反爬安全校验页（不是登录页）。"""
 106 |     zhipin_urls = [
 107 |         page.get("url", "")
 108 |         for page in (pages or [])
 109 |         if page.get("type") == "page" and host_matches(page.get("url", ""), "zhipin.com")
 110 |     ]
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r3-highlightvsreferences-gained-c-3118cc/repro.json
```

## Evidence and reduction

- representative 0112eaa84042-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Panniantong/Agent-Reach@a19a171fa980, TauricResearch/TradingAgents@2d17df8da153, hiyouga/LlamaFactory@97b32d3133b5, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#10818](https://github.com/microsoft/pyright/issues/10818) why lsp progress keep showing find references (closed, 2025-08-19, 1 comments)
- [microsoft/pyright#10086](https://github.com/microsoft/pyright/issues/10086) Pyright LSP Returns Incomplete References Without Explicit didOpen for All Files (closed, 2025-03-14, 5 comments)
- [microsoft/pyright#9538](https://github.com/microsoft/pyright/issues/9538) Symlinks are not taken into account with "find references" (closed, 2024-12-03, 2 comments)
- [microsoft/pyright#8047](https://github.com/microsoft/pyright/issues/8047) Pyright runs forever on an identity function being called with a tuple containing two references of itself as argument (closed, 2024-06-02, 1 comments)
- [microsoft/pyright#7763](https://github.com/microsoft/pyright/issues/7763) Incorrect type when `Enum` member references other `Enum` member in initalization (closed, 2024-04-25, 2 comments)
- [microsoft/pyright#10087](https://github.com/microsoft/pyright/issues/10087) Currently no error when poping a Required key from a TypedDict & still return correct type. (closed, 2025-03-14, 3 comments)
- [microsoft/pyright#2035](https://github.com/microsoft/pyright/issues/2035) Explicitly choose a Pyright version when using it with the VS Code Python Extension (closed, 2021-06-26, 19 comments)
- [microsoft/pyright#9642](https://github.com/microsoft/pyright/issues/9642) Running pyright on a full workspace does not seem to report all existing errors. (closed, 2024-12-29, 13 comments)
- queries: `references in:title repo:microsoft/pyright is:issue`; `highlight unexpected repo:microsoft/pyright is:issue`; `highlight references repo:microsoft/pyright is:issue`; `highlight inconsistent repo:microsoft/pyright is:issue`
