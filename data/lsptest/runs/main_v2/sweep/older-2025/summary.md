# Version sweep `older-2025`

Each triage group's representative replayed on another build of its server; reproduced = every replay reproduced the violation, not-reproduced = every replay settled with agreeing controls and none reproduced.

| from kind | build | reproduced | not-reproduced | flaky | unsettled | error | skipped |
|---|---|---|---|---|---|---|---|
| gopls | gopls v0.20.0 | 27 | 2 | 0 | 1 | 0 | 0 |
| pyright | pyright 1.1.406 | 16 | 1 | 0 | 0 | 0 | 0 |
| rust-analyzer | rust-analyzer 2025-10-27 | 6 | 3 | 1 | 4 | 0 | 0 |
| ts6 | tsserver 5.9.3+tsls5.0.0 | 34 | 2 | 0 | 3 | 0 | 0 |
| ts7 | - - | 0 | 0 | 0 | 0 | 0 | 21 |

| oracle | reproduced | not-reproduced | flaky | unsettled | error | skipped |
|---|---|---|---|---|---|---|
| r0_crash | 1 | 0 | 0 | 0 | 0 | 0 |
| r1_history | 29 | 5 | 0 | 2 | 0 | 1 |
| r2_handles | 1 | 0 | 0 | 1 | 0 | 0 |
| r3_routes | 14 | 3 | 1 | 0 | 0 | 5 |
| r4_edits | 29 | 0 | 0 | 5 | 0 | 4 |
| r5_transforms | 9 | 0 | 0 | 0 | 0 | 1 |
| r6_crossimpl | 0 | 0 | 0 | 0 | 0 | 10 |

| group | from | build | verdict | reproduced | settled | seconds |
|---|---|---|---|---|---|---|
| gopls-r1-codeaction-changed-h4-c5344e | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 75.0 |
| gopls-r1-codeaction-changed-h7-383b05 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 115.8 |
| gopls-r1-codeaction-key-lost-h7-547744 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 81.0 |
| gopls-r1-completion-extra-h5-2dfa5a | gopls | gopls v0.20.0 | not-reproduced | 0/3 | 3/3 | 185.3 |
| gopls-r1-completion-extra-h6-410566 | gopls | gopls v0.20.0 | unsettled | 2/3 | 3/3 | 200.3 |
| gopls-r1-completion-extra-h8-02679b | gopls | gopls v0.20.0 | not-reproduced | 0/3 | 3/3 | 40.3 |
| gopls-r1-completion-lost-h7-1a1169 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 1916.6 |
| gopls-r1-diagnostics-message-h5-e59f2c | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 68.9 |
| gopls-r1-diagnostics-missing-h7-10a910 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 79.9 |
| gopls-r1-references-extra-h5-e2e003 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 149.8 |
| gopls-r2-codeactionresolve-changed-codeaction-70b3e9 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 34.0 |
| gopls-r3-definitionconsistency-changed-d-cf67f4 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 27.2 |
| gopls-r3-definitionconsistency-result-error-0-d-f91fb9 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 49.4 |
| gopls-r3-highlightvsreferences-extra-c-84be95 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 25.4 |
| gopls-r4-completioninsert-gained-completion-22daf7 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 63.2 |
| gopls-r4-diagnostics-extra-incompatibleassign-inv-mutation-m2-3cfa07 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 47.4 |
| gopls-r4-diagnostics-extra-incompatibleassign-mutation-m2-ade1f0 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 45.0 |
| gopls-r4-diagnostics-extra-mismatchedtypes-mutation-m2-dc6e94 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 50.9 |
| gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 46.8 |
| gopls-r4-diagnostics-extra-notatype-mutation-m2-477181 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 45.6 |
| gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 42.1 |
| gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 42.3 |
| gopls-r4-diagnostics-extra-unusedimport-mutation-m3-aefa9e | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 45.7 |
| gopls-r4-diagnostics-extra-wrongargcount-mutation-m3-ac10cc | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 53.1 |
| gopls-r5-codeaction-extra-t1-6dfb45 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 43.5 |
| gopls-r5-codeaction-extra-t2-86a8ac | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 40.3 |
| gopls-r5-foldingrange-changed-t4-b07c86 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 50.3 |
| gopls-r5-foldingrange-changed-t6-ecacad | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 44.4 |
| gopls-r5-semantictokens-changed-t4-b423af | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 50.8 |
| gopls-r5-semantictokens-extra-t4-867006 | gopls | gopls v0.20.0 | reproduced | 3/3 | 3/3 | 40.2 |
| pyright-r0-references-result-error-32603-fresh-pair-2718c4 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 10.6 |
| pyright-r1-definition-extra-h5-2e7477 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 67.6 |
| pyright-r1-definition-missing-h5-964341 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 93.3 |
| pyright-r1-hover-text-h2-fb2ed0 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 110.4 |
| pyright-r1-hover-text-h5-f24c4e | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 92.8 |
| pyright-r1-hover-text-h8-2a8227 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 46.6 |
| pyright-r1-references-extra-h4-a63d47 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 74.6 |
| pyright-r1-references-extra-h9-37c1a2 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 34.9 |
| pyright-r1-references-missing-h5-64453c | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 90.7 |
| pyright-r1-signaturehelp-changed-h9-846c6c | pyright | pyright 1.1.406 | not-reproduced | 0/3 | 3/3 | 39.7 |
| pyright-r1-typedefinition-extra-h2-764582 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 98.8 |
| pyright-r1-typedefinition-extra-h8-9c51fd | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 47.0 |
| pyright-r3-definitionconsistency-extra-d-3d112f | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 20.0 |
| pyright-r3-definitionconsistency-lost-d-a4eaed | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 38.7 |
| pyright-r3-definitionconsistency-missing-d-81a7e5 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 19.5 |
| pyright-r3-highlightvsreferences-gained-c-3118cc | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 19.8 |
| pyright-r4-completioninsert-gained-completion-79a584 | pyright | pyright 1.1.406 | reproduced | 3/3 | 3/3 | 49.5 |
| rust-analyzer-r2-completionresolve-changed-completion-3170a1 | rust-analyzer | rust-analyzer 2025-10-27 | unsettled | 0/3 | 3/3 | 45.9 |
| rust-analyzer-r3-definitionconsistency-changed-d-2c6179 | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 53.4 |
| rust-analyzer-r3-definitionconsistency-missing-d-586fd8 | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 47.2 |
| rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0 | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 65.3 |
| rust-analyzer-r3-diagnostics-missing-unlinked-file-a-efb484 | rust-analyzer | rust-analyzer 2025-10-27 | flaky | 1/3 | 3/3 | 68.9 |
| rust-analyzer-r3-highlightvsreferences-extra-c-c2bfed | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 47.1 |
| rust-analyzer-r3-semantictokensrange-changed-b-b6e28b | rust-analyzer | rust-analyzer 2025-10-27 | not-reproduced | 0/3 | 3/3 | 46.7 |
| rust-analyzer-r4-completioninsert-gained-completion-e99b79 | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 91.6 |
| rust-analyzer-r4-diagnostics-extra-e0063-mutation-m1-aeef82 | rust-analyzer | rust-analyzer 2025-10-27 | unsettled | 0/3 | 3/3 | 34.1 |
| rust-analyzer-r4-diagnostics-extra-e0560-mutation-m2-1f508d | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 95.4 |
| rust-analyzer-r4-diagnostics-extra-inactive-code-quickfix-f2d641 | rust-analyzer | rust-analyzer 2025-10-27 | unsettled | 0/3 | 3/3 | 45.8 |
| rust-analyzer-r4-syntax-gained-mutation-m1-7af5e4 | rust-analyzer | rust-analyzer 2025-10-27 | unsettled | 0/3 | 3/3 | 34.5 |
| rust-analyzer-r5-codeaction-changed-t6-4ee734 | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 87.8 |
| rust-analyzer-r5-documentsymbol-changed-t6-a3a950 | rust-analyzer | rust-analyzer 2025-10-27 | reproduced | 3/3 | 3/3 | 80.0 |
| ts6-r1-codeaction-extra-h5-f48d27 | ts6 | tsserver 5.9.3+tsls5.0.0 | unsettled | 0/3 | 3/3 | 65.8 |
| ts6-r1-codeaction-key-lost-h8-3e0e0f | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 107.6 |
| ts6-r1-completion-lost-h9-ce1ffc | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 375.8 |
| ts6-r1-definition-lost-h9-898f29 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 241.3 |
| ts6-r1-diagnostics-extra-2307-7006-h9-8325a2 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 175.2 |
| ts6-r1-diagnostics-moved-2875-h8-751ff9 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 110.7 |
| ts6-r1-documenthighlight-missing-h9-2e657a | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 229.1 |
| ts6-r1-hover-text-h5-b3855d | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 187.7 |
| ts6-r1-hover-text-h8-2ce168 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 75.9 |
| ts6-r1-inlayhint-changed-h8-8f6569 | ts6 | tsserver 5.9.3+tsls5.0.0 | not-reproduced | 0/3 | 3/3 | 75.6 |
| ts6-r1-inlayhint-changed-h9-b9d052 | ts6 | tsserver 5.9.3+tsls5.0.0 | not-reproduced | 0/3 | 3/3 | 457.6 |
| ts6-r1-references-missing-h5-cc8950 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 205.5 |
| ts6-r1-semantictokens-changed-h9-c4368c | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 147.9 |
| ts6-r1-signaturehelp-changed-h5-db5a5e | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 159.2 |
| ts6-r1-typedefinition-lost-h9-b52749 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 218.0 |
| ts6-r3-definitionconsistency-changed-d-bf619d | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 95.1 |
| ts6-r3-definitionconsistency-extra-d-1fb668 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 99.2 |
| ts6-r3-definitionconsistency-lost-d-fb78dd | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 136.4 |
| ts6-r3-definitionconsistency-missing-d-0ab4de | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 168.6 |
| ts6-r3-highlightvsreferences-gained-c-e8db7c | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 82.6 |
| ts6-r4-diagnostics-changed-1064-2322-quickfix-d597f5 | ts6 | tsserver 5.9.3+tsls5.0.0 | unsettled | 0/3 | 3/3 | 50.1 |
| ts6-r4-diagnostics-changed-mutation-m1-34f06f | ts6 | tsserver 5.9.3+tsls5.0.0 | unsettled | 0/3 | 3/3 | 39.7 |
| ts6-r4-diagnostics-extra-17000-mutation-m3-07673d | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 360.9 |
| ts6-r4-diagnostics-extra-17002-2552-mutation-m1-727795 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 163.8 |
| ts6-r4-diagnostics-extra-2304-mutation-m2-1554be | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 330.8 |
| ts6-r4-diagnostics-extra-2322-2345-mutation-m1-2566f2 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 84.2 |
| ts6-r4-diagnostics-extra-2322-mutation-m1-dc576a | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 186.4 |
| ts6-r4-diagnostics-extra-2322-mutation-m3-1879f3 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 187.9 |
| ts6-r4-diagnostics-extra-2339-6133-mutation-m1-4cd363 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 112.4 |
| ts6-r4-diagnostics-extra-2345-2554-mutation-m1-d523d0 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 191.6 |
| ts6-r4-diagnostics-extra-2353-mutation-m1-2b6bdb | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 175.1 |
| ts6-r4-diagnostics-extra-2448-7022-mutation-m1-e5d199 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 171.4 |
| ts6-r4-diagnostics-extra-2552-mutation-m2-f7e816 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 216.8 |
| ts6-r4-diagnostics-extra-2554-mutation-m3-d2ab31 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 214.0 |
| ts6-r4-diagnostics-extra-2555-mutation-m3-8de4a9 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 229.2 |
| ts6-r4-diagnostics-extra-2558-2604-mutation-m1-e220b8 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 112.7 |
| ts6-r4-diagnostics-extra-2604-mutation-m1-0e3b68 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 111.7 |
| ts6-r4-syntax-gained-mutation-m1-7e3417 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 112.8 |
| ts6-r5-foldingrange-extra-t2-625065 | ts6 | tsserver 5.9.3+tsls5.0.0 | reproduced | 3/3 | 3/3 | 73.1 |
| ts7-r1-hover-text-h8-500422 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-definitionconsistency-changed-d-a42b32 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-definitionconsistency-extra-d-fb74d3 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-definitionconsistency-lost-d-0129b3 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-definitionconsistency-missing-d-560852 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r3-highlightvsreferences-gained-c-9f16d3 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r4-diagnostics-extra-2322-2345-mutation-m1-5efcb9 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r4-diagnostics-extra-2322-mutation-m1-e5a893 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r4-diagnostics-extra-2353-mutation-m1-cf35f5 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r4-diagnostics-extra-2558-2604-mutation-m1-ead3ee | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r5-foldingrange-extra-t2-5dd83a | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-completion-changed-completion-997cb3 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-completion-missing-completion-60ede6 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-definition-changed-definition-1c2318 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-definition-extra-definition-d8e982 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-definition-gained-definition-24364e | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-diagnostics-missing-2304-2339-2593-diagnostics-31eb88 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-diagnostics-missing-2304-2593-diagnostics-58256c | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-diagnostics-missing-80006-diagnostics-da3300 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-hover-changed-hover-e5c91e | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
| ts7-r6-hover-lost-hover-feed64 | ts7 |   | skipped | 0/0 | 0/0 | 0.0 |
