# Release sweep `lifecycle` (releases published up to 2026-09-28)

Cell: reproduced/replays and the frozen sweep's verdict; n/a (Go) = not replayable (the project needs a newer Go than the build runs); unavailable = not installable or not launchable; not run = pending. Rules, release dates and install details: releases.json.

## gopls

Rule: the first release (vX.Y.0) of every minor line v0.16 ... v0.23 (the campaign's v0.23.0), plus the newest.

- v0.16.0 (released 2024-06-20; first of v0.16; runs go1.24.4)
- v0.17.0 (released 2024-12-11; first of v0.17; runs go1.24.4)
- v0.18.0 (released 2025-02-20; first of v0.18; runs go1.24.4)
- v0.19.0+go1.27.1 (released 2025-06-10; first of v0.19; runs go1.27.1)
- v0.20.0 (released 2025-07-28; first of v0.20; runs go1.27.1)
- v0.21.0 (released 2025-12-05; first of v0.21; runs go1.27.1)
- v0.22.0 (released 2026-05-15; first of v0.22; runs go1.27.1)
- v0.23.0 (released 2026-07-07; first of v0.23, newest, campaign; runs go1.27.1)

| cause | group | v0.16.0 | v0.17.0 | v0.18.0 | v0.19.0+go1.27.1 | v0.20.0 | v0.21.0 | v0.22.0 | v0.23.0 |
|---|---|---|---|---|---|---|---|---|---|
| C3 | `gopls-r2-codeactionresolve-changed-codeaction-70b3e9` | n/a (Go) | n/a (Go) | n/a (Go) | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-notatype-mutation-m2-477181` | n/a (Go) | n/a (Go) | n/a (Go) | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C6 | `gopls-r4-diagnostics-extra-mutation-m2-111975` | 0/3 unsettled | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C7 | `gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39` | n/a (Go) | n/a (Go) | n/a (Go) | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C9 | `gopls-r1-references-extra-h9-0290a7` | n/a (Go) | n/a (Go) | n/a (Go) | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C12 | `gopls-r1-codeaction-changed-h4-c5344e` | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 3/3 reproduced | 3/3 reproduced |

## rust-analyzer

Rule: the first weekly release (tag YYYY-MM-DD) of each quarter 2024-Q4 ... 2026-Q3, plus the campaign's 2026-09-21 and the newest.

- 2024-10-07 (released 2024-10-07; first of 2024-Q4)
- 2025-01-06 (released 2025-01-06; first of 2025-Q1)
- 2025-04-07 (released 2025-04-07; first of 2025-Q2)
- 2025-07-07 (released 2025-07-07; first of 2025-Q3) - UNAVAILABLE: RuntimeError: launch check failed (no diagnostics or hover on the smoke project): " "--lockfile-path" "<tmp>/smoke-rust-analyzer-d89y_pll/target/rust-analyzer/m
- 2025-10-27 (released 2025-10-27; first of 2025-Q4)
- 2026-01-05 (released 2026-01-05; first of 2026-Q1)
- 2026-04-06 (released 2026-04-06; first of 2026-Q2)
- 2026-07-06 (released 2026-07-06; first of 2026-Q3)
- 2026-09-21 (released 2026-09-21; campaign)
- 2026-09-28 (released 2026-09-28; newest)

| cause | group | 2024-10-07 | 2025-01-06 | 2025-04-07 | 2025-07-07 | 2025-10-27 | 2026-01-05 | 2026-04-06 | 2026-07-06 | 2026-09-21 | 2026-09-28 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C4 | `rust-analyzer-r2-completionresolve-changed-completion-3170a1` | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | unavailable | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C8 | `rust-analyzer-r3-definitionconsistency-extra-d-4cbc9e` | 0/3 not-reproduced | 0/3 unsettled | 0/3 not-reproduced | unavailable | 0/3 not-reproduced | 0/3 not-reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C23 | `rust-analyzer-r0-references-result-error-timeout-fresh-pair-8a4b8d` | 0/3 not-reproduced | 0/3 unsettled | 0/3 not-reproduced | unavailable | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced |
| C24 | `rust-analyzer-r0-semantictokens-result-error-timeout-fresh-pair-62256f` | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | unavailable | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced |
| C25 | `rust-analyzer-r3-diagnostics-missing-e0004-inactive-code-a-731c4f` | 0/3 not-reproduced | 0/3 unsettled | 0/3 not-reproduced | unavailable | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 3/3 reproduced | 3/3 reproduced |
| C26 | `rust-analyzer-r3-semantictokensrange-changed-b-b6e28b` | 0/3 not-reproduced | 0/3 not-reproduced | 3/3 reproduced | unavailable | 0/3 not-reproduced | 0/3 not-reproduced | 2/3 unsettled | 2/3 unsettled | 3/3 reproduced | 3/3 reproduced |
| C27 | `rust-analyzer-r4-completioninsert-gained-completion-e99b79` | 3/3 reproduced | 0/3 unsettled | 3/3 reproduced | unavailable | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |

## ts6

Rule: the last patch of each TypeScript minor 5.5, 5.6, 5.7, 5.8, 5.9 and 6.0, each with the typescript-language-server release newest at that TypeScript release's publication time (npm `time`), plus the campaign pair 6.0.3+tsls6.0.0 and the newest pair.

- 5.5.4+tsls4.3.3 (released 2024-07-22; last patch of 5.5; wrapper released 2024-02-09)
- 5.6.3+tsls4.3.3 (released 2024-10-08; last patch of 5.6; wrapper released 2024-02-09)
- 5.7.3+tsls4.3.3 (released 2025-01-08; last patch of 5.7; wrapper released 2024-02-09)
- 5.8.3+tsls4.3.4 (released 2025-04-05; last patch of 5.8; wrapper released 2025-02-26)
- 5.9.3+tsls5.0.0 (released 2025-09-30; last patch of 5.9; wrapper released 2025-09-15)
- 6.0.3+tsls5.1.3 (released 2026-04-16; last patch of 6.0; wrapper released 2025-11-19)
- 6.0.3+tsls6.0.0 (released 2026-04-16; campaign; wrapper released 2026-08-20)
- 6.0.3+tsls6.0.1 (released 2026-04-16; newest; wrapper released 2026-09-24)

| cause | group | 5.5.4+tsls4.3.3 | 5.6.3+tsls4.3.3 | 5.7.3+tsls4.3.3 | 5.8.3+tsls4.3.4 | 5.9.3+tsls5.0.0 | 6.0.3+tsls5.1.3 | 6.0.3+tsls6.0.0 | 6.0.3+tsls6.0.1 |
|---|---|---|---|---|---|---|---|---|---|
| C1 | `ts6-r1-references-lost-h5-d24ca6` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C2 | `ts6-r1-diagnostics-extra-2304-h7-8ca52f` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C11 | `ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |

## ts7

Rule: every TypeScript 7.x version on npm up to the newest stable one (stable and beta/rc releases; nightly -dev builds excluded).

- 7.0.1-rc (released 2026-06-18; pre-release)
- 7.0.2 (released 2026-07-08; newest, campaign)

| cause | group | 7.0.1-rc | 7.0.2 |
|---|---|---|---|
| C10 | `ts7-r1-references-missing-h9-2dd24a` | 3/3 reproduced | 3/3 reproduced |
