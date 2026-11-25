# Second-rater agreement, main_v2

Generated 2026-11-20T05:42:22 by `scripts/paper/rater2_agreement.py` from `data/lsptest/runs/main_v2/triage/decisions.csv` and `data/lsptest/runs/main_v2/triage/rater2_decisions.csv`.

Groups: 121 in the triage; the author judged 121, the second rater 121; both 121. Missing from the second rater: 0; from the author: 0; unknown groups in the rater-2 file: 0; rater-2 rows without a verdict: 0.

| | n | agreement | kappa | SE | 95% CI (asymptotic) | 95% CI (bootstrap) |
|---|---:|---:|---:|---:|---|---|
| three classes | 121 | 116 (95.9%) | 0.935 | 0.028 | [0.879, 0.991] | [0.873, 0.987] |
| bug or not | 121 | 118 (97.5%) | 0.949 | 0.029 | [0.892, 1.000] | [0.884, 1.000] |
| three classes, unsure as legitimate | 121 | 116 (95.9%) | 0.935 | 0.028 | [0.879, 0.990] | [0.872, 0.987] |
| bug or not, unsure as legitimate | 121 | 120 (99.2%) | 0.983 | 0.017 | [0.950, 1.000] | [0.946, 1.000] |

Confusion matrix, three classes (rows: author, columns: rater 2):

| author \ rater 2 | bug | legitimate | tool-artifact | total |
|---|---:|---:|---:|---:|
| bug | 49 | 0 | 0 | 49 |
| legitimate | 2 | 46 | 2 | 50 |
| tool-artifact | 1 | 0 | 21 | 22 |
| total | 52 | 46 | 23 | 121 |

Confusion matrix, bug or not (rows: author, columns: rater 2):

| author \ rater 2 | bug | not bug | total |
|---|---:|---:|---:|
| bug | 49 | 0 | 49 |
| not bug | 3 | 69 | 72 |
| total | 52 | 69 | 121 |

By relation:

| relation | n | agree | agreement | kappa (3 classes) | kappa (bug or not) |
|---|---:|---:|---:|---:|---:|
| R0 | 1 | 1 | 100.0% | – | – |
| R1 | 37 | 37 | 100.0% | 1.000 | 1.000 |
| R2 | 2 | 2 | 100.0% | – | – |
| R3 | 23 | 21 | 91.3% | 0.701 | 0.701 |
| R4 | 38 | 38 | 100.0% | 1.000 | 1.000 |
| R5 | 10 | 7 | 70.0% | 0.516 | 0.783 |
| R6 | 10 | 10 | 100.0% | – | – |

Rater-2 notes marking the group as unsure: 6 (author agrees on 4). The rows 'unsure as legitimate' recode those groups to legitimate: rater-2 verdicts of the groups the rater's note marks as unsure recoded to legitimate, the default the author's judging page gave for groups that stay unclear.

Method: kappa: Cohen's kappa on the groups both raters judged; ci95_asymptotic: kappa +- 1.96 SE, SE from the large-sample variance of Fleiss, Cohen and Everitt (1969); clipped to [-1, 1]; bootstrap: percentile interval, groups resampled with replacement, 10000 resamples, seed 20261117; resamples with undefined kappa skipped; by_relation: relation from triage.json; kappa is null where it is undefined (one category only).
