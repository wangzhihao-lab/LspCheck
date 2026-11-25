# [pyright 1.1.414] completion edit is not valid (completionInsert:gained)

Draft for the author (not filed). Group `pyright-r4-completioninsert-gained-completion-79a584`, signature `pyright|r4_edits|completionInsert:gained`, case family `completion`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `Graphify-Labs/graphify@a5957aa6ef51` (corpus, commit a5957aa6ef51c9be8d054de9783d25046c187f3f), language python

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/completion` on `tests/test_hypergraph.py` at line 136, column 24 (LSP position {line: 135, character: 23}); insert the item: the file must not gain a syntax error.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "expected argument value expression"
]
```

Project file `tests/test_hypergraph.py`:

```
 134 | def test_attach_hyperedges_skips_entry_without_id():
 135 |     G = nx.Graph()
 136 |     attach_hyperedges(G, [{"label": "No ID", "nodes": ["A", "B", "C"]}])
 137 |     assert G.graph.get("hyperedges", []) == []
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/pyright-r4-completioninsert-gained-completion-79a584/repro.json
```

## Evidence and reduction

- representative d5f29969c6e6-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Graphify-Labs/graphify@a5957aa6ef51, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- none found
- queries: `completionInsert unexpected repo:microsoft/pyright is:issue`; `completionInsert "wrong edit" repo:microsoft/pyright is:issue`
