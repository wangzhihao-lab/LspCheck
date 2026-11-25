# Release sweep `newest-2026-11-18` (releases published up to 2026-11-18)

Cell: reproduced/replays and the frozen sweep's verdict; n/a (Go) = not replayable (the project needs a newer Go than the build runs); unavailable = not installable or not launchable; not run = pending. Rules, release dates and install details: releases.json.

## gopls

Rule: newest stable version on proxy.golang.org.

- v0.24.0 (released 2026-10-14; newest; runs go1.27.1)

| cause | group | v0.24.0 |
|---|---|---|
| C3 | `gopls-r2-codeactionresolve-changed-codeaction-70b3e9` | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-notatype-mutation-m2-477181` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-invalidifaceassign-mutation-m2-416e90` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-nonindexableoperand-mutation-m2-ba152b` | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a` | 3/3 reproduced |
| C6 | `gopls-r4-diagnostics-extra-mutation-m2-111975` | 3/3 reproduced |
| C6 | `gopls-r4-syntax-gained-mutation-m2-86fde3` | 3/3 reproduced |
| C7 | `gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39` | 3/3 reproduced |
| C9 | `gopls-r1-references-extra-h9-0290a7` | 3/3 reproduced |
| C12 | `gopls-r1-codeaction-changed-h4-c5344e` | 3/3 reproduced |

## rust-analyzer

Rule: newest weekly GitHub release (tag YYYY-MM-DD).

- 2026-11-16 (released 2026-11-16; newest)

| cause | group | 2026-11-16 |
|---|---|---|
| C4 | `rust-analyzer-r2-completionresolve-changed-completion-3170a1` | 3/3 reproduced |
| C8 | `rust-analyzer-r3-definitionconsistency-extra-d-4cbc9e` | 3/3 reproduced |
| C8 | `rust-analyzer-r3-definitionconsistency-missing-d-586fd8` | 3/3 reproduced |
| C23 | `rust-analyzer-r0-references-result-error-timeout-fresh-pair-8a4b8d` | 0/3 not-reproduced |
| C24 | `rust-analyzer-r0-semantictokens-result-error-timeout-fresh-pair-62256f` | 0/3 not-reproduced |
| C25 | `rust-analyzer-r3-diagnostics-missing-e0004-inactive-code-a-731c4f` | 3/3 reproduced |
| C25 | `rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0` | 3/3 reproduced |
| C26 | `rust-analyzer-r3-semantictokensrange-changed-b-b6e28b` | 3/3 reproduced |
| C27 | `rust-analyzer-r4-completioninsert-gained-completion-e99b79` | 3/3 reproduced |

## ts6

Rule: newest TypeScript 6.x with the newest typescript-language-server (npm).

- 6.0.3+tsls6.1.0 (released 2026-04-16; newest; wrapper released 2026-11-12)

| cause | group | 6.0.3+tsls6.1.0 |
|---|---|---|
| C1 | `ts6-r1-codeaction-key-lost-h5-4f92e2` | 3/3 reproduced |
| C1 | `ts6-r1-completion-lost-h5-fa501c` | 3/3 reproduced |
| C1 | `ts6-r1-definition-lost-h5-61a0fd` | 1/3 flaky |
| C1 | `ts6-r1-definition-lost-h9-898f29` | 3/3 reproduced |
| C1 | `ts6-r1-diagnostics-extra-2305-2339-7006-h5-d5a250` | 2/3 flaky |
| C1 | `ts6-r1-documenthighlight-lost-h5-9b4675` | 1/3 flaky |
| C1 | `ts6-r1-references-lost-h5-d24ca6` | 2/3 flaky |
| C1 | `ts6-r1-references-missing-h5-cc8950` | 2/3 flaky |
| C1 | `ts6-r1-semantictokens-changed-h5-591c42` | 3/3 reproduced |
| C1 | `ts6-r1-semantictokens-missing-h9-d686b3` | 3/3 reproduced |
| C1 | `ts6-r1-signaturehelp-changed-h5-db5a5e` | 2/3 flaky |
| C1 | `ts6-r1-signaturehelp-lost-h9-7bd793` | 3/3 reproduced |
| C1 | `ts6-r1-typedefinition-lost-h5-712a35` | 3/3 reproduced |
| C2 | `ts6-r1-diagnostics-extra-2304-h7-8ca52f` | 3/3 reproduced |
| C11 | `ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3` | 3/3 reproduced |

## ts7

Rule: newest stable TypeScript 7.x (npm).

- 7.0.2 (released 2026-07-08; newest, campaign)

| cause | group | 7.0.2 |
|---|---|---|
| C10 | `ts7-r1-references-missing-h9-2dd24a` | 3/3 reproduced |
