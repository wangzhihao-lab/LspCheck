# Detection of reproduced historical bugs: campaign bench_v1-dryrun

A case is detected when an oracle confirms (3/3) a signature on the pre-fix build that it does not confirm on the post-fix build. `author_match` is for the author: does the signature show the case's reported bug?

- cases with a generic ground-truth probe: 3 (3 with every run finished), detected 3; by oracle {'r0_crash': 1, 'r3_routes': 2, 'r4_edits': 1}
- cases whose ground truth used the specification probe edit_text_differs (reported separately): 0 (0 finished), detected 0; by oracle -

## Cases (generic ground-truth probes)

| case | kind | class / subtype | ground-truth probe | builds | detected | oracles with pre-only signatures | runs finished |
|---|---|---|---|---|---|---|---|
| gopls-60435 | gopls | R3 / highlight-refs | two_routes_differ | v0.12.0 -> v0.12.1 | yes | r3_routes | yes |
| rust-analyzer-21173 | rust-analyzer | R1 / edit-undo | error_response | 2025-12-08 -> 2025-12-15 | yes | r0_crash, r3_routes | yes |
| tsserver-46466 | tsserver | R4 / quickfix | edit_breaks_syntax | 4.4.4+tsls0.7.1 -> 4.5.2+tsls0.7.1 | yes | r4_edits | yes |

## Cases whose ground truth used edit_text_differs

| case | kind | class / subtype | ground-truth probe | builds | detected | oracles with pre-only signatures | runs finished |
|---|---|---|---|---|---|---|---|

## Pre-only signatures

| case | oracle | signature | pre-fix violations | runs finished | author_match |
|---|---|---|---|---|---|
| gopls-60435 | r3_routes | `gopls\|r3_routes\|highlightVsReferences:extra` | 485265fc03e1-v01, a8920f8f9cc5-v01 | yes |  |
| rust-analyzer-21173 | r0_crash | `rust-analyzer\|r0_crash\|codeAction:result->error:-32603` | a3d629628564-v00, c8e7d09749c2-v00 | yes |  |
| rust-analyzer-21173 | r0_crash | `rust-analyzer\|r0_crash\|diagnostics:result->error:-32603` | a3d629628564-v01, c8e7d09749c2-v01 | yes |  |
| rust-analyzer-21173 | r3_routes | `rust-analyzer\|r3_routes\|diagnostics:error:-32603->result` | 4cd55b7cf5d1-v00, 6152df9194f1-v01 | yes |  |
| tsserver-46466 | r4_edits | `tsserver\|r4_edits\|diagnostics:changed:1005,1109,1308` | 4f6e0b0496b7-v00, 6fdfb833326c-v00 | yes |  |

## Confirmed signatures per case and oracle (pre / post)

| case | oracle | pre | post | runs pre | runs post | labelled (pre / post, not replayed) |
|---|---|---|---|---|---|---|
| gopls-60435 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r1_history | 1 | 1 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| gopls-60435 | r2_handles | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r3_routes | 2 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| gopls-60435 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r0_crash | 2 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| rust-analyzer-21173 | r2_handles | 1 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r3_routes | 2 | 1 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r4_edits | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| rust-analyzer-21173 | r5_transforms | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46466 | r0_crash | 0 | 0 | {'ok': 2} | {'ok': 2} | 0 / 0 |
| tsserver-46466 | r1_history | 0 | 0 | {'ok': 4} | {'ok': 4} | 0 / 0 |
| tsserver-46466 | r4_edits | 3 | 2 | {'ok': 2} | {'ok': 2} | 0 / 0 |
