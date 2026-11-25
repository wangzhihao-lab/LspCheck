# Dry run bench_v1-dryrun: timings per (oracle, server kind)

| oracle | kind | runs | projects | max_cases | mean s per run (run + confirm) | sessions | candidates | replayed | confirmed | labelled (skipped + replayed before labels) | capped | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r0_crash | gopls | 4 | gopls-60435 | 12 | 4.2 (3.5 + 0.0) | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r0_crash | rust-analyzer | 4 | rust-analyzer-21173 | 12 | 135.8 (34.0 + 101.2) | 2.0 | 10.5 | 1.0 | 1.0 | 0.0 + 0.0 | 0.0 | ok |
| r0_crash | tsserver | 4 | tsserver-46466 | 12 | 3.8 (3.5 + 0.0) | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | gopls | 8 | gopls-60435 | 12 | 1361.8 (1075.3 + 285.8) | 17.0 | 0.5 | 0.2 | 0.2 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | rust-analyzer | 8 | rust-analyzer-21173 | 12 | 461.9 (461.3 + 0.0) | 5.5 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | tsserver | 8 | tsserver-46466 | 12 | 112.1 (111.7 + 0.0) | 14.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r2_handles | gopls | 4 | gopls-60435 | 12 | 3.5 (3.0 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r2_handles | rust-analyzer | 4 | rust-analyzer-21173 | 12 | 70.5 (43.7 + 26.0) | 1.0 | 0.5 | 0.5 | 0.5 | 0.0 + 0.0 | 0.0 | ok |
| r3_routes | gopls | 4 | gopls-60435 | 12 | 36.5 (9.2 + 26.9) | 3.0 | 2.5 | 1.5 | 1.5 | 0.0 + 0.0 | 0.0 | ok |
| r3_routes | rust-analyzer | 4 | rust-analyzer-21173 | 12 | 135.0 (67.6 + 66.7) | 3.0 | 1.0 | 1.0 | 1.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | gopls | 4 | gopls-60435 | 12 | 24.9 (24.4 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | rust-analyzer | 4 | rust-analyzer-21173 | 12 | 29.2 (28.6 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | tsserver | 4 | tsserver-46466 | 12 | 156.2 (56.5 + 99.0) | 3.5 | 2.5 | 2.5 | 2.5 | 0.0 + 0.0 | 0.0 | ok |
| r5_transforms | gopls | 4 | gopls-60435 | 6 | 27.2 (26.6 + 0.0) | 8.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r5_transforms | rust-analyzer | 4 | rust-analyzer-21173 | 6 | 184.9 (184.2 + 0.0) | 8.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |

# Projection of bench_v1: 1236 runs

Model: per run, the dry-run means of its (oracle, kind) are used: the oracle run is scaled to the run's max_cases for oracles whose work grows with it (r1, r2, r4, r5: a fixed part of one fresh session, R5 two, a session costing about the dry-run R0 time; the rest linear), and, for the high estimate only, by (s0 + extra) / s0, where s0 is that session cost and extra is how much longer the project's corpus probe took to settle than the dry-run project's. Confirmation is the dry-run confirmation time without the share of replayed signatures that now carry a legitimate-difference label; the low estimate also applies the signature cap as if every signature of an (oracle, kind) queue recurred in all its runs (confirmations in min(N, K) of N runs), the high estimate as if none recurred. Wall time at concurrency c = max(total / c, longest run, run-hours of a kind with a limit L / min(c, L)). Timings come from a shared, loaded machine at the dry run's concurrency; more concurrent runs add contention.

Cost controls: signature cap 3 runs (build scope); proxies {'pyright': 'gopls'}.

| server kind | runs | run-hours (low - high) |
|---|---|---|
| gopls | 616 | 65.4 - 68.9 |
| pyright | 28 | 3.0 - 3.1 |
| rust-analyzer | 560 | 32.9 - 32.9 |
| tsserver | 32 | 0.9 - 0.9 |

Total 102.1 - 105.8 run-hours; server limits {'rust-analyzer': 2}.
- concurrency 4: about 25.5 - 26.4 h wall time

Per (oracle, kind), run-hours (low, high): r0_crash gopls (0.1, 0.1), r1_history gopls (63.09, 66.58), r2_handles gopls (0.09, 0.09), r3_routes gopls (0.89, 0.89), r4_edits gopls (0.61, 0.61), r5_transforms gopls (0.66, 0.66), r0_crash pyright (0.0, 0.0), r1_history pyright (2.87, 3.03), r2_handles pyright (0.0, 0.0), r3_routes pyright (0.04, 0.04), r4_edits pyright (0.03, 0.03), r5_transforms pyright (0.03, 0.03), r0_crash rust-analyzer (3.02, 3.02), r1_history rust-analyzer (20.53, 20.53), r2_handles rust-analyzer (1.57, 1.57), r3_routes rust-analyzer (3.0, 3.0), r4_edits rust-analyzer (0.65, 0.65), r5_transforms rust-analyzer (4.11, 4.11), r0_crash tsserver (0.01, 0.01), r1_history tsserver (0.5, 0.5), r4_edits tsserver (0.35, 0.35)
