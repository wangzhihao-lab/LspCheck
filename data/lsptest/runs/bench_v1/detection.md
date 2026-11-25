# Detection of reproduced historical bugs: campaign bench_v1

A case is detected when an oracle confirms (3/3) a signature on the pre-fix build that it does not confirm on the post-fix build. `author_match` is for the author: does the signature show the case's reported bug?

- cases with a generic ground-truth probe: 74 (69 with every run finished), detected 38; by oracle {'r0_crash': 2, 'r1_history': 12, 'r2_handles': 2, 'r3_routes': 5, 'r4_edits': 19, 'r5_transforms': 3}
- cases whose ground truth used the specification probe edit_text_differs (reported separately): 6 (5 finished), detected 1; by oracle {'r4_edits': 1}

## Cases (generic ground-truth probes)

| case | kind | class / subtype | ground-truth probe | builds | detected | oracles with pre-only signatures | runs finished |
|---|---|---|---|---|---|---|---|
| gopls-36824 | gopls | R4 / organize | edit_leaves_diagnostic | v0.4.1 -> v0.4.2 | yes | r1_history, r4_edits | yes |
| gopls-38424 | gopls | R1 / edit-undo | differs_from_fresh | v0.4.3 -> v0.4.4 | yes | r1_history | yes |
| gopls-38732 | gopls | R1 / edit-undo | differs_from_fresh | v0.6.6 -> v0.6.7 | yes | r1_history | yes |
| gopls-41057 | gopls | R4 / format | edit_breaks_syntax | v0.4.4 -> v0.5.0 | no | - | yes |
| gopls-42254 | gopls | R3 / def-consistency | two_routes_differ | v0.5.3 -> v0.5.4 | yes | r3_routes | yes |
| gopls-43144 | gopls | R1 / open-close | two_routes_differ | v0.9.5 -> v0.10.0 | yes | r5_transforms | yes |
| gopls-46436 | gopls | R4 / completion | edit_breaks_syntax | v0.7.0 -> v0.7.1 | no | - | yes |
| gopls-46667 | gopls | R1 / edit-undo | differs_from_fresh | v0.7.0 -> v0.7.1 | no | - | yes |
| gopls-47436 | gopls | R1 / edit-undo | differs_from_fresh | v0.7.1 -> v0.7.2 | no | - | yes |
| gopls-52500 | gopls | R1 / edit-undo | differs_from_fresh | v0.8.3 -> v0.8.4 | yes | r1_history | yes |
| gopls-52981 | gopls | R1 / typing | differs_from_fresh | v0.8.4 -> v0.9.0 | no | - | yes |
| gopls-54147 | gopls | R1 / typing | differs_from_fresh | v0.9.1 -> v0.9.2 | no | - | yes |
| gopls-57480 | gopls | R4 / completion | edit_breaks_syntax | v0.11.0 -> v0.12.0 | no | - | yes |
| gopls-60435 | gopls | R3 / highlight-refs | two_routes_differ | v0.12.0 -> v0.12.1 | yes | r3_routes | yes |
| gopls-62141 | gopls | R4 / completion | edit_breaks_syntax | v0.13.2 -> v0.14.0 | yes | r4_edits | yes |
| gopls-73269 | gopls | R4 / quickfix | edit_leaves_diagnostic | v0.18.1 -> v0.19.0 | yes | r4_edits | yes |
| gopls-73564 | gopls | R4 / quickfix | edit_leaves_diagnostic | v0.18.1 -> v0.19.0 | yes | r4_edits | yes |
| gopls-73576 | gopls | R4 / quickfix | edit_breaks_syntax | v0.18.1 -> v0.19.0 | yes | r2_handles, r4_edits | yes |
| gopls-73661 | gopls | R4 / quickfix | edit_leaves_diagnostic | v0.18.1 -> v0.19.0 | yes | r4_edits | yes |
| gopls-74708 | gopls | R4 / quickfix | edit_breaks_syntax | v0.20.0 -> v0.21.0 | yes | r4_edits | yes |
| gopls-74709 | gopls | R4 / quickfix | edit_breaks_syntax | v0.20.0 -> v0.21.0 | yes | r4_edits | yes |
| gopls-74938 | gopls | R4 / quickfix | edit_leaves_diagnostic | v0.20.0 -> v0.21.0 | no | - | yes |
| jdtls-2111 | jdtls | R2 / stale-handle | stale_code_action | 1.12.0 -> 1.13.0 | yes | r2_handles | yes |
| jdtls-3155 | jdtls | R1 / dependency-edit | differs_from_fresh | 1.36.0 -> 1.37.0 | yes | r0_crash, r1_history | no |
| pyright-2759 | pyright | R1 / query-order | differs_from_fresh | 1.1.199 -> 1.1.200 | no | - | yes |
| pyright-2983 | pyright | R1 / query-order | differs_from_fresh | 1.1.232 -> 1.1.233 | no | - | yes |
| pyright-3482 | pyright | R1 / edit-undo | differs_from_fresh | 1.1.247 -> 1.1.248 | yes | r1_history | yes |
| pyright-3504 | pyright | R1 / query-order | diagnostic_present | 1.1.250 -> 1.1.251 | no | - | yes |
| pyright-3585 | pyright | R1 / query-order | diagnostic_absent | 1.1.254 -> 1.1.255 | no | - | yes |
| pyright-4844 | pyright | R1 / query-order | diagnostic_present | 1.1.300 -> 1.1.301 | yes | r1_history | yes |
| pyright-6629 | pyright | R1 / typing | diagnostic_present | 1.1.338 -> 1.1.339 | no | - | yes |
| pyright-7466 | pyright | R3 / other-route | differs_from_fresh | 1.1.363 -> 1.1.364 | no | - | yes |
| pyright-7516 | pyright | R1 / query-order | differs_from_fresh | 1.1.357 -> 1.1.358 | no | - | yes |
| pyright-8133 | pyright | R5 / whitespace | diagnostic_present | 1.1.367 -> 1.1.374 | no | - | yes |
| pyright-8946 | pyright | R1 / edit-undo | differs_from_fresh | 1.1.380 -> 1.1.381 | yes | r1_history | yes |
| pyright-9681 | pyright | R5 / crlf | transform_differs | 1.1.391 -> 1.1.392 | yes | r5_transforms | yes |
| rust-analyzer-10326 | rust-analyzer | R4 / quickfix | edit_breaks_syntax | 2026-07-06 -> 2026-07-13 | no | - | no |
| rust-analyzer-11897 | rust-analyzer | R4 / completion | edit_breaks_syntax | 2022-07-18 -> 2022-07-25 | no | - | yes |
| rust-analyzer-14841 | rust-analyzer | R3 / def-consistency | two_routes_differ | 2023-06-12 -> 2023-08-07 | yes | r5_transforms | yes |
| rust-analyzer-16556 | rust-analyzer | R4 / quickfix | edit_breaks_syntax | 2024-02-19 -> 2024-02-26 | yes | r4_edits | yes |
| rust-analyzer-16858 | rust-analyzer | R4 / quickfix | edit_breaks_syntax | 2024-04-15 -> 2024-04-22 | yes | r4_edits | yes |
| rust-analyzer-17525 | rust-analyzer | R4 / completion | edit_breaks_syntax | 2025-08-25 -> 2025-10-27 | yes | r1_history | yes |
| rust-analyzer-17728 | rust-analyzer | R4 / quickfix | edit_breaks_syntax | 2024-07-29 -> 2024-08-05 | yes | r4_edits | yes |
| rust-analyzer-18130 | rust-analyzer | R4 / completion | edit_breaks_syntax | 2024-09-16 -> 2024-09-30 | yes | r4_edits | yes |
| rust-analyzer-18144 | rust-analyzer | R5 / comment | transform_differs | 2024-09-16 -> 2024-09-30 | no | - | yes |
| rust-analyzer-18572 | rust-analyzer | R4 / completion | edit_breaks_syntax | 2026-04-13 -> 2026-04-20 | yes | r1_history | no |
| rust-analyzer-19694 | rust-analyzer | R4 / completion | edit_breaks_syntax | 2025-04-28 -> 2025-05-05 | yes | r3_routes | yes |
| rust-analyzer-20588 | rust-analyzer | R4 / quickfix | edit_breaks_syntax | 2025-08-25 -> 2025-10-27 | yes | r1_history | yes |
| rust-analyzer-20987 | rust-analyzer | R4 / completion | edit_breaks_syntax | 2025-12-15 -> 2025-12-22 | yes | r4_edits | yes |
| rust-analyzer-20998 | rust-analyzer | R4 / completion | edit_breaks_syntax | 2025-11-10 -> 2025-11-17 | no | - | no |
| rust-analyzer-21173 | rust-analyzer | R1 / edit-undo | error_response | 2025-12-08 -> 2025-12-15 | yes | r0_crash, r1_history, r3_routes | no |
| tsserver-29908 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 3.8.3+tsls0.4.0 -> 3.9.2+tsls0.4.0 | no | - | yes |
| tsserver-32068 | tsserver | R4 / format | edit_leaves_diagnostic | 3.5.3+tsls0.4.0 -> 3.6.2+tsls0.4.0 | yes | r4_edits | yes |
| tsserver-37830 | tsserver | R3 / def-consistency | two_routes_differ | 3.9.10+tsls0.4.0 -> 4.0.2+tsls0.4.0 | yes | r3_routes | yes |
| tsserver-41526 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.1.6+tsls0.5.1 -> 4.2.2+tsls0.5.1 | no | - | yes |
| tsserver-43278 | tsserver | R4 / quickfix | edit_breaks_syntax | 4.2.4+tsls0.5.1 -> 4.3.2+tsls0.5.1 | no | - | yes |
| tsserver-44123 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.3.5+tsls0.7.1 -> 4.4.2+tsls0.7.1 | yes | r4_edits | yes |
| tsserver-45270 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.3.5+tsls0.7.1 -> 4.4.2+tsls0.7.1 | no | - | yes |
| tsserver-45533 | tsserver | R4 / completion | edit_leaves_diagnostic | 4.4.4+tsls0.7.1 -> 4.5.2+tsls0.7.1 | no | - | yes |
| tsserver-46466 | tsserver | R4 / quickfix | edit_breaks_syntax | 4.4.4+tsls0.7.1 -> 4.5.2+tsls0.7.1 | yes | r4_edits | yes |
| tsserver-46564 | tsserver | R1 / edit-undo | edit_leaves_diagnostic | 4.4.4+tsls0.7.1 -> 4.5.2+tsls0.7.1 | no | - | yes |
| tsserver-48006 | tsserver | R4 / format | edit_breaks_syntax | 4.6.4+tsls0.10.1 -> 4.7.2+tsls0.10.1 | no | - | yes |
| tsserver-49001 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.7.4+tsls1.1.2 -> 4.8.2+tsls1.1.2 | no | - | yes |
| tsserver-49693 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.7.4+tsls1.1.2 -> 4.8.2+tsls1.1.2 | no | - | yes |
| tsserver-50076 | tsserver | R4 / format | edit_breaks_syntax | 4.7.4+tsls1.1.2 -> 4.8.2+tsls1.1.2 | no | - | yes |
| tsserver-50188 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.7.4+tsls1.1.2 -> 4.8.2+tsls1.1.2 | no | - | yes |
| tsserver-51667 | tsserver | R4 / completion | edit_breaks_syntax | 5.0.4+tsls3.3.2 -> 5.1.3+tsls3.3.2 | no | - | yes |
| tsserver-51920 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.9.5+tsls3.3.0 -> 5.0.2+tsls3.3.0 | yes | r4_edits | yes |
| tsserver-52274 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 4.9.5+tsls3.3.0 -> 5.0.2+tsls3.3.0 | yes | r4_edits | yes |
| tsserver-52675 | tsserver | R4 / completion | edit_breaks_syntax | 5.0.4+tsls3.3.2 -> 5.1.3+tsls3.3.2 | no | - | yes |
| tsserver-52792 | tsserver | R1 / open-close | error_response | 5.0.4+tsls3.3.2 -> 5.1.3+tsls3.3.2 | no | - | yes |
| tsserver-57497 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 5.4.5+tsls4.3.3 -> 5.5.2+tsls4.3.3 | no | - | yes |
| tsserver-59116 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 5.5.4+tsls4.3.3 -> 5.6.2+tsls4.3.3 | yes | r4_edits | yes |
| tsserver-60186 | tsserver | R4 / quickfix | edit_leaves_diagnostic | 5.6.3+tsls4.3.3 -> 5.7.2+tsls4.3.3 | no | - | yes |

## Cases whose ground truth used edit_text_differs

| case | kind | class / subtype | ground-truth probe | builds | detected | oracles with pre-only signatures | runs finished |
|---|---|---|---|---|---|---|---|
| gopls-72753 | gopls | R4 / completion | edit_text_differs | v0.18.1 -> v0.19.0 | no | - | yes |
| rust-analyzer-10618 | rust-analyzer | R4 / quickfix | edit_text_differs | 2026-04-06 -> 2026-04-13 | yes | r4_edits | no |
| rust-analyzer-17139 | rust-analyzer | R4 / quickfix | edit_text_differs | 2024-05-20 -> 2024-05-27 | no | - | yes |
| rust-analyzer-19758 | rust-analyzer | R4 / completion | edit_text_differs | 2025-05-05 -> 2025-05-12 | no | - | yes |
| rust-analyzer-21204 | rust-analyzer | R4 / quickfix | edit_text_differs | 2025-12-08 -> 2025-12-15 | no | - | yes |
| rust-analyzer-22281 | rust-analyzer | R4 / quickfix | edit_text_differs | 2026-05-11 -> 2026-05-18 | no | - | yes |

## Pre-only signatures

| case | oracle | signature | pre-fix violations | runs finished | author_match |
|---|---|---|---|---|---|
| gopls-36824 | r1_history | `gopls\|r1_history\|definition:result->error:0` | 0766542a976b-v03, c78cc37df9be-v00 | yes |  |
| gopls-36824 | r1_history | `gopls\|r1_history\|documentHighlight:lost` | 0766542a976b-v04, c78cc37df9be-v01 | yes |  |
| gopls-36824 | r1_history | `gopls\|r1_history\|documentSymbol:lost` | 0766542a976b-v05, c78cc37df9be-v02 | yes |  |
| gopls-36824 | r1_history | `gopls\|r1_history\|hover:changed` | 0766542a976b-v06, c78cc37df9be-v03 | yes |  |
| gopls-36824 | r1_history | `gopls\|r1_history\|hover:lost` | 0766542a976b-v07, c78cc37df9be-v04 | yes |  |
| gopls-36824 | r1_history | `gopls\|r1_history\|references:result->error:0` | 0766542a976b-v08, c78cc37df9be-v05 | yes |  |
| gopls-36824 | r4_edits | `gopls\|r4_edits\|organizeImports:gained` | 7c47ccf34683-v00, 98c2308013f1-v00 | yes |  |
| gopls-38424 | r1_history | `gopls\|r1_history\|codeAction:result->error:0` | 609ebfde9d6e-v00, 8e5e0fab945c-v00, ab450444c7f0-v00 | yes |  |
| gopls-38424 | r1_history | `gopls\|r1_history\|diagnostics:extra:?` | 609ebfde9d6e-v01, 8e5e0fab945c-v01, ab450444c7f0-v01 | yes |  |
| gopls-38732 | r1_history | `gopls\|r1_history\|codeAction:error:0->result` | 7fc6a0126bac-v01 | yes |  |
| gopls-38732 | r1_history | `gopls\|r1_history\|codeAction:key-lost` | 7fc6a0126bac-v00 | yes |  |
| gopls-38732 | r1_history | `gopls\|r1_history\|diagnostics:missing:?` | 7fc6a0126bac-v02 | yes |  |
| gopls-42254 | r3_routes | `gopls\|r3_routes\|definitionConsistency:changed` | e3dfa731ba3e-v00, f87481e998a4-v00 | yes |  |
| gopls-43144 | r5_transforms | `gopls\|r5_transforms\|documentSymbol:changed` | 2fb4af1ae90b-v00, fc1a0e798310-v00 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|definition:result->error:0` | 5030e88eba05-v01, f4be4dc8d3b2-v02 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|diagnostics:extra:UndeclaredName` | 5030e88eba05-v02, f4be4dc8d3b2-v03 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|documentHighlight:lost` | 5030e88eba05-v03, f4be4dc8d3b2-v04 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|documentSymbol:lost` | 5030e88eba05-v04, f4be4dc8d3b2-v05 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|hover:changed` | 5030e88eba05-v07, f4be4dc8d3b2-v08 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|hover:lost` | 5030e88eba05-v06, f4be4dc8d3b2-v07 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|hover:text` | 5030e88eba05-v05, f4be4dc8d3b2-v06 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|references:missing` | 5030e88eba05-v08, f4be4dc8d3b2-v09 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|semanticTokens:changed` | 5030e88eba05-v10, f4be4dc8d3b2-v10 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|semanticTokens:result->error:0` | 5030e88eba05-v11, f4be4dc8d3b2-v11 | yes |  |
| gopls-52500 | r1_history | `gopls\|r1_history\|typeDefinition:result->error:0` | 5030e88eba05-v12, f4be4dc8d3b2-v12 | yes |  |
| gopls-60435 | r3_routes | `gopls\|r3_routes\|highlightVsReferences:extra` | 485265fc03e1-v01, a8920f8f9cc5-v01 | yes |  |
| gopls-62141 | r4_edits | `gopls\|r4_edits\|completionInsert:gained` | 6c815d8e1adf-v00, 916de349b2fa-v00 | yes |  |
| gopls-73269 | r4_edits | `gopls\|r4_edits\|diagnostics:extra:CannotInferTypeArgs` | 864711338949-v00, bcb38ab3674d-v00 | yes |  |
| gopls-73564 | r4_edits | `gopls\|r4_edits\|diagnostics:extra:CannotInferTypeArgs` | 04e89532c673-v00, 6d7fb362be42-v00 | yes |  |
| gopls-73576 | r2_handles | `gopls\|r2_handles\|codeActionResolve:changed` | d43486dbc01e-v00 | yes |  |
| gopls-73576 | r4_edits | `gopls\|r4_edits\|diagnostics:extra:?` | 28d6e512916e-v00, 42d15608cca4-v00 | yes |  |
| gopls-73661 | r4_edits | `gopls\|r4_edits\|diagnostics:extra:IncompatibleAssign` | 588af1f93269-v00, 9d98b7004142-v00 | yes |  |
| gopls-74708 | r4_edits | `gopls\|r4_edits\|diagnostics:extra:?` | 3bb40aadab8b-v00, db1bca460fe2-v00 | yes |  |
| gopls-74709 | r4_edits | `gopls\|r4_edits\|diagnostics:extra:?` | 12bac84dd717-v00, b54edcf2280e-v00 | yes |  |
| jdtls-2111 | r2_handles | `jdtls\|r2_handles\|codeActionResolve:changed` | a10cfe4da316-v01, c88089177073-v00 | yes |  |
| jdtls-3155 | r0_crash | `jdtls\|r0_crash\|references:result->error:timeout` | 89756a56e6b5-v00 | yes |  |
| jdtls-3155 | r1_history | `jdtls\|r1_history\|codeAction:extra` | 2f47e1684987-v01 | no |  |
| jdtls-3155 | r1_history | `jdtls\|r1_history\|diagnostics:extra:268435846,570425394` | 2f47e1684987-v02 | no |  |
| pyright-3482 | r1_history | `pyright\|r1_history\|diagnostics:extra:reportGeneralTypeIssues` | 05500cce2b75-v00 | yes |  |
| pyright-3482 | r1_history | `pyright\|r1_history\|hover:text` | 05500cce2b75-v01 | yes |  |
| pyright-4844 | r1_history | `pyright\|r1_history\|codeAction:key-lost` | 0fbd8b7d204b-v00 | yes |  |
| pyright-4844 | r1_history | `pyright\|r1_history\|diagnostics:extra:reportGeneralTypeIssues` | 28212517fd6f-v00 | yes |  |
| pyright-4844 | r1_history | `pyright\|r1_history\|diagnostics:missing:reportGeneralTypeIssues` | 0fbd8b7d204b-v01 | yes |  |
| pyright-8946 | r1_history | `pyright\|r1_history\|definition:lost` | 5a4f9235d12a-v00 | yes |  |
| pyright-8946 | r1_history | `pyright\|r1_history\|hover:text` | 3e4577624555-v01, 5a4f9235d12a-v01 | yes |  |
| pyright-8946 | r1_history | `pyright\|r1_history\|references:lost` | 5a4f9235d12a-v02 | yes |  |
| pyright-8946 | r1_history | `pyright\|r1_history\|signatureHelp:lost` | 3e4577624555-v02 | yes |  |
| pyright-8946 | r1_history | `pyright\|r1_history\|typeDefinition:changed` | 3e4577624555-v03 | yes |  |
| pyright-8946 | r1_history | `pyright\|r1_history\|typeDefinition:lost` | 5a4f9235d12a-v03 | yes |  |
| pyright-8946 | r1_history | `pyright\|r1_history\|typeDefinition:result->error:-32603` | 3e4577624555-v00, 5a4f9235d12a-v04 | yes |  |
| pyright-9681 | r5_transforms | `pyright\|r5_transforms\|diagnostics:extra:reportAssignmentType` | 85696dfdf55e-v00, b9fcc3392b8b-v00 | yes |  |
| rust-analyzer-10618 | r4_edits | `rust-analyzer\|r4_edits\|diagnostics:changed:E0063,E0451` | 3a3075c699f5-v00, b856e7abd3b7-v00 | yes |  |
| rust-analyzer-14841 | r5_transforms | `rust-analyzer\|r5_transforms\|codeAction:extra` | 3ac665313d9f-v00, a9d7986f7000-v00 | yes |  |
| rust-analyzer-16556 | r4_edits | `rust-analyzer\|r4_edits\|diagnostics:extra:syntax-error` | 1ec49281ceb4-v00, b7712965fb8e-v00 | yes |  |
| rust-analyzer-16858 | r4_edits | `rust-analyzer\|r4_edits\|completionInsert:gained` | 88d8ee5113da-v00, f852a58a3ffb-v00 | yes |  |
| rust-analyzer-17525 | r1_history | `rust-analyzer\|r1_history\|diagnostics:extra:syntax-error` | 07bf3af5c528-v04, e176faaf98b4-v04 | yes |  |
| rust-analyzer-17525 | r1_history | `rust-analyzer\|r1_history\|semanticTokens:changed` | 07bf3af5c528-v08 | yes |  |
| rust-analyzer-17728 | r4_edits | `rust-analyzer\|r4_edits\|diagnostics:changed:E0308,syntax-error` | 17e3a7234738-v01, 8aa4faf773c8-v01 | yes |  |
| rust-analyzer-18130 | r4_edits | `rust-analyzer\|r4_edits\|completionInsert:gained` | 45a020cb3c00-v00, b0c665ceaae4-v00 | yes |  |
| rust-analyzer-18572 | r1_history | `rust-analyzer\|r1_history\|codeAction:lost` | 8cb7dd2b0300-v01 | no |  |
| rust-analyzer-18572 | r1_history | `rust-analyzer\|r1_history\|codeAction:missing` | 8cb7dd2b0300-v00 | no |  |
| rust-analyzer-19694 | r3_routes | `rust-analyzer\|r3_routes\|diagnostics:missing:E0268` | 55d98c0cdc91-v00 | yes |  |
| rust-analyzer-20588 | r1_history | `rust-analyzer\|r1_history\|codeAction:lost` | 507d391b23c9-v01, fe75bbe3678e-v01 | yes |  |
| rust-analyzer-20588 | r1_history | `rust-analyzer\|r1_history\|documentHighlight:lost` | 507d391b23c9-v04, fe75bbe3678e-v04 | yes |  |
| rust-analyzer-20987 | r4_edits | `rust-analyzer\|r4_edits\|completionInsert:gained` | 5b4a8e2d794e-v00, ea64eec81319-v00 | yes |  |
| rust-analyzer-21173 | r0_crash | `rust-analyzer\|r0_crash\|codeAction:result->error:-32603` | a3d629628564-v00, c8e7d09749c2-v00 | yes |  |
| rust-analyzer-21173 | r0_crash | `rust-analyzer\|r0_crash\|diagnostics:result->error:-32603` | a3d629628564-v01, c8e7d09749c2-v01 | yes |  |
| rust-analyzer-21173 | r1_history | `rust-analyzer\|r1_history\|codeAction:error:-32603->result` | 511f3c2a374a-v00 | no |  |
| rust-analyzer-21173 | r1_history | `rust-analyzer\|r1_history\|completion:lost` | 511f3c2a374a-v01 | no |  |
| rust-analyzer-21173 | r3_routes | `rust-analyzer\|r3_routes\|diagnostics:error:-32603->result` | 4cd55b7cf5d1-v00, 6152df9194f1-v01 | yes |  |
| tsserver-32068 | r4_edits | `tsserver\|r4_edits\|formatting:gained` | 471186c183af-v00, acfab65143bf-v00 | yes |  |
| tsserver-37830 | r3_routes | `tsserver\|r3_routes\|definitionConsistency:changed` | 616bf86baa4b-v00, ad60272e1138-v00 | yes |  |
| tsserver-44123 | r4_edits | `tsserver\|r4_edits\|diagnostics:extra:1163` | 48aa946c5f1b-v00, 7cf64845ac61-v00 | yes |  |
| tsserver-46466 | r4_edits | `tsserver\|r4_edits\|diagnostics:changed:1005,1109,1308` | 4f6e0b0496b7-v00, 6fdfb833326c-v00 | yes |  |
| tsserver-51920 | r4_edits | `tsserver\|r4_edits\|diagnostics:changed:2741,8010` | 62e1d3d43776-v00, b8c3c8a3472a-v00 | yes |  |
| tsserver-52274 | r4_edits | `tsserver\|r4_edits\|diagnostics:extra:8024` | 26987aef853f-v00, aa69bf241b19-v00 | yes |  |
| tsserver-59116 | r4_edits | `tsserver\|r4_edits\|diagnostics:extra:2339` | 1cd5799a8e00-v00, d19f3f597197-v00 | yes |  |

## Confirmed signatures per case and oracle (pre / post)

| case | oracle | pre | post | runs pre | runs post | labelled (pre / post, not replayed) |
|---|---|---|---|---|---|---|
| gopls-36824 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-36824 | r1_history | 10 | 4 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-36824 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-36824 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-36824 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-36824 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38424 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38424 | r1_history | 2 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-38424 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38424 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38424 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38424 | r5_transforms | 4 | 4 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38732 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38732 | r1_history | 3 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-38732 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38732 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38732 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-38732 | r5_transforms | 5 | 5 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-41057 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-41057 | r1_history | 2 | 2 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-41057 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-41057 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-41057 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-41057 | r5_transforms | 3 | 3 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-42254 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-42254 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-42254 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-42254 | r3_routes | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-42254 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-42254 | r5_transforms | 6 | 6 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-43144 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-43144 | r1_history | 7 | 7 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-43144 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-43144 | r3_routes | 3 | 3 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-43144 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-43144 | r5_transforms | 3 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46436 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46436 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-46436 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46436 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46436 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46436 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46667 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46667 | r1_history | 18 | 18 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-46667 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46667 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46667 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-46667 | r5_transforms | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-47436 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-47436 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-47436 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-47436 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-47436 | r4_edits | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-47436 | r5_transforms | 5 | 5 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52500 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52500 | r1_history | 13 | 2 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-52500 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52500 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52500 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52500 | r5_transforms | 5 | 5 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52981 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52981 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-52981 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52981 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52981 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-52981 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-54147 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-54147 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-54147 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-54147 | r3_routes | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-54147 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-54147 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-57480 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-57480 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-57480 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-57480 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-57480 | r4_edits | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-57480 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-60435 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r3_routes | 2 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-62141 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-62141 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-62141 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-62141 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-62141 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-62141 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-72753 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-72753 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-72753 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-72753 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-72753 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-72753 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73269 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73269 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-73269 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73269 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73269 | r4_edits | 3 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73269 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73564 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73564 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-73564 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73564 | r3_routes | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73564 | r4_edits | 3 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73564 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73576 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73576 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-73576 | r2_handles | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73576 | r3_routes | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73576 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73576 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73661 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73661 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-73661 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73661 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73661 | r4_edits | 2 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-73661 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74708 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74708 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-74708 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74708 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74708 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74708 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74709 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74709 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-74709 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74709 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74709 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74709 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74938 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74938 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-74938 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74938 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74938 | r4_edits | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-74938 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| jdtls-2111 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| jdtls-2111 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| jdtls-2111 | r2_handles | 2 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| jdtls-2111 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| jdtls-3155 | r0_crash | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| jdtls-3155 | r1_history | 2 | 0 | {'ok': 3, 'timeout': 1} | {'ok': 4} | 0 / 0 |
| jdtls-3155 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| jdtls-3155 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2759 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2759 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-2759 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2759 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2759 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2759 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2983 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2983 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-2983 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2983 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2983 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-2983 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3482 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3482 | r1_history | 2 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-3482 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3482 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3482 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3482 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3504 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3504 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-3504 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3504 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3504 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3504 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3585 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3585 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-3585 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3585 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3585 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-3585 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-4844 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-4844 | r1_history | 3 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-4844 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-4844 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-4844 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-4844 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-6629 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-6629 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-6629 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-6629 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-6629 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-6629 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7466 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7466 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-7466 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7466 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7466 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7466 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7516 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7516 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-7516 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7516 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7516 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-7516 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8133 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8133 | r1_history | 0 | 6 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-8133 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8133 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8133 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8133 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8946 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8946 | r1_history | 7 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-8946 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8946 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8946 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-8946 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-9681 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-9681 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| pyright-9681 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-9681 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-9681 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| pyright-9681 | r5_transforms | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10326 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10326 | r1_history | 0 | 0 | {'ok': 3, 'incomplete': 1} | {'ok': 4} | 0 / 0 |
| rust-analyzer-10326 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10326 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10326 | r4_edits | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10326 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10618 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10618 | r1_history | 0 | 0 | {'incomplete': 1, 'ok': 3} | {'ok': 4} | 0 / 0 |
| rust-analyzer-10618 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10618 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10618 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-10618 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-11897 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-11897 | r1_history | 3 | 3 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-11897 | r2_handles | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-11897 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-11897 | r4_edits | 4 | 4 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-11897 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-14841 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-14841 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-14841 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-14841 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-14841 | r4_edits | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-14841 | r5_transforms | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16556 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16556 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-16556 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16556 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16556 | r4_edits | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16556 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16858 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16858 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-16858 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16858 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16858 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-16858 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17139 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17139 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-17139 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17139 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17139 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17139 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17525 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17525 | r1_history | 12 | 10 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-17525 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17525 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17525 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17525 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17728 | r0_crash | 0 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17728 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-17728 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17728 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17728 | r4_edits | 2 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-17728 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18130 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18130 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-18130 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18130 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18130 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18130 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18144 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18144 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-18144 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18144 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18144 | r4_edits | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18144 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18572 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18572 | r1_history | 2 | 0 | {'ok': 3, 'incomplete': 1} | {'ok': 3, 'incomplete': 1} | 0 / 0 |
| rust-analyzer-18572 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18572 | r3_routes | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18572 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-18572 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19694 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19694 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-19694 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19694 | r3_routes | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19694 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19694 | r5_transforms | 3 | 3 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19758 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19758 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-19758 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19758 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19758 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-19758 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20588 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20588 | r1_history | 7 | 7 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-20588 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20588 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20588 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20588 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20987 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20987 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-20987 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20987 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20987 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20987 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20998 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20998 | r1_history | 1 | 3 | {'ok': 3, 'incomplete': 1} | {'ok': 3, 'incomplete': 1} | 0 / 0 |
| rust-analyzer-20998 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20998 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20998 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-20998 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r0_crash | 2 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r1_history | 2 | 1 | {'ok': 3, 'incomplete': 1} | {'ok': 3, 'incomplete': 1} | 0 / 0 |
| rust-analyzer-21173 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r3_routes | 2 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21204 | r0_crash | 0 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21204 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-21204 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21204 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21204 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21204 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-22281 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-22281 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-22281 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-22281 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-22281 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-22281 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-29908 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-29908 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-29908 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-29908 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-29908 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-29908 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-32068 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-32068 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-32068 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-32068 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-32068 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-32068 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-37830 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-37830 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-37830 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-37830 | r3_routes | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-37830 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-37830 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-41526 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-41526 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-41526 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-41526 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-41526 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-41526 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-43278 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-43278 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-43278 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-43278 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-43278 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-43278 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-44123 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-44123 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-44123 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-44123 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-44123 | r4_edits | 4 | 3 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-44123 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45270 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45270 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-45270 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45270 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45270 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45270 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45533 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45533 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-45533 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45533 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45533 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-45533 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46466 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46466 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-46466 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46466 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46466 | r4_edits | 3 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46466 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46564 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46564 | r1_history | 2 | 2 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-46564 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46564 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46564 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46564 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-48006 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-48006 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-48006 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-48006 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-48006 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-48006 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49001 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49001 | r1_history | 9 | 9 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-49001 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49001 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49001 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49001 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49693 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49693 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-49693 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49693 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49693 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-49693 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50076 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50076 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-50076 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50076 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50076 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50076 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50188 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50188 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-50188 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50188 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50188 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-50188 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51667 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51667 | r1_history | 0 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-51667 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51667 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51667 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51667 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51920 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51920 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-51920 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51920 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51920 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-51920 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52274 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52274 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-52274 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52274 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52274 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52274 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52675 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52675 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-52675 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52675 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52675 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52675 | r5_transforms | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52792 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52792 | r1_history | 7 | 7 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-52792 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52792 | r3_routes | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52792 | r4_edits | 2 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-52792 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-57497 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-57497 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-57497 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-57497 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-57497 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-57497 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-59116 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-59116 | r1_history | 10 | 10 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-59116 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-59116 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-59116 | r4_edits | 1 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-59116 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-60186 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-60186 | r1_history | 7 | 7 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-60186 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-60186 | r3_routes | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-60186 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-60186 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
