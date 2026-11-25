# Second-rater agreement, main_v1

Generated 2026-11-18T04:58:56 by `scripts/paper/rater2_agreement.py` from `data/lsptest/runs/main_v1/triage/decisions.csv` and `data/lsptest/runs/main_v1/triage/rater2_decisions.csv`.

Groups: 106 in the triage; the author judged 106, the second rater 106; both 106. Missing from the second rater: 0; from the author: 0; unknown groups in the rater-2 file: 0; rater-2 rows without a verdict: 0.

| | n | agreement | kappa | SE | 95% CI (asymptotic) | 95% CI (bootstrap) |
|---|---:|---:|---:|---:|---|---|
| three classes | 106 | 83 (78.3%) | 0.663 | 0.061 | [0.544, 0.782] | [0.539, 0.779] |
| bug or not | 106 | 89 (84.0%) | 0.632 | 0.080 | [0.476, 0.788] | [0.467, 0.778] |
| three classes, unsure as legitimate | 106 | 81 (76.4%) | 0.627 | 0.064 | [0.501, 0.752] | [0.497, 0.749] |
| bug or not, unsure as legitimate | 106 | 90 (84.9%) | 0.643 | 0.081 | [0.485, 0.801] | [0.477, 0.793] |

Confusion matrix, three classes (rows: author, columns: rater 2):

| author \ rater 2 | bug | legitimate | tool-artifact | total |
|---|---:|---:|---:|---:|
| bug | 25 | 0 | 4 | 29 |
| legitimate | 9 | 41 | 4 | 54 |
| tool-artifact | 4 | 2 | 17 | 23 |
| total | 38 | 43 | 25 | 106 |

Confusion matrix, bug or not (rows: author, columns: rater 2):

| author \ rater 2 | bug | not bug | total |
|---|---:|---:|---:|
| bug | 25 | 4 | 29 |
| not bug | 13 | 64 | 77 |
| total | 38 | 68 | 106 |

By relation:

| relation | n | agree | agreement | kappa (3 classes) | kappa (bug or not) |
|---|---:|---:|---:|---:|---:|
| R0 | 2 | 0 | 0.0% | 0.000 | 0.000 |
| R1 | 29 | 26 | 89.7% | 0.801 | 0.930 |
| R2 | 2 | 2 | 100.0% | – | – |
| R3 | 24 | 18 | 75.0% | 0.308 | 0.308 |
| R4 | 27 | 21 | 77.8% | 0.526 | 0.471 |
| R5 | 9 | 5 | 55.6% | 0.250 | – |
| R6 | 13 | 11 | 84.6% | 0.000 | 0.000 |

Exception class (descriptive): 49 of 58 groups both raters judged legitimate (or both tool-artifact) and both gave a class agree (84.5%).

Rater-2 notes marking the group as unsure: 5 (author agrees on 3). The rows 'unsure as legitimate' recode those groups to legitimate: rater-2 verdicts of the groups the rater's note marks as unsure recoded to legitimate, the default the author's judging page gave for groups that stay unclear.

Method: kappa: Cohen's kappa on the groups both raters judged; ci95_asymptotic: kappa +- 1.96 SE, SE from the large-sample variance of Fleiss, Cohen and Everitt (1969); clipped to [-1, 1]; bootstrap: percentile interval, groups resampled with replacement, 10000 resamples, seed 20261117; resamples with undefined kappa skipped; by_relation: relation from triage.json; kappa is null where it is undefined (one category only).
