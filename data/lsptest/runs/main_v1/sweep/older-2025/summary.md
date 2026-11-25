# Version sweep `older-2025`

Each triage group's representative replayed on another build of its server; reproduced = every replay reproduced the violation, not-reproduced = every replay settled with agreeing controls and none reproduced.

| from kind | build | reproduced | not-reproduced | flaky | unsettled | error | skipped |
|---|---|---|---|---|---|---|---|
| gopls | gopls v0.20.0 | 17 | 1 | 0 | 1 | 0 | 0 |
| pyright | pyright 1.1.406 | 11 | 0 | 0 | 0 | 0 | 0 |
| rust-analyzer | rust-analyzer 2025-10-27 | 2 | 10 | 0 | 2 | 0 | 0 |
| ts6 | tsserver 5.9.3+tsls5.0.0 | 33 | 1 | 4 | 0 | 0 | 0 |
| ts7 | - - | 0 | 0 | 0 | 0 | 0 | 24 |

| oracle | reproduced | not-reproduced | flaky | unsettled | error | skipped |
|---|---|---|---|---|---|---|
| r0_crash | 0 | 2 | 0 | 0 | 0 | 0 |
| r1_history | 20 | 2 | 4 | 1 | 0 | 2 |
| r2_handles | 1 | 0 | 0 | 1 | 0 | 0 |
| r3_routes | 13 | 7 | 0 | 0 | 0 | 4 |
| r4_edits | 23 | 1 | 0 | 1 | 0 | 2 |
| r5_transforms | 6 | 0 | 0 | 0 | 0 | 3 |
| r6_crossimpl | 0 | 0 | 0 | 0 | 0 | 13 |

| group | from | build | verdict | reproduced | settled | seconds |
|---|---|---|---|---|---|---|
| gopls-r1-codeaction-changed-h4-c5344e | gopls | gopls v0.20.0 | unsettled | 0/3 | 3/3 | 112.7 |
| gopls-r1-completion-extra-h5-2dfa5a | gopls | gopls v0.20.0 | not-reproduced | 0/3 | 3/3 | 170.7 |
| gopls-r1-references-extra-h9-0290a7 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 29.8 |
| gopls-r2-codeactionresolve-changed-codeaction-70b3e9 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 29.4 |
| gopls-r3-definitionconsistency-changed-d-cf67f4 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 40.1 |
| gopls-r3-highlightvsreferences-extra-c-84be95 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 26.7 |
| gopls-r4-diagnostics-extra-invalidifaceassign-mutation-m2-416e90 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 48.0 |
| gopls-r4-diagnostics-extra-mutation-m2-111975 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 45.2 |
| gopls-r4-diagnostics-extra-nonindexableoperand-mutation-m2-ba152b | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 46.6 |
| gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 49.0 |
| gopls-r4-diagnostics-extra-notatype-mutation-m2-477181 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 43.5 |
| gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 43.4 |
| gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 55.0 |
| gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 52.1 |
| gopls-r4-diagnostics-extra-wrongargcount-mutation-m3-ac10cc | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 50.1 |
| gopls-r4-syntax-gained-mutation-m2-86fde3 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 44.9 |
| gopls-r5-codeaction-extra-t1-6dfb45 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 36.6 |
| gopls-r5-codeaction-extra-t2-86a8ac | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 55.0 |
| gopls-r5-foldingrange-changed-t6-ecacad | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 53.7 |
| pyright-r1-references-extra-h4-a63d47 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 218.1 |
| pyright-r1-references-extra-h5-181832 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 27.5 |
| pyright-r1-references-extra-h8-98dfb1 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 19.1 |
| pyright-r1-references-missing-h3-876306 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 82.2 |
| pyright-r1-references-missing-h5-64453c | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 19.4 |
| pyright-r3-definitionconsistency-extra-d-3d112f | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 18.4 |
| pyright-r3-definitionconsistency-lost-d-a4eaed | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 35.0 |
| pyright-r3-definitionconsistency-missing-d-81a7e5 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 18.6 |
| pyright-r3-highlightvsreferences-gained-c-3118cc | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 18.1 |
| pyright-r4-completioninsert-gained-completion-79a584 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 49.8 |
| pyright-r5-definition-lost-t1-ae8275 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 29.5 |
| rust-analyzer-r0-references-result-error-timeout-fresh-pair-8a4b8d | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 32.8 |
| rust-analyzer-r0-semantictokens-result-error-timeout-fresh-pair-62256f | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 27.9 |
| rust-analyzer-r2-completionresolve-changed-completion-3170a1 | rust-analyzer | rust-analyzer 2025-10-27 | unsettled | 0/3 | 3/3 | 16.8 |
| rust-analyzer-r3-definitionconsistency-changed-d-2c6179 | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 35.1 |
| rust-analyzer-r3-definitionconsistency-extra-d-4cbc9e | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 56.7 |
| rust-analyzer-r3-definitionconsistency-missing-d-586fd8 | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 56.5 |
| rust-analyzer-r3-diagnostics-extra-non-snake-case-a-52ba0b | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 50.3 |
| rust-analyzer-r3-diagnostics-extra-unlinked-file-a-751ce1 | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 50.6 |
| rust-analyzer-r3-diagnostics-missing-e0004-inactive-code-a-731c4f | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 49.1 |
| rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0 | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 49.3 |
| rust-analyzer-r3-highlightvsreferences-extra-c-c2bfed | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 34.4 |
| rust-analyzer-r3-semantictokensrange-changed-b-b6e28b | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 35.3 |
| rust-analyzer-r4-completioninsert-gained-completion-e99b79 | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 79.6 |
| rust-analyzer-r4-diagnostics-extra-inactive-code-quickfix-f2d641 | rust-analyzer | rust-analyzer 2025-10-27 | unsettled | 0/3 | 3/3 | 37.7 |
| ts6-r1-codeaction-key-lost-h5-4f92e2 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 77.8 |
| ts6-r1-completion-lost-h5-fa501c | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 77.6 |
| ts6-r1-definition-lost-h5-61a0fd | ts6 | tsserver 5.9.3+tsls5.0.0 | flaky | 2/3 | 3/3 | 53.1 |
| ts6-r1-definition-lost-h9-898f29 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 450.1 |
| ts6-r1-diagnostics-extra-2304-h7-8ca52f | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 64.8 |
| ts6-r1-diagnostics-extra-2305-2339-7006-h5-d5a250 | ts6 | tsserver 5.9.3+tsls5.0.0 | flaky | 2/3 | 3/3 | 70.1 |
| ts6-r1-documenthighlight-lost-h5-9b4675 | ts6 | tsserver 5.9.3+tsls5.0.0 | flaky | 2/3 | 3/3 | 80.9 |
| ts6-r1-hover-text-h2-284519 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 172.7 |
| ts6-r1-hover-text-h5-b3855d | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 220.2 |
| ts6-r1-hover-text-h8-2ce168 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 157.2 |
| ts6-r1-inlayhint-changed-h5-0c1aa5 | ts6 | tsserver 5.9.3+tsls5.0.0 | not-reproduced | 0/3 | 3/3 | 173.0 |
| ts6-r1-references-extra-h6-6e0a73 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 100.1 |
| ts6-r1-references-lost-h5-d24ca6 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 107.1 |
| ts6-r1-references-missing-h5-cc8950 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 71.3 |
| ts6-r1-semantictokens-changed-h5-591c42 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 110.4 |
| ts6-r1-semantictokens-missing-h9-d686b3 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 83.7 |
| ts6-r1-signaturehelp-changed-h5-db5a5e | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 77.2 |
| ts6-r1-signaturehelp-lost-h9-7bd793 | ts6 | tsserver 5.9.3+tsls5.0.0 | flaky | 2/3 | 3/3 | 240.3 |
| ts6-r1-typedefinition-lost-h5-712a35 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 72.4 |
| ts6-r3-definitionconsistency-changed-d-bf619d | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 86.3 |
| ts6-r3-definitionconsistency-extra-d-1fb668 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 238.0 |
| ts6-r3-definitionconsistency-lost-d-fb78dd | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 52.6 |
| ts6-r3-definitionconsistency-missing-d-0ab4de | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 56.8 |
| ts6-r3-highlightvsreferences-gained-c-e8db7c | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 78.5 |
| ts6-r4-diagnostics-extra-18004-mutation-m2-63d36d | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 156.7 |
| ts6-r4-diagnostics-extra-2304-mutation-m2-1554be | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 133.1 |
| ts6-r4-diagnostics-extra-2322-2552-2554-mutation-m1-6d8de2 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 78.5 |
| ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 113.1 |
| ts6-r4-diagnostics-extra-2339-2349-2352-mutation-m1-66b5a5 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 254.1 |
| ts6-r4-diagnostics-extra-2339-7053-mutation-m1-2aad71 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 54.9 |
| ts6-r4-diagnostics-extra-2339-mutation-m1-a8c765 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 134.4 |
| ts6-r4-diagnostics-extra-2448-7022-mutation-m1-e5d199 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 61.6 |
| ts6-r4-diagnostics-extra-2552-mutation-m1-da2133 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 66.3 |
| ts6-r4-diagnostics-extra-2552-mutation-m2-f7e816 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 56.3 |
| ts6-r4-diagnostics-extra-2554-mutation-m3-d2ab31 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 82.5 |
| ts6-r4-diagnostics-extra-2678-mutation-m1-7b3f3b | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 60.7 |
| ts6-r5-foldingrange-changed-t2-ec7247 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 34.9 |
| ts6-r5-foldingrange-extra-t2-625065 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 168.2 |
| ts7-r1-references-extra-h6-574e94 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r1-references-missing-h9-2dd24a | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-definitionconsistency-changed-d-a42b32 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-definitionconsistency-extra-d-fb74d3 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-definitionconsistency-missing-d-560852 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-highlightvsreferences-gained-c-9f16d3 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r4-diagnostics-extra-2339-2349-2352-mutation-m1-47c762 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r4-diagnostics-extra-2339-mutation-m1-12bd0a | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r5-documentsymbol-changed-t3-8eae6d | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r5-foldingrange-changed-t2-5985a9 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r5-foldingrange-extra-t2-5dd83a | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-completion-changed-completion-997cb3 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-completion-extra-completion-afe533 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-completion-gained-completion-4b6660 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-completion-missing-completion-60ede6 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-definition-changed-definition-1c2318 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-definition-extra-definition-d8e982 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-definition-gained-definition-24364e | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-diagnostics-changed-2322-2503-2591-diagnostics-dee939 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-diagnostics-missing-2304-2593-diagnostics-58256c | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-diagnostics-missing-80006-diagnostics-da3300 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-diagnostics-moved-6133-diagnostics-5e7a2f | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-hover-changed-hover-e5c91e | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-hover-lost-hover-feed64 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
