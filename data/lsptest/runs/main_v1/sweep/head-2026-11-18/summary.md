# Release sweep `head-2026-11-18` (releases published up to 2026-11-18)

Cell: reproduced/replays and the frozen sweep's verdict; n/a (Go) = not replayable (the project needs a newer Go than the build runs); unavailable = not installable or not launchable; not run = pending. Rules, release dates and install details: releases.json.

## gopls

Rule: the development head: golang.org/x/tools/gopls at the pseudo-version of @master on 2026-11-18.

- v0.0.0-20261118023053-8967817d2000 (released 2026-11-18; development head; runs go1.27.1)

| cause | group | v0.0.0-20261118023053-8967817d2000 |
|---|---|---|
| C3 | `gopls-r2-codeactionresolve-changed-codeaction-70b3e9` | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-notatype-mutation-m2-477181` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-invalidifaceassign-mutation-m2-416e90` | 0/3 unsettled |
| C5 | `gopls-r4-diagnostics-extra-nonindexableoperand-mutation-m2-ba152b` | 3/3 reproduced |
| C5 | `gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a` | 3/3 reproduced |
| C6 | `gopls-r4-diagnostics-extra-mutation-m2-111975` | 0/3 unsettled |
| C6 | `gopls-r4-syntax-gained-mutation-m2-86fde3` | 0/3 unsettled |
| C7 | `gopls-r4-diagnostics-extra-undeclaredname-wrongar-mutation-m3-946c39` | 0/3 unsettled |
| C9 | `gopls-r1-references-extra-h9-0290a7` | 3/3 reproduced |
