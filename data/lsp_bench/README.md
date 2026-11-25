# LSP historical-bug benchmark (kickoff v3, C3)

One directory per bug under `cases/<server>-<number>/`: `case.json` (metadata, provenance of every
project file, the hand-written reproduction as `model.Op` JSON and one probe) and `project/`. A case
counts as **reproduced** only when its probe reports the bug in 3/3 fresh runs on the pinned pre-fix
build and in 0/3 on the post-fix build (`scripts/lsptest/bench/run_repro.py`). Results:
`repro_results.jsonl` (append-only, one line per case run, tied to the case revision by `case_sha`)
and `repro_results.md` (generated). Build installs: `builds.json`.

```
python3 scripts/lsptest/bench/sources.py gopls 60435            # issue + comments -> temp/lsp_bench/issues/
python3 scripts/lsptest/bench/case_format.py                     # validate every case (provenance, ops, probe)
python3 scripts/lsptest/bench/install_builds.py --all            # pre/post builds of every case, one at a time
python3 scripts/lsptest/bench/run_repro.py --smoke <case dir>    # harness check on both builds, no verdict
python3 scripts/lsptest/bench/run_repro.py --all                 # 3 + 3 fresh runs per case, results files
python3 -m unittest discover -s scripts/lsptest/tests
```

Probe types (`bench/probes.py`, `bench/probes_derived.py`): `differs_from_fresh` (R1: answers after
the ops vs a fresh session on the final content, with a fresh control that must agree),
`error_response`, `edit_breaks_syntax` and `edit_leaves_diagnostic` (R4: the server's own code action
or completion edit, parse errors from `oracles/syntax.py`, new errors from a fresh session on the
edited content), `diagnostic_present` / `diagnostic_absent`, `two_routes_differ` (R3: equal, subset,
highlights within references) and `transform_differs` (R5: inserted lines, LF to CRLF). Historical
builds: pyright from npm; TypeScript as kind `tsserver`, version `<ts>+tsls<wrapper>` (npm
`typescript` plus the typescript-language-server release that was current at the post-fix build,
started with the pinned `tsserver.js`, reported version checked on every session); rust-analyzer
weekly release assets; gopls built and run with an era Go installed through golang.org/dl under
`temp/lsp_servers/go-sdks/` (`toolchain.json` next to the binary; `scripts/lsp_repro/servers_bench.py`).

## Pilot, 2026-09-23

| case | class / subtype | probe | pre -> post build | attempts | verdict | effort min |
|---|---|---|---|---|---|---:|
| gopls-60435 | R3 highlight-refs | two_routes_differ (highlights within references) | v0.12.0 -> v0.12.1 (go1.20.4) | 1 | reproduced | 12 |
| pyright-2983 | R1 query-order | differs_from_fresh, race timing | 1.1.232 -> 1.1.233 | 1 | reproduced | 7 |
| tsserver-52792 | R1 open-close | error_response (completion) | 5.0.4 -> 5.1.3, wrapper 3.3.2 | 1 | reproduced | 12 |
| tsserver-46466 | R4 quickfix | edit_breaks_syntax (add async) | 4.4.4 -> 4.5.2, wrapper 0.7.1 | 1 | reproduced | 6 |
| rust-analyzer-21173 | R1 edit-undo (as screened) | error_response (textDocument/diagnostic) | 2025-12-08 -> 2025-12-15 | 2 | reproduced on attempt 2 | 18 |

Each case was run twice with the final case content (the first run, then one consolidated
`run_repro.py --all`): pre-fix present 6/6, post-fix present 0/6 for every case. Effort = reading the
issue and the fix, writing the case, harness smoke, the 3 + 3 runs and checking the evidence; the
one-off infrastructure is not included. Runner wall time per case: 0.3 min (gopls, one session per
run) to 1.8-4.5 min (rust-analyzer, depending on the load of the shared machine); the three-session
R1 attempt on rust-analyzer took 5 min.

Not reproduced or not obtainable:
- **tsserver #49964** (requested; replaced by #46466, same subtype). No stable pre-fix build has the
  bug: the add-extends-constraint code fix was introduced during 4.8 development
  (`fixAddMissingConstraint.ts` is absent at v4.7.4 and present at v4.8.2), so the candidate's pre
  build 4.7.4 does not offer the fix at all; only the nightlies 4.8.0-dev.20220722 -> ...23 bracket it.
  In addition the bug needs the combined fix ("Add `extends` constraint to all type parameters"),
  which typescript-language-server does not expose as a code action in the releases checked (0.7.1,
  1.1.2, 2.0.0, 2.3.0, 3.3.2, 4.3.3: only single fixes plus source.fixAll for three fixed error
  kinds); per-fix "fix all" actions appear in the 6.0.0 wrapper. The sibling #49965 (same fix PR)
  has the same missing-pre-build problem.
- **rust-analyzer #21173, attempt 1** (R1 edit-undo as screened: insert and delete a space, compare
  textDocument/diagnostic with a fresh session): not reproduced, because the case session, the fresh
  session and the control all answered `-32603 request handler panicked: cannot find !BoundConst ...`
  on 2025-12-08. In a headless client the first diagnostics request of a fresh session already
  panics; the reporter's editor presumably asked before the crate had loaded, so the report reads as
  edit-dependent. Attempt 2 used the issue's literal symptom (error response to the diagnostics
  request after an edit) and reproduced 3/3 vs 0/3. The case is an error-response bug on a valid
  program: the R1 oracle cannot see it, a crash-or-error criterion can.
- tsserver #52792: the candidate's fix commit (#53472) only adds tests; its text says the crash was
  fixed by #53001 (1da6d87a05, 2023-03-01). `git tag --contains` puts that in 5.1-beta / 5.1.3 and in
  no 5.0.x, so the 5.0.4 -> 5.1.3 window stands (recorded in the case).

## What reproduces headlessly

- Deterministic relations reproduce on the first attempt with the issue's own code: route
  relations (gopls highlight vs references), code-action output checked by a parser, a request that
  fails outright after the issue's steps (tsserver completion `Debug Failure`).
- Query-order bugs (pyright) need the race timing the issue describes (a request right after the
  edit, before the server re-analyses); a settle marker after the open keeps the rest deterministic.
- Screened R1 "after an edit" reports can turn out history-independent (rust-analyzer #21173); run
  the R1 formulation first and record it, then the literal symptom.
- The earlier state-bug spike (`data/lsp_repro/results.md`) reproduced 3 of 11 hand-picked state bugs;
  its failures were fixtures a client cannot set up over the protocol, a race that a client waiting
  for every reply cannot express, symptoms internal to the server (a logged exception, a retained
  AST) and editor-specific triggers. The screening grades such reports B or C.

Pre-flight checks worth automating before a case is written (each would have saved time here):
1. The feature exists in the pre-fix build (a code fix or analyzer introduced in the same cycle has
   no released buggy build; tsserver: GitHub contents API at the pre tag).
2. The fix PR text names the real fix ("fixed by #N") and the release window is recomputed from it.
3. The LSP route exists in the contemporary wrapper (tsserver combined fixes, organize-imports modes).
4. The era toolchain runs on this machine (go1.20.4 does; older Go releases are untested on macOS 27),
   and an old gopls built with the local Go still loads the project with that Go (smoke first).

## Batch plan to 40-60 reproduced cases on 4 servers

Pool (candidates.jsonl): 287 grade A/B keeps with both builds obtainable and a released buggy build
(gopls 111, rust-analyzer 99, tsserver 59, pyright 18); 167 of them grade A (gopls 56,
rust-analyzer 69, tsserver 37, pyright 5).

| batch | server | candidates to attempt | subtypes first | builds | target reproduced |
|---|---|---:|---|---|---:|
| 1 | tsserver | 20 | R4 quickfix / completion (single fixes), R1 open-close | npm pairs; wrappers 0.3.8-4.3.4 (smoke 0.3.x/0.4.0 first, 14 candidates need them) | 12 |
| 2 | gopls | 22 | R4 modernizer / quickfix (v0.18-v0.21, local Go), R3, then R1 edit-undo / open-close | 25 of 111 build only with an era Go (golang.org/dl) | 14 |
| 3 | rust-analyzer | 22 | R4 quickfix / completion (parser probe), R3 def-consistency, R5 comment / blank lines | release assets 2021-2026 | 14 |
| 4 | pyright | 18 (all A/B) | R1 query-order (race timing), edit-undo, R5 crlf / file-edge | npm | 8 |
| total | | about 80 | | | about 48 |

Assumptions: grade A candidates with a deterministic subtype reproduce at about 60-80% (pilot: 4 of
the 5 requested candidates reproduced, one only on its second attempt; the fifth had no stable
pre-fix build and its substitute reproduced), grade B and race subtypes at about 30%. At the observed 6-18 min per case (median 12), 80 attempts cost about 16 hours of case
writing plus about 3 hours of sequential machine time; the per-case review by the owner
(case.json, provenance, evidence line) at about 5 min per case stays within the 8-10 hours of
kickoff section 5. Order within a batch: the pre-flight checks above, then grade A before B, then by
the candidate rank; stop a server's batch once it reaches its target and move the remaining effort
to the server furthest from its target. Every attempt, including the non-reproduced ones and their
reasons, stays in `repro_results.jsonl` and in the case's `attempts` list.

## Construction status (2026-09-23, final for v1)

- 92 cases attempted, 80 reproduced (pre-fix 3/3 present, post-fix 0/3): gopls 23, rust-analyzer 20, tsserver 23, pyright 12, JDT LS 2; 6 of the 80 establish the ground truth with the specification probe `edit_text_differs` (reported separately).
- Not reproduced 8 and invalid 4, each with its reason in repro_results.md. tsserver-40257 and tsserver-41194 stay invalid: both attempts had specification errors that never exercised the bug; the two-attempt rule is kept rather than allowing a third attempt.
- Side effect outside the repository: jdtls-3155 (the issue's Maven project) downloaded artifacts into ~/.m2/repository (8 MB).
