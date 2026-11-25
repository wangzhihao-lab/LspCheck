# Version sweep `ts7-groups-on-ts6`

Each triage group's representative replayed on another build of its server; reproduced = every replay reproduced the violation, not-reproduced = every replay settled with agreeing controls and none reproduced.

| from kind | build | reproduced | not-reproduced | flaky | unsettled | error | skipped |
|---|---|---|---|---|---|---|---|
| ts7 | ts6 6.0.3 | 1 | 1 | 0 | 0 | 0 | 0 |

| oracle | reproduced | not-reproduced | flaky | unsettled | error | skipped |
|---|---|---|---|---|---|---|
| r1_history | 1 | 1 | 0 | 0 | 0 | 0 |

| group | from | build | verdict | reproduced | settled | seconds |
|---|---|---|---|---|---|---|
| ts7-r1-references-extra-h6-574e94 | ts7 | ts6 6.0.3 | reproduced | 3/3 | 3/3 | 59.5 |
| ts7-r1-references-missing-h9-2dd24a | ts7 | ts6 6.0.3 | not-reproduced | 0/3 | 3/3 | 112.3 |
