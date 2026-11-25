# Second-rater agreement on the benchmark signatures, bench_v1

Generated 2026-11-19T03:45:41 by `scripts/paper/detection_agreement.py` from `data/lsptest/runs/bench_v1/detection_author.csv` and `data/lsptest/runs/bench_v1/detection_rater2.csv`.

Signatures: 77 pre-only signatures; the author judged 77, the second rater 77; both 77. Missing from the second rater: 0; from the author: 0; unknown rows: rater 2 0, author 0.

| | n | agreement | kappa | SE | 95% CI (asymptotic) | 95% CI (bootstrap) |
|---|---:|---:|---:|---:|---|---|
| three classes | 77 | 70 (90.9%) | 0.790 | 0.072 | [0.649, 0.931] | [0.635, 0.919] |
| detected or not | 77 | 70 (90.9%) | 0.776 | 0.079 | [0.623, 0.930] | [0.607, 0.915] |
| case detected or not | 39 | 37 (94.9%) | 0.827 | 0.118 | [0.596, 1.000] | [0.538, 1.000] |
| three classes, unsure as no | 77 | 68 (88.3%) | 0.729 | 0.079 | [0.575, 0.883] | [0.567, 0.875] |
| detected or not, unsure as no | 77 | 69 (89.6%) | 0.749 | 0.081 | [0.589, 0.908] | [0.578, 0.897] |
| case detected or not, unsure as no | 39 | 37 (94.9%) | 0.827 | 0.118 | [0.596, 1.000] | [0.538, 1.000] |
| three classes, without practice cases | 62 | 56 (90.3%) | 0.755 | 0.090 | [0.578, 0.932] | [0.552, 0.917] |
| detected or not, without practice cases | 62 | 56 (90.3%) | 0.739 | 0.098 | [0.548, 0.931] | [0.518, 0.912] |
| case detected or not, without practice cases | 36 | 34 (94.4%) | 0.824 | 0.119 | [0.590, 1.000] | [0.534, 1.000] |

Without practice cases: the manual's practice examples cover 3 cases on this page (gopls-36824, pyright-8946, pyright-9681), 15 signatures left out.

Confusion matrix, three classes (rows: author, columns: rater 2):

| author \ rater 2 | yes | partial | no | total |
|---|---:|---:|---:|---:|
| yes | 52 | 7 | 0 | 59 |
| partial | 0 | 1 | 0 | 1 |
| no | 0 | 0 | 17 | 17 |
| total | 52 | 8 | 17 | 77 |

Confusion matrix, detected or not (rows: author, columns: rater 2):

| author \ rater 2 | detected | not detected | total |
|---|---:|---:|---:|
| detected | 52 | 7 | 59 |
| not detected | 0 | 18 | 18 |
| total | 52 | 25 | 77 |

Cases: 39, judged in full by both 39; detected by the author 33, by the second rater 31; differ on 2: `gopls-60435` (detected / not detected), `jdtls-2111` (detected / not detected).

By relation:

| relation | n | agree | agreement | kappa (3 classes) | kappa (detected) |
|---|---:|---:|---:|---:|---:|
| R0 | 3 | 3 | 100.0% | 1.000 | 1.000 |
| R1 | 44 | 39 | 88.6% | 0.771 | 0.754 |
| R2 | 2 | 1 | 50.0% | 0.333 | 0.000 |
| R3 | 5 | 4 | 80.0% | 0.583 | 0.545 |
| R4 | 20 | 20 | 100.0% | – | – |
| R5 | 3 | 3 | 100.0% | 1.000 | 1.000 |

By server:

| server | n | agree | agreement | kappa (3 classes) | kappa (detected) |
|---|---:|---:|---:|---:|---:|
| gopls | 34 | 32 | 94.1% | 0.855 | 0.850 |
| jdtls | 4 | 2 | 50.0% | 0.333 | 0.200 |
| pyright | 13 | 11 | 84.6% | 0.000 | 0.000 |
| rust-analyzer | 19 | 18 | 94.7% | 0.907 | 0.895 |
| tsserver | 7 | 7 | 100.0% | – | – |

Rater-2 notes marking the signature as unsure: 4 (author agrees on 2). The rows 'unsure as no': rater-2 verdicts of the signatures the rater's note marks as unsure recoded to no: an unsure signature does not count as a detection.

Signatures judged differently:

| case | signature | author | rater 2 | rater-2 note |
|---|---|---|---|---|
| gopls-38732 | `gopls|r1_history|codeAction:key-lost` | yes | partial | key-lost 只是因为 foo.go 的那条诊断不见了（见第 72 条），间接表现。 |
| gopls-60435 | `gopls|r3_routes|highlightVsReferences:extra` | yes | partial | 方向相反：从 http 的使用处高亮，选中了 httptest 的导入路径；很可能是同一个按包名子串匹配的缺陷，但不是 issue 报的那个方向。 |
| jdtls-2111 | `jdtls|r2_handles|codeActionResolve:changed` | yes | partial | 不确定：过期的 Generate Getter and Setter 句柄在编辑后解析出缩进不同的编辑；与 issue 同属编辑后代码操作状态陈旧，但表现不是 issue 说的选项缺失或无效。 |
| jdtls-3155 | `jdtls|r1_history|codeAction:extra` | yes | partial | 多出的 Remove unused import 只是因为陈旧的导入错误还在（见第 64 条），间接表现。 |
| pyright-4844 | `pyright|r1_history|codeAction:key-lost` | yes | partial | codeAction 的 key-lost 只是因为第一个 f(0) 的误报在操作后消失（见第 36 条），间接表现。 |
| pyright-8946 | `pyright|r1_history|typeDefinition:result->error:-32603` | yes | partial | 导入的模块名改成 datetime_x 再改回后，对模块名做 typeDefinition 返回内部错误；触发条件同类（编辑改变导入），但表现是内部错误而不是类型无法识别。 |
| rust-analyzer-21173 | `rust-analyzer|r1_history|codeAction:error:-32603->result` | yes | partial | 不确定：新会话一侧的 codeAction -32603 应是同一个 panic，但这条报的是“操作后不再报错”的历史差异，只间接表现。 |

Method: kappa: Cohen's kappa on the signatures both raters judged; detected_or_not: yes against partial and no; ci95_asymptotic: kappa +- 1.96 SE, SE from the large-sample variance of Fleiss, Cohen and Everitt (1969); clipped to [-1, 1]; bootstrap: percentile interval, signatures resampled with replacement, 10000 resamples, seed 20261118; resamples with undefined kappa skipped; cases: a case counts as detected by a rater when at least one of its signatures is judged yes; only cases whose signatures both judged in full; by_relation: kappa is null where it is undefined (one category only).
