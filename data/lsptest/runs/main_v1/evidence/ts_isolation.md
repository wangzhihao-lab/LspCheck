# C1/C2 component isolation (version sweep, 3 replays per group)

| cause | group | ts6 campaign (6.0.3+tsls6.0.0) | a: 6.0.3+tsls6.0.1 | b: 5.9.3+tsls6.0.0 | c: 6.0.3+tsls5.0.0 | ctl: 6.0.3+tsls6.0.0 | older-2025: 5.9.3+tsls5.0.0 |
|---|---|---|---|---|---|---|---|
| C1 | `ts6-r1-codeaction-key-lost-h5-4f92e2` | reproduced (3/3, triage) | reproduced (3/3) | flaky (2/3) | flaky (2/3) | reproduced (3/3) | reproduced (3/3) |
| C1 | `ts6-r1-completion-lost-h5-fa501c` | reproduced (3/3, triage) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) |
| C1 | `ts6-r1-definition-lost-h5-61a0fd` | reproduced (3/3, triage) | reproduced (3/3) | flaky (1/3) | flaky (2/3) | not-reproduced (0/3) | flaky (2/3) |
| C1 | `ts6-r1-definition-lost-h9-898f29` | reproduced (3/3, triage) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) |
| C1 | `ts6-r1-diagnostics-extra-2305-2339-7006-h5-d5a250` | reproduced (3/3, triage) | not-reproduced (0/3) | flaky (2/3) | reproduced (3/3) | reproduced (3/3) | flaky (2/3) |
| C1 | `ts6-r1-documenthighlight-lost-h5-9b4675` | reproduced (3/3, triage) | flaky (2/3) | reproduced (3/3) | reproduced (3/3) | flaky (2/3) | flaky (2/3) |
| C1 | `ts6-r1-references-lost-h5-d24ca6` | reproduced (3/3, triage) | reproduced (3/3) | flaky (1/3) | flaky (2/3) | flaky (2/3) | reproduced (3/3) |
| C1 | `ts6-r1-references-missing-h5-cc8950` | reproduced (3/3, triage) | flaky (1/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) |
| C1 | `ts6-r1-semantictokens-changed-h5-591c42` | reproduced (3/3, triage) | reproduced (3/3) | reproduced (3/3) | flaky (2/3) | flaky (2/3) | reproduced (3/3) |
| C1 | `ts6-r1-semantictokens-missing-h9-d686b3` | reproduced (3/3, triage) | reproduced (3/3) | flaky (2/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) |
| C1 | `ts6-r1-signaturehelp-changed-h5-db5a5e` | reproduced (3/3, triage) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | flaky (2/3) | reproduced (3/3) |
| C1 | `ts6-r1-signaturehelp-lost-h9-7bd793` | reproduced (3/3, triage) | flaky (1/3) | reproduced (3/3) | flaky (2/3) | flaky (2/3) | flaky (2/3) |
| C1 | `ts6-r1-typedefinition-lost-h5-712a35` | reproduced (3/3, triage) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) |
| C2 | `ts6-r1-diagnostics-extra-2304-h7-8ca52f` | reproduced (3/3, triage) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) | reproduced (3/3) |

Per build (C1 groups; C2 group):

- a 6.0.3+tsls6.0.1 (newer wrapper, same TypeScript; installed typescript 6.0.3, wrapper 6.0.1) C1: flaky 3, not-reproduced 1, reproduced 9
- a 6.0.3+tsls6.0.1 (newer wrapper, same TypeScript; installed typescript 6.0.3, wrapper 6.0.1) C2: reproduced 1
- b 5.9.3+tsls6.0.0 (older TypeScript, same wrapper; installed typescript 5.9.3, wrapper 6.0.0) C1: flaky 5, reproduced 8
- b 5.9.3+tsls6.0.0 (older TypeScript, same wrapper; installed typescript 5.9.3, wrapper 6.0.0) C2: reproduced 1
- c 6.0.3+tsls5.0.0 (older wrapper, same TypeScript; installed typescript 6.0.3, wrapper 5.0.0) C1: flaky 5, reproduced 8
- c 6.0.3+tsls5.0.0 (older wrapper, same TypeScript; installed typescript 6.0.3, wrapper 5.0.0) C2: reproduced 1
- ctl 6.0.3+tsls6.0.0 (campaign components, sweep launch kind (control); installed typescript 6.0.3, wrapper 6.0.0) C1: flaky 5, not-reproduced 1, reproduced 7
- ctl 6.0.3+tsls6.0.0 (campaign components, sweep launch kind (control); installed typescript 6.0.3, wrapper 6.0.0) C2: reproduced 1
- ref 5.9.3+tsls5.0.0 (both older; installed typescript 5.9.3, wrapper 5.0.0) C1: flaky 4, reproduced 9
- ref 5.9.3+tsls5.0.0 (both older; installed typescript 5.9.3, wrapper 5.0.0) C2: reproduced 1
