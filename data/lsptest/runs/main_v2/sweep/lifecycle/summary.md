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
| C13 | `gopls-r1-codeaction-key-lost-h7-547744` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C14 | `gopls-r1-completion-lost-h7-1a1169` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C15 | `gopls-r4-diagnostics-extra-unusedimport-mutation-m3-aefa9e` | n/a (Go) | n/a (Go) | n/a (Go) | 0/3 unsettled | 3/3 reproduced | 0/3 unsettled | 0/3 unsettled | 3/3 reproduced |
| C16 | `gopls-r5-foldingrange-changed-t4-b07c86` | n/a (Go) | n/a (Go) | n/a (Go) | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |

## rust-analyzer

Rule: the first weekly release (tag YYYY-MM-DD) of each quarter 2024-Q4 ... 2026-Q3, plus the campaign's 2026-09-21 and the newest.

- 2024-10-07 (released 2024-10-07; first of 2024-Q4)
- 2025-01-06 (released 2025-01-06; first of 2025-Q1)
- 2025-04-07 (released 2025-04-07; first of 2025-Q2)
- 2025-07-07 (released 2025-07-07; first of 2025-Q3) - UNAVAILABLE: RuntimeError: launch check failed (no diagnostics or hover on the smoke project): " "--lockfile-path" "<tmp>/smoke-rust-analyzer-7dhmsej0/target/rust-analyzer/m
- 2025-10-27 (released 2025-10-27; first of 2025-Q4)
- 2026-01-05 (released 2026-01-05; first of 2026-Q1)
- 2026-04-06 (released 2026-04-06; first of 2026-Q2)
- 2026-07-06 (released 2026-07-06; first of 2026-Q3)
- 2026-09-21 (released 2026-09-21; campaign)
- 2026-09-28 (released 2026-09-28; newest)

| cause | group | 2024-10-07 | 2025-01-06 | 2025-04-07 | 2025-07-07 | 2025-10-27 | 2026-01-05 | 2026-04-06 | 2026-07-06 | 2026-09-21 | 2026-09-28 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C28 | `rust-analyzer-r4-completioninsert-gained-completion-e99b79` | 3/3 reproduced | 0/3 unsettled | 3/3 reproduced | unavailable | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 0/3 not-reproduced |
| C29 | `rust-analyzer-r4-diagnostics-extra-e0063-mutation-m1-aeef82` | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | unavailable | 0/3 unsettled | 0/3 unsettled | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |

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
| C31 | `ts6-r1-inlayhint-changed-h9-b9d052` | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced |
| C30 | `ts6-r1-codeaction-extra-h5-f48d27` | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C32 | `ts6-r4-diagnostics-changed-1064-2322-quickfix-d597f5` | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C33 | `ts6-r4-diagnostics-changed-mutation-m1-34f06f` | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 0/3 unsettled | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C34 | `ts6-r4-diagnostics-extra-17002-2552-mutation-m1-727795` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C35 | `ts6-r4-diagnostics-extra-2448-7022-mutation-m1-e5d199` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |

## pyright

Rule: the first stable release (npm `time`) of each quarter 2024-Q4 ... 2026-Q3, plus the campaign's 1.1.414 and the newest (as the rust-analyzer rule: both lines release about weekly); installed as the benchmark installs pyright (npm pyright@<v>, scripts/lsptest/bench/install_builds.py).

- 1.1.383 (released 2024-10-01; first of 2024-Q4)
- 1.1.392 (released 2025-01-15; first of 2025-Q1)
- 1.1.399 (released 2025-04-09; first of 2025-Q2)
- 1.1.403 (released 2025-07-08; first of 2025-Q3)
- 1.1.406 (released 2025-10-01; first of 2025-Q4)
- 1.1.408 (released 2026-01-08; first of 2026-Q1)
- 1.1.409 (released 2026-04-16; first of 2026-Q2)
- 1.1.412 (released 2026-08-12; first of 2026-Q3)
- 1.1.414 (released 2026-09-09; campaign, newest)

| cause | group | 1.1.383 | 1.1.392 | 1.1.399 | 1.1.403 | 1.1.406 | 1.1.408 | 1.1.409 | 1.1.412 | 1.1.414 |
|---|---|---|---|---|---|---|---|---|---|---|
| C17 | `pyright-r0-references-result-error-32603-fresh-pair-2718c4` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C18 | `pyright-r1-hover-text-h2-fb2ed0` | 0/3 not-reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C19 | `pyright-r1-hover-text-h5-f24c4e` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C20 | `pyright-r1-references-extra-h9-37c1a2` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C21 | `pyright-r1-signaturehelp-changed-h9-846c6c` | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 0/3 not-reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
| C22 | `pyright-r4-completioninsert-gained-completion-79a584` | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced | 3/3 reproduced |
