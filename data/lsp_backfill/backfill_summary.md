# LSP Bug Fix-Evidence Backfill Summary

Generated 2026-09-21 11:35 UTC by `scripts/lsp_backfill/run_all.py`. Method: git history grep (no GitHub API, no tokens read or printed).

## Method notes (facts about how this was produced)

- Clones: `git clone --filter=blob:none --bare <url> temp/clones/<repo>.git`. Blobs are fetched
  lazily on demand only for the specific commits that are later diffed for stats.
- Every git invocation (`log`, `show --numstat`) runs via Python `subprocess` inside the scripts in
  `scripts/lsp_backfill/`, never as literal `git ...` text passed to a shell command. This session's
  interactive shell used for this project has an active `rtk` hook that transparently rewrites recognized
  commands (`git log` -> `rtk git log`, a lossy "one-line commit history"; `git show` -> `rtk git show`,
  a "compact show"; also `head`/`cat`/`wc`) before they run, which would have silently corrupted the
  exact hashes/dates/full commit text this pipeline depends on. `git clone` and any `python3 ...`
  invocation are not recognized by that hook and pass through unmodified, which is what this pipeline
  relies on for correctness.
- Issue-number matching uses a non-digit lookbehind/lookahead around `#N` (`(?<!\d)#(\d+)(?!\d)`) so
  `#1234` never matches inside `#12345`.
- pyright: single-repo `#N` convention. gopls: golang/tools commits reference golang/go issues
  cross-repo; three patterns are tried in priority order -- `golang/go#N`, then `go#N` (excluding the
  `go#N` inside an already-matched `golang/go#N`), then bare `#N` restricted to commit messages that
  also contain "gopls" (case-insensitive) to hold down false positives from golang/tools' own,
  unrelated PR/CL numbers.
- Per-commit stats come from `git show --format= --numstat --no-renames`, the machine-readable
  equivalent of `--stat`, chosen because the human-readable graph format can truncate long pathnames
  (which would corrupt `touches_tests`). Renames are disabled so every touched path is a plain
  add/delete pair rather than an ambiguous `{old => new}` token. `touches_tests` is true if any
  changed path contains "test" (case-insensitive). Merge commits are not given special-case
  handling: plain `git show --numstat` on a merge already defaults to a diff against its first
  parent only (verified empirically against git 2.50.1, equivalent to `--first-parent -m`), so the
  stat is well-defined and non-empty; such commits are flagged `is_merge` for transparency.
- Issue-level `files_changed` / `insertions` / `deletions` / `touches_tests` report the **first
  (earliest-dated) fix commit only**; `fix_commits` in the JSONL carries the full per-commit
  breakdown for every matched commit if a different aggregation is needed downstream. Ties on an
  identical committer-date second (rare) are broken by commit hash for determinism, not by any
  semantic ordering.
- `fix_latency_days` = first_fix_date (commit committer date) minus the issue's `createdAt`.

## 1. Clone report

| Repo | URL | Already existed | Elapsed (s) | Size (MB) |
|---|---|---|---|---|
| microsoft/pyright | https://github.com/microsoft/pyright.git | True | 0.0 | 27.6 |
| golang/tools (issues tracked in golang/go) | https://github.com/golang/tools.git | True | 0.0 | 37.6 |

Full commit history: pyright 8,867 commits, golang/tools 11,427 commits. numstat fetch failures: pyright 0, gopls 0.

## 2. Coverage: issues with 0 / 1 / 2+ fix commits

### pyright (addressed-in-next-version) (2469 issues)

| Fix commits found | Issues (%) |
|---|---|
| 0 fix commits | 1557 (63.1%) |
| 1 fix commit | 851 (34.5%) |
| 2+ fix commits | 61 (2.5%) |

### gopls (1345 issues)

| Fix commits found | Issues (%) |
|---|---|
| 0 fix commits | 19 (1.4%) |
| 1 fix commit | 993 (73.8%) |
| 2+ fix commits | 333 (24.8%) |

## 3. Validation: pyright 51 linked-issue recall

- total linked issues: 51 (this file uses label filter `bug` only; 17 of the 51 also carry `addressed in next version` and hence also appear in the 2,469-issue set below -- validation below re-runs the grep method directly against all 51 via the shared commit index, independent of that overlap)
- **found_any** (grep found >=1 commit referencing the issue number): 17/51 = 33.3%
- of those, 3 issues carry a ground-truth `closer_commit.oid` and 2 of the grep hits match that hash exactly
- 48 issues carry a merged closing PR number; 15 of the grep hits contain that PR number in the matched commit's subject/body (squash-merge commits typically carry both the PR number in the subject and the original "Fixes #N" in the body)
- **recovered_strict** (found_any AND corroborated by hash or PR number, or no ground truth to cross-check): 17/51 = 33.3%
- missed issue numbers (no commit found at all): [11751, 11743, 11729, 11728, 11712, 11633, 11529, 11518, 11511, 11505, 11470, 11451, 11438, 11253, 11220, 11039, 10845, 10603, 10350, 10198, 9610, 9289, 6465, 6314, 6146, 5943, 5415, 5243, 3962, 2711, 2562, 2545, 1976, 1815]

## 4. gopls consistency check (closer_commit vs. grep)

- issues with a ground-truth `closer_commit`: 1343
- grep found the exact same commit hash: 1317 (98.1%)
- inconsistent (closer_commit present but not in grep hits): 26
- issues lacking `closer_commit` entirely: 2
- of those, grep found a fix commit anyway: 2

**gopls match-pattern usage** (a commit can match more than one pattern):

| pattern | matches |
|---|---|
| golang/go#N | 1986 |
| bare#N+gopls | 6 |

## 5. files_changed distribution

### pyright

| files_changed bucket | issues |
|---|---|
| 0 | 0 |
| 1 | 180 |
| 2-3 | 468 |
| 4-10 | 234 |
| 11+ | 30 |

### gopls

| files_changed bucket | issues |
|---|---|
| 0 | 0 |
| 1 | 318 |
| 2-3 | 493 |
| 4-10 | 403 |
| 11+ | 112 |

## 6. touches_tests

### pyright

| touches_tests | issues (of those with >=1 fix commit) |
|---|---|
| true | 673 |
| false | 239 |

### gopls

| touches_tests | issues (of those with >=1 fix commit) |
|---|---|
| true | 923 |
| false | 403 |

## 7. fix_latency_days quantiles

| repo | count | min | p25 | median | p75 | max | mean |
|---|---|---|---|---|---|---|---|
| pyright | 912 | 0.001 | 0.115 | 0.445 | 3.047 | 600.7 | 7.933 |
| gopls | 1326 | 0.012 | 1.457 | 7.702 | 42.413 | 2142.869 | 66.421 |

## 8. 20 most-referenced commits (bulk-fix / release-note candidates to exclude later)

### pyright

| commit | date | n_issues_referenced | subject |
|---|---|---|---|
| 2f66d52f48 | 2025-01-21 | 12 | Merge branch 'main' into tensorShapes7 |
| a775c56ebb | 2025-08-31 | 10 | Merge branch 'main' into issue-10625 |
| 55f1f5f6a8 | 2024-07-18 | 4 | Added the distinction between "external" versus "internal" type variable scopes. |
| 6950622347 | 2024-04-26 | 4 | Issue7779 (#7781) |
| 23b4668508 | 2024-10-07 | 3 | Backed out recent performance optimization that resulted in a regression for pro |
| 96d0145763 | 2024-04-25 | 3 | Changed `TypeIs` to use the same logic as `isinstance` type narrowing logic for  |
| d97565a193 | 2025-08-30 | 2 | Revert "Added support for tracking multiple constraint sets when performing prot |
| 8fe87a951a | 2024-12-07 | 2 | Fixed bug that leads to a hang when returning a tuple from a lambda argument exp |
| d0bc751a24 | 2024-11-05 | 2 | Removed recent check for illegal identifiers used in `alias` for `dataclass_tran |
| 2e5a2a2db4 | 2024-10-21 | 2 | Issue 9280 (#9284) |
| 6d66b90553 | 2024-09-23 | 2 | Fixed a bug that can result in a false positive error when a function signature  |
| f3ed4990d3 | 2024-09-16 | 2 | Fixed bug that results in incorrect type narrowing when `TypeIs` intersects `typ |
| 171f05214d | 2024-09-13 | 2 | Fixed recent regression that results in incorrect type narrowing for `isinstance |
| 8faec96982 | 2024-09-08 | 2 | Fixed a bug that leads to incorrect type narrowing with `isinstance` or `TypeIs` |
| b9d25687f4 | 2024-07-21 | 2 | Fixed issues with the `reportInconsistentConstructor`. It produced false negativ |
| 1d9b8b5ece | 2024-07-17 | 2 | Fixed a bug that results in a false positive error when using bidirectional type |
| c9543bc987 | 2024-07-30 | 2 | Further simplification of the logic involved in type var solving. (#8600) |
| 8f8f5b163d | 2024-06-27 | 2 | Fixed recent regression that results in false positive when a inner function wit |
| 6913347aa8 | 2024-07-30 | 2 | Fixed bug that results in false positive error under certain circumstances when  |
| 400bb92da0 | 2024-04-23 | 2 | Redesigned the handling of PEP 695-style type parameter scoping to better match  |

### gopls

| commit | date | n_issues_referenced | subject |
|---|---|---|---|
| beed481fb5 | 2024-09-12 | 3 | gopls/internal/settings: use CodeActionKind hierarchy |
| 060c748a28 | 2024-01-22 | 3 | gopls: consolidate analyzers, eliminating "convenience" analyzers |
| b389785156 | 2023-07-26 | 3 | gopls: fix tests that depend on log sequencing |
| bddb3720ba | 2022-09-28 | 3 | gopls: deprecate three experimental features |
| 4874f863e6 | 2019-06-27 | 3 | internal/jsonrpc2: change the concurrency strategy |
| 50c1ed9ff4 | 2026-06-05 | 2 | gopls/internal/filecache: add GetOrFatal and ErrNoCache |
| 6c613c8456 | 2025-12-18 | 2 | gopls/internal/cache/parsego: construct File.Cursor lazily |
| db38d36303 | 2025-09-15 | 2 | gopls/internal/golang/completion: don't offer internal std packages |
| cb39a5f00b | 2025-06-04 | 2 | gopls/internal/golang: Format generated files |
| 33d59880f3 | 2025-06-04 | 2 | gopls/internal/server: Organize Imports of generated files |
| d9bacab54d | 2025-06-04 | 2 | gopls/internal/server: improve "editing generated file" warning |
| 3b3100c2e7 | 2025-06-30 | 2 | gopls/internal/golang: recover failed inlineAllCalls |
| 4e672d580b | 2025-06-02 | 2 | gopls/internal/protocol: PublishDiagnosticsParams.version omitempty |
| bcaee63084 | 2025-06-02 | 2 | gopls/internal/protocol: make some optional integer fields indirect |
| edff653582 | 2025-04-09 | 2 | gopls/internal/server: TypeHierarchy support |
| 8d38122b0b | 2025-03-04 | 2 | gopls/internal/cache: reproduce and fix crash on if cond overflow |
| f11abcb12b | 2025-04-23 | 2 | internal/analysisinternal: permit Fix.End slightly beyond EOF |
| 4d65dec0c3 | 2026-09-04 | 2 | gopls/internal/cache: tolerate missing nodes in reachability analysis |
| e26dff9fb9 | 2024-11-11 | 2 | gopls/internal/golang: semtok: use type information consistently |
| c45778760f | 2024-10-22 | 2 | gopls/internal/cache: avoid reporting bugs when go/packages has errors |

## 9. Random examples for eyeballing (10 per repo)

### pyright

| issue | url | commit | subject |
|---|---|---|---|
| #6634 | https://github.com/microsoft/pyright/issues/6634 | 935e21cfc6 | Fixed regression that resulted in a false negative for the `reportUnknownMemberType` check |
| #9784 | https://github.com/microsoft/pyright/issues/9784 | 4fa8d71523 | Fixed regression that resulted in a false positive error when evaluating a call expression |
| #10773 | https://github.com/microsoft/pyright/issues/10773 | 30068aaa52 | Fixed a bug that results in false positive errors when using `object` methods (like `__eq_ |
| #6094 | https://github.com/microsoft/pyright/issues/6094 | f2b2294f61 | Added support for @deprecated when applied to property accessors and descriptor methods. T |
| #8649 | https://github.com/microsoft/pyright/issues/8649 | 4adf903331 | Fixed bug that caused first argument of `cast` method on `memoryview` object to be treated |
| #8866 | https://github.com/microsoft/pyright/issues/8866 | ed761d9298 | Fixed bug that results in incorrect type narrowing for the `in` (containment) operator whe |
| #9040 | https://github.com/microsoft/pyright/issues/9040 | e0d33e4808 | Fixed bug that results in false positive error when using a `Final` variable in a protocol |
| #9574 | https://github.com/microsoft/pyright/issues/9574 | 8a44e4c914 | Fixed bug that results in spurious type evaluation error when an operator overload method  |
| #6116 | https://github.com/microsoft/pyright/issues/6116 | 41aca983a9 | Fixed crash that occurs when encountering a malformed system version check of the form `sy |
| #9841 | https://github.com/microsoft/pyright/issues/9841 | fe79092b72 | Fixed bug that results in incorrect inferred type for an instance or class variable assign |

### gopls

| issue | url | commit | subject |
|---|---|---|---|
| #31341 | https://github.com/golang/go/issues/31341 | f939817187 | internal/lsp: add an additional check to ToUTF16Column |
| #71405 | https://github.com/golang/go/issues/71405 | 058d583f49 | gopls/internal/golang: don't apply edits in codeAction/resolve |
| #78270 | https://github.com/golang/go/issues/78270 | 1cc5cddeb9 | go/analysis/passes/modernize: fix panic in atomictypes |
| #59318 | https://github.com/golang/go/issues/59318 | 04059e179a | gopls/internal/lsp/cache: record unloadable files if loading completes |
| #61344 | https://github.com/golang/go/issues/61344 | dbfa51380a | gopls/internal/lsp: don't awaitLoaded inside resolveImportGraph |
| #63755 | https://github.com/golang/go/issues/63755 | 080c202046 | gopls/internal/lsp: fix code action panic on params of external funcs |
| #69624 | https://github.com/golang/go/issues/69624 | 53f41002c0 | gopls/doc: document Rename feature |
| #71888 | https://github.com/golang/go/issues/71888 | 66eb306a36 | Revert "internal/settings: drop "annotations" setting" |
| #36751 | https://github.com/golang/go/issues/36751 | d33eef8e68 | gopls/doc: document updating to an unstable version |
| #73269 | https://github.com/golang/go/issues/73269 | a99a1c3c83 | gopls/internal/analysis/modernize: prevent conversion of variadic functions to slices.Cont |

## 10. Idempotence check (rerun once to confirm)

| check | value |
|---|---|
| pyright clone already_existed (run 2) | True |
| gopls clone already_existed (run 2) | True |
| pyright commit log cached (run 2) | True |
| gopls commit log cached (run 2) | True |
| pyright output byte-identical run1 vs run2 | True |
| gopls output byte-identical run1 vs run2 | True |
| run 1 wall time (s) | 1863.4 |
| run 2 wall time (s) | 0.5 |

## 11. Output files

- `data/lsp_backfill/pyright_fix_evidence.jsonl` (2469 records)
- `data/lsp_backfill/gopls_fix_evidence.jsonl` (1345 records)
- pyright runtime: 0.1s; gopls runtime: 0.4s

