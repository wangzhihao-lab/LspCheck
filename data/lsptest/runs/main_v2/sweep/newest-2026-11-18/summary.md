# Release sweep `newest-2026-11-18` (releases published up to 2026-11-18)

Cell: reproduced/replays and the frozen sweep's verdict; n/a (Go) = not replayable (the project needs a newer Go than the build runs); unavailable = not installable or not launchable; not run = pending. Rules, release dates and install details: releases.json.

## gopls

Rule: newest stable version on proxy.golang.org.

- v0.24.0 (released 2026-10-14; newest; runs go1.27.1)

| cause | group | v0.24.0 |
|---|---|---|
| C3 | `gopls-r2-codeactionresolve-changed-codeaction-70b3e9` | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-incompatibleassign-mutation-m2-ade1f0` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-mismatchedtypes-mutation-m2-dc6e94` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a` | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-notatype-mutation-m2-477181` | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70` | 0/3 unsettled |
| C7 | `gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c` | 3/3 reproduced |
| C9 | `gopls-r1-references-extra-h5-e2e003` | 3/3 reproduced |
| C12 | `gopls-r1-codeaction-changed-h4-c5344e` | 3/3 reproduced |
| C12 | `gopls-r1-codeaction-changed-h7-383b05` | 3/3 reproduced |
| C13 | `gopls-r1-codeaction-key-lost-h7-547744` | 3/3 reproduced |
| C13 | `gopls-r1-diagnostics-missing-h7-10a910` | 3/3 reproduced |
| C14 | `gopls-r1-completion-lost-h7-1a1169` | 3/3 reproduced |
| C13 | `gopls-r1-diagnostics-message-h5-e59f2c` | 3/3 reproduced |
| C15 | `gopls-r4-diagnostics-extra-unusedimport-mutation-m3-aefa9e` | 3/3 reproduced |
| C16 | `gopls-r5-foldingrange-changed-t4-b07c86` | 3/3 reproduced |
| C16 | `gopls-r5-semantictokens-changed-t4-b423af` | 3/3 reproduced |
| C16 | `gopls-r5-semantictokens-extra-t4-867006` | 3/3 reproduced |

## rust-analyzer

Rule: newest weekly GitHub release (tag YYYY-MM-DD).

- 2026-11-16 (released 2026-11-16; newest)

| cause | group | 2026-11-16 |
|---|---|---|
| C4 | `rust-analyzer-r2-completionresolve-changed-completion-3170a1` | 3/3 reproduced |
| C25 | `rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0` | 0/3 not-reproduced |
| C25 | `rust-analyzer-r3-diagnostics-missing-unlinked-file-a-efb484` | 0/3 not-reproduced |
| C26 | `rust-analyzer-r3-semantictokensrange-changed-b-b6e28b` | 3/3 reproduced |
| C28 | `rust-analyzer-r4-completioninsert-gained-completion-e99b79` | 0/3 not-reproduced |
| C29 | `rust-analyzer-r4-diagnostics-extra-e0063-mutation-m1-aeef82` | 3/3 reproduced |
| C29 | `rust-analyzer-r4-syntax-gained-mutation-m1-7af5e4` | 3/3 reproduced |

## ts6

Rule: newest TypeScript 6.x with the newest typescript-language-server (npm).

- 6.0.3+tsls6.1.0 (released 2026-04-16; newest; wrapper released 2026-11-12)

| cause | group | 6.0.3+tsls6.1.0 |
|---|---|---|
| C1 | `ts6-r1-completion-lost-h9-ce1ffc` | 3/3 reproduced |
| C1 | `ts6-r1-definition-lost-h9-898f29` | 3/3 reproduced |
| C1 | `ts6-r1-diagnostics-extra-2307-7006-h9-8325a2` | 3/3 reproduced |
| C1 | `ts6-r1-documenthighlight-missing-h9-2e657a` | 2/3 flaky |
| C31 | `ts6-r1-inlayhint-changed-h9-b9d052` | 0/3 not-reproduced |
| C1 | `ts6-r1-references-missing-h5-cc8950` | 3/3 reproduced |
| C1 | `ts6-r1-semantictokens-changed-h9-c4368c` | 2/3 flaky |
| C1 | `ts6-r1-typedefinition-lost-h9-b52749` | 3/3 reproduced |
| C11 | `ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3` | 3/3 reproduced |
| C30 | `ts6-r1-codeaction-extra-h5-f48d27` | 3/3 reproduced |
| C2 | `ts6-r1-codeaction-key-lost-h8-3e0e0f` | 3/3 reproduced |
| C2 | `ts6-r1-diagnostics-moved-2875-h8-751ff9` | 3/3 reproduced |
| C32 | `ts6-r4-diagnostics-changed-1064-2322-quickfix-d597f5` | 3/3 reproduced |
| C33 | `ts6-r4-diagnostics-changed-mutation-m1-34f06f` | 3/3 reproduced |
| C34 | `ts6-r4-diagnostics-extra-17002-2552-mutation-m1-727795` | 3/3 reproduced |
| C34 | `ts6-r4-syntax-gained-mutation-m1-7e3417` | 3/3 reproduced |
| C35 | `ts6-r4-diagnostics-extra-2448-7022-mutation-m1-e5d199` | 3/3 reproduced |

## pyright

Rule: newest stable pyright (npm).

- 1.1.414 (released 2026-09-09; newest, campaign)

| cause | group | 1.1.414 |
|---|---|---|
| C17 | `pyright-r0-references-result-error-32603-fresh-pair-2718c4` | 3/3 reproduced |
| C18 | `pyright-r1-hover-text-h2-fb2ed0` | 3/3 reproduced |
| C18 | `pyright-r1-hover-text-h8-2a8227` | 3/3 reproduced |
| C19 | `pyright-r1-hover-text-h5-f24c4e` | 3/3 reproduced |
| C20 | `pyright-r1-references-extra-h9-37c1a2` | 3/3 reproduced |
| C21 | `pyright-r1-signaturehelp-changed-h9-846c6c` | 3/3 reproduced |
| C22 | `pyright-r4-completioninsert-gained-completion-79a584` | 3/3 reproduced |
