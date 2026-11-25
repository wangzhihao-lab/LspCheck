# Engine smoke (2026-09-23 01:44)

Seed 1, up to 3 files x 12 positions per project. Stability = share of keys whose normalized result is equal in two fresh sessions (baseline, control).

| server | project@commit | settled B/C | settle s B/C | keys B/C | stability | total s B/C |
|---|---|---|---|---|---|---|
| pyright 1.1.414 | pallets/flask@d73fa1cdcbd8 | True/True | 3.25/3.449 | 299/299 | 1.0 | 37.18/47.37 |
| ts6 6.0.3 | pmndrs/zustand@b57db4f86ef1 | True/True | 5.376/3.426 | 306/306 | 1.0 | 8.89/5.89 |
| ts7 7.0.2 | pmndrs/zustand@b57db4f86ef1 | True/True | 2.566/2.609 | 306/306 | 1.0 | 3.4/3.42 |
| rust-analyzer 2026-09-21 | sharkdp/fd@9e8927e8f3ee | True/True | 105.195/120.486 | 304/304 | 1.0 | 118.21/125.42 |
| gopls v0.23.0 | spf13/cobra@adbc8813901b | True/True | 4.156/3.957 | 303/303 | 1.0 | 6.31/5.92 |

## Stability per method: equal/keys (informative baseline results)

| server | codeAction | completion | definition | diagnostics | documentHighlight | documentSymbol | foldingRange | hover | inlayHint | references | semanticTokens | signatureHelp | typeDefinition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pyright | 41/41 (0) | 36/36 (16) | 36/36 (21) | 3/3 (2) | 36/36 (36) | 3/3 (3) | - | 36/36 (36) | - | 36/36 (22) | - | 36/36 (2) | 36/36 (19) |
| ts6 | 39/39 (37) | 36/36 (28) | 36/36 (33) | 3/3 (2) | 36/36 (33) | 3/3 (3) | 3/3 (3) | 36/36 (36) | 3/3 (3) | 36/36 (33) | 3/3 (3) | 36/36 (5) | 36/36 (21) |
| ts7 | 39/39 (0) | 36/36 (28) | 36/36 (33) | 3/3 (2) | 36/36 (33) | 3/3 (3) | 3/3 (3) | 36/36 (35) | 3/3 (3) | 36/36 (33) | 3/3 (3) | 36/36 (5) | 36/36 (19) |
| rust-analyzer | 37/37 (26) | 36/36 (34) | 36/36 (35) | 3/3 (1) | 36/36 (35) | 3/3 (3) | 3/3 (3) | 36/36 (35) | 3/3 (3) | 36/36 (35) | 3/3 (3) | 36/36 (13) | 36/36 (22) |
| gopls | 36/36 (36) | 36/36 (31) | 36/36 (36) | 3/3 (0) | 36/36 (36) | 3/3 (3) | 3/3 (3) | 36/36 (36) | 3/3 (3) | 36/36 (31) | 3/3 (3) | 36/36 (15) | 36/36 (26) |

## Notes

- pyright: diagnostics in baseline 5, of which unresolved-module noise 1; settle mode push
- ts6: diagnostics in baseline 3, of which unresolved-module noise 3; settle mode push
- ts7: diagnostics in baseline 3, of which unresolved-module noise 3; settle mode pull
- rust-analyzer: diagnostics in baseline 1, of which unresolved-module noise 0; settle mode pull
- gopls: diagnostics in baseline 0, of which unresolved-module noise 0; settle mode push
- server processes after the run: 0 of 22 still alive; pgrep matches: 0

## Interpretation

- Completion 'server order' is the display order the server requests (sortText, else label, per LSP); the array order is alphabetical in ts6 and arbitrary in ts7, so its first 50 items would be meaningless. sortText values are not stored.
- Exploratory run with seed 2, 4 files x 20 positions (about 665 keys per server): all servers and methods 100% stable except gopls completion, 78/80. Five further fresh gopls sessions differed pairwise on the same 2 keys (identifier prefixes 'int' and 'w'), each time with a different subset of unimported-package names from the Go module cache. This is nondeterminism inside gopls, not a volatile field (completionBudget=0s does not remove it); the oracles' fresh-vs-fresh control excludes such keys.
- Edit round trip (insert a comment line, run the full query suite, apply the computed inverse, settle, query again) matched a fresh baseline on 100% of keys for ts6, ts7 and gopls. For pyright 1.1.414, 2 auto-import completion keys differed, reproduced 2/2 (fresh-vs-fresh is 100% stable). This is a candidate for R1 triage, not an engine artifact.
- rust-analyzer settle time is dominated by cache priming (indexing std and dependencies; 15-90 s per session). Setting cachePriming.enable=false would shorten sessions if needed. gopls keeps a content-addressed analysis cache in ~/Library/Caches/gopls shared across sessions (GOPLSCACHE could isolate it per session).
