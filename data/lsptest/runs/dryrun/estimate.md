# Dry run dryrun: timings per (oracle, server kind)

| oracle | kind | runs | projects | max_cases | mean s per run (run + confirm) | sessions | candidates | replayed | confirmed | labelled (skipped + replayed before labels) | capped | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r0_crash | pyright | 1 | Panniantong/Agent-Reach@a19a171fa980 | 2 | 8.1 (7.7 + 0.0) | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r0_crash | ts6 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 19.1 (18.7 + 0.0) | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r0_crash | ts7 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 18.1 (17.0 + 0.0) | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r0_crash | rust-analyzer | 1 | rust-lang/rustlings@a650509c789d | 2 | 26.2 (25.1 + 0.0) | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r0_crash | gopls | 1 | spf13/cobra@adbc8813901b | 2 | 9.1 (8.9 + 0.0) | 2.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | pyright | 1 | Panniantong/Agent-Reach@a19a171fa980 | 2 | 39.3 (39.0 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | ts6 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 62.4 (61.5 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | ts7 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 63.4 (62.9 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | rust-analyzer | 1 | rust-lang/rustlings@a650509c789d | 2 | 91.6 (90.8 + 0.0) | 3.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r1_history | gopls | 1 | spf13/cobra@adbc8813901b | 2 | 48.3 (47.3 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r2_handles | pyright | 1 | Panniantong/Agent-Reach@a19a171fa980 | 2 | 17.1 (16.5 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r2_handles | ts6 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 37.3 (36.2 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r2_handles | ts7 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 19.1 (18.5 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r2_handles | rust-analyzer | 1 | rust-lang/rustlings@a650509c789d | 2 | 51.4 (50.5 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r2_handles | gopls | 1 | spf13/cobra@adbc8813901b | 2 | 12.1 (11.7 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r3_routes | pyright | 1 | Panniantong/Agent-Reach@a19a171fa980 | 2 | 154.2 (128.8 + 24.6) | 3.0 | 2.0 | 1.0 | 1.0 | 0.0 + 0.0 | 0.0 | ok |
| r3_routes | ts6 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 482.4 (104.7 + 376.9) | 3.0 | 16.0 | 5.0 | 5.0 | 0.0 + 4.0 | 0.0 | ok |
| r3_routes | ts7 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 446.1 (103.1 + 342.5) | 3.0 | 16.0 | 5.0 | 5.0 | 0.0 + 4.0 | 0.0 | ok |
| r3_routes | rust-analyzer | 1 | rust-lang/rustlings@a650509c789d | 2 | 411.9 (189.1 + 221.9) | 3.0 | 6.0 | 2.0 | 2.0 | 0.0 + 1.0 | 0.0 | ok |
| r3_routes | gopls | 1 | spf13/cobra@adbc8813901b | 2 | 107.7 (56.0 + 50.8) | 3.0 | 5.0 | 2.0 | 2.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | pyright | 1 | Panniantong/Agent-Reach@a19a171fa980 | 2 | 9.1 (8.5 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | ts6 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 19.1 (18.2 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | ts7 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 18.1 (16.9 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | rust-analyzer | 1 | rust-lang/rustlings@a650509c789d | 2 | 27.2 (26.1 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r4_edits | gopls | 1 | spf13/cobra@adbc8813901b | 2 | 13.1 (12.0 + 0.0) | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r5_transforms | pyright | 1 | Panniantong/Agent-Reach@a19a171fa980 | 2 | 27.2 (26.4 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r5_transforms | ts6 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 73.5 (73.2 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r5_transforms | ts7 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 62.5 (61.9 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r5_transforms | rust-analyzer | 1 | rust-lang/rustlings@a650509c789d | 2 | 79.6 (78.6 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r5_transforms | gopls | 1 | spf13/cobra@adbc8813901b | 2 | 30.2 (29.1 + 0.0) | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 + 0.0 | 0.0 | ok |
| r6_crossimpl | ts7 | 1 | pmndrs/zustand@b57db4f86ef1 | 2 | 292.1 (46.7 + 244.5) | 4.0 | 22.0 | 2.0 | 2.0 | 0.0 + 0.0 | 0.0 | ok |

# Projection of main_v1: 720 runs

Model: per run, the dry-run means of its (oracle, kind) are used: the oracle run is scaled to the run's max_cases for oracles whose work grows with it (r1, r2, r4, r5: a fixed part of one fresh session, R5 two, a session costing about the dry-run R0 time; the rest linear), and, for the high estimate only, by (s0 + extra) / s0, where s0 is that session cost and extra is how much longer the project's corpus probe took to settle than the dry-run project's. Confirmation is the dry-run confirmation time without the share of replayed signatures that now carry a legitimate-difference label; the low estimate also applies the signature cap as if every signature of an (oracle, kind) queue recurred in all its runs (confirmations in min(N, K) of N runs), the high estimate as if none recurred. Wall time at concurrency c = max(total / c, longest run, run-hours of a kind with a limit L / min(c, L)). Timings come from a shared, loaded machine at the dry run's concurrency; more concurrent runs add contention.

Cost controls: signature cap 3 runs (campaign scope); proxies none.

| server kind | runs | run-hours (low - high) |
|---|---|---|
| pyright | 140 | 4.2 - 5.2 |
| ts6 | 140 | 6.1 - 6.7 |
| ts7 | 160 | 6.1 - 7.6 |
| rust-analyzer | 140 | 9.0 - 28.5 |
| gopls | 140 | 4.3 - 5.2 |

Total 29.7 - 53.3 run-hours; server limits {'rust-analyzer': 2}.
- concurrency 4: about 7.4 - 14.3 h wall time
- concurrency 6: about 5.0 - 14.3 h wall time

Per (oracle, kind), run-hours (low, high): r0_crash pyright (0.02, 0.03), r1_history pyright (2.72, 3.33), r2_handles pyright (0.34, 0.42), r3_routes pyright (0.74, 1.02), r4_edits pyright (0.07, 0.09), r5_transforms pyright (0.27, 0.33), r0_crash ts6 (0.05, 0.05), r1_history ts6 (3.84, 3.97), r2_handles ts6 (0.69, 0.72), r3_routes ts6 (0.65, 1.02), r4_edits ts6 (0.11, 0.11), r5_transforms ts6 (0.81, 0.83), r0_crash ts7 (0.05, 0.05), r1_history ts7 (4.07, 4.08), r2_handles ts7 (0.15, 0.15), r3_routes ts7 (0.63, 0.96), r4_edits ts7 (0.1, 0.1), r5_transforms ts7 (0.66, 0.66), r6_crossimpl ts7 (0.47, 1.62), r0_crash rust-analyzer (0.07, 0.22), r1_history rust-analyzer (5.83, 18.35), r2_handles rust-analyzer (0.99, 3.11), r3_routes rust-analyzer (1.15, 3.93), r4_edits rust-analyzer (0.18, 0.55), r5_transforms rust-analyzer (0.76, 2.37), r0_crash gopls (0.03, 0.03), r1_history gopls (3.34, 3.88), r2_handles gopls (0.15, 0.17), r3_routes gopls (0.36, 0.65), r4_edits gopls (0.16, 0.18), r5_transforms gopls (0.29, 0.34)
