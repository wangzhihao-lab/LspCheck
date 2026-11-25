# LSP bug-fix pilot data collection - summary

Generated 2026-09-21 06:11 UTC by `scripts/lsp_pilot/run_pilot.py`. Runtime: 0.3s. GraphQL points used (observed): 0; requests sent: 0; last remaining/limit: None/None; rate-limit sleeps: 0; backoff retries: 0.

Column definitions: for standalone repos, 'total issues'/'closed issues' are repo-wide (no label filter). For the two monorepo targets (golang/go, llvm/llvm-project) they are scoped by the identifying label itself (gopls / clangd), since there is no dedicated sub-repo to count against - so 'closed issues' and 'closed bug-labeled' are expected to be equal for those two rows.

## Funnel table

| Target | Repo | Label filter (AND) | Total issues | Closed issues | Closed bug-labeled | Fixed bug candidates |
|---|---|---|---:|---:|---:|---:|
| rust-analyzer | rust-lang/rust-analyzer | `C-bug` | 9,792 | 8,092 | 2,670 | 1,278 |
| pyright | microsoft/pyright | `bug` | 7,580 | 7,308 | 3,977 | 51 |
| golang-go-gopls | golang/go | `gopls` | 3,963 | 3,496 | 3,496 | 1,345 |
| llvm-project-clangd | llvm/llvm-project | `clangd` | 450 | 274 | 274 | 72 |
| microsoft-typescript | microsoft/TypeScript | `Bug AND (Domain: Error Messages OR Domain: Formatter OR Domain: JSDoc OR Domain: LS: Auto-import OR Domain: LS: Completion Lists OR Domain: LS: Inlay Hints OR Domain: LS: Organize Imports OR Domain: LS: Quick Fixes OR Domain: LS: Refactorings OR Domain: LS: Signature Help OR Domain: LS: Symbol Navigation OR Domain: LS: TSServer)` | 43,528 | 38,666 | 1,594 | 901 |
| eclipse-jdtls | eclipse-jdtls/eclipse.jdt.ls | `bug` | 1,641 | 1,239 | 336 | 253 |

**Total fixed-bug candidates across required targets (1-6): 3,900**
**Grand total including additional targets: 6,435**

## Yearly distribution of fixed bug candidates (by closedAt)

| Target | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | other |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rust-analyzer | 0 | 0 | 47 | 217 | 224 | 303 | 253 | 234 | 0 |
| pyright | 0 | 0 | 5 | 1 | 7 | 2 | 3 | 33 | 0 |
| golang-go-gopls | 161 | 285 | 119 | 118 | 181 | 203 | 165 | 113 | 0 |
| llvm-project-clangd | 0 | 0 | 0 | 10 | 12 | 10 | 12 | 28 | 0 |
| microsoft-typescript | 61 | 139 | 117 | 102 | 97 | 31 | 6 | 3 | 345 |
| eclipse-jdtls | 37 | 13 | 19 | 24 | 24 | 12 | 9 | 13 | 102 |
| clangd-clangd-repo | 7 | 19 | 8 | 11 | 6 | 6 | 3 | 6 | 0 |
| pyright-addressed-in-next-version | 150 | 283 | 382 | 403 | 577 | 509 | 158 | 7 | 0 |

## Label names actually used

- **rust-analyzer** (`rust-lang/rust-analyzer`): requested `['C-bug']` -> used `['C-bug']` [OK]
- **pyright** (`microsoft/pyright`): requested `['bug']` -> used `['bug']` [OK]
- **golang-go-gopls** (`golang/go`): requested `['gopls']` -> used `['gopls']` [OK]
- **llvm-project-clangd** (`llvm/llvm-project`): requested `['clangd']` -> used `['clangd']` [OK]
- **microsoft-typescript** (`microsoft/TypeScript`): requested `['Bug']` -> used `['Bug']` [OK]
- **eclipse-jdtls** (`eclipse-jdtls/eclipse.jdt.ls`): requested `['bug']` -> used `['bug']` [OK]
- **pyright-addressed-in-next-version** (`microsoft/pyright`): requested `['bug', 'addressed in next version']` -> used `['bug', 'addressed in next version']` [OK]
- **lualls-lua-language-server** (`LuaLS/lua-language-server`): requested `['bug']` -> used `['bug']` [OK]
- **omnisharp-roslyn** (`OmniSharp/omnisharp-roslyn`): requested `['bug']` -> used `['bug']` [OK]
- **dart-lang-sdk** (`dart-lang/sdk`): requested `['area-analyzer', 'type-bug']` -> used `None` [DIFFERS (see anomalies)]

## Additional targets (coordinator addition, 2026-09-20)

Reported separately from the required-targets total above (different repos / different evidence criteria - see detail sections below).

| Target | Repo | Label filter (AND) | Total issues | Closed issues | Closed bug-labeled | Fixed bug candidates |
|---|---|---|---:|---:|---:|---:|
| clangd-clangd-repo | clangd/clangd | `bug` | 2,207 | 1,353 | 126 | 66 |
| pyright-addressed-in-next-version | microsoft/pyright | `bug AND addressed in next version (label evidence, not link evidence)` | 7,580 | 7,308 | 2,469 | 2,469 |

**Additional-targets subtotal: 2,535**

## microsoft/TypeScript domain-label detail

All `Domain: *` labels on the repo with their closed-issue counts (65 total, sorted descending):

| Domain label | Closed issues |
|---|---:|
| `Domain: lib.d.ts` | 828 |
| `Domain: LS: Completion Lists` | 396 |
| `Domain: API` | 371 |
| `Domain: LS: Refactorings` | 338 |
| `Domain: Error Messages` | 283 |
| `Domain: JSDoc` | 283 |
| `Domain: LS: Quick Fixes` | 271 |
| `Domain: Formatter` | 197 |
| `Domain: Declaration Emit` | 175 |
| `Domain: API: Transforms` | 160 |
| `Domain: JavaScript` | 156 |
| `Domain: LS: TSServer` | 125 |
| `Domain: JSX/TSX` | 122 |
| `Domain: Performance` | 114 |
| `Domain: LS: Symbol Navigation` | 106 |
| `Domain: LS: Quick Info` | 98 |
| `Domain: LS: Auto-import` | 97 |
| `Domain: check: Control Flow` | 48 |
| `Domain: check: Type Inference` | 48 |
| `Domain: JS Emit` | 41 |
| `Domain: Conditional Types` | 39 |
| `Domain: ES Modules` | 38 |
| `Domain: LS: Organize Imports` | 37 |
| `Domain: Literal Types` | 36 |
| `Domain: Decorators` | 35 |
| `Domain: LS: Type Display` | 34 |
| `Domain: Comment Emit` | 32 |
| `Domain: LS: Signature Help` | 32 |
| `Domain: Mapped Types` | 29 |
| `Domain: LS: Outlining` | 27 |
| `Domain: LS: Inlay Hints` | 24 |
| `Domain: check: Contextual Types` | 20 |
| `Domain: Parser` | 18 |
| `Domain: Related Error Spans` | 17 |
| `Domain: Crashes` | 16 |
| `Domain: tsc: --incremental` | 15 |
| `Domain: tsc -b` | 13 |
| `Domain: This-Typing` | 12 |
| `Domain: flag: isolatedDeclarations` | 12 |
| `Domain: Indexed Access Types` | 11 |
| `Domain: check: Type Circularity` | 10 |
| `Domain: API: ts.transpileDeclaration` | 9 |
| `Domain: Node ESM` | 9 |
| `Domain: Something Else` | 9 |
| `Domain: check: Big Unions` | 8 |
| `Domain: classes` | 8 |
| `Domain: Binder` | 7 |
| `Domain: check: Error Instability` | 7 |
| `Domain: enum` | 7 |
| `Domain: Intersection` | 6 |
| `Domain: Module Resolution` | 6 |
| `Domain: check: Excess Property Checking` | 6 |
| `Domain: LS: Smart Indentation` | 5 |
| `Domain: tslib and Helper Functions` | 5 |
| `Domain: check: Variance Relationships` | 4 |
| `Domain: LS: Smart-Select` | 3 |
| `Domain: LS: Suggestion Diagnostics` | 2 |
| `Domain: flag: exactOptionalPropertyTypes` | 2 |
| `Domain: Editor/VS Code Extension` | 1 |
| `Domain: Index Types` | 1 |
| `Domain: Module specifier synthesis` | 1 |
| `Domain: Source Maps` | 1 |
| `Domain: Content Mappers` | 0 |
| `Domain: flag: noUncheckedIndexedAccess` | 0 |
| `Domain: node` | 0 |

**Anomaly**: only 2 of the task spec's 13 example domain labels exist verbatim: `Domain: TSServer` (missing), `Domain: Completion Lists` (missing), `Domain: Quick Fixes` (missing), `Domain: Refactorings` (missing), `Domain: Rename` (missing), `Domain: Signature Help` (missing), `Domain: Go to Definition` (missing), `Domain: Find All References` (missing), `Domain: Formatter`, `Domain: Error Messages`, `Domain: Symbol Navigation` (missing), `Domain: Code Actions` (missing), `Domain: Organize Imports` (missing)

Per coordinator direction (2026-09-20), the language-service subset is instead every `Domain:` label whose name mentions any of: `TSServer`, `Completion`, `Quick Fix`, `Refactor`, `Rename`, `Signature`, `Definition`, `References`, `Formatter`, `Error Messages`, `Symbol`, `Code Action`, `Organize Imports`, `Navigation`, `Hover`, `JSDoc`, `Import`, `Inlay` (case-insensitive substring match).

Matched 12 domain label(s):

| Domain label | Closed `Bug` AND domain issues |
|---|---:|
| `Domain: Error Messages` | 172 |
| `Domain: Formatter` | 171 |
| `Domain: JSDoc` | 225 |
| `Domain: LS: Auto-import` | 69 |
| `Domain: LS: Completion Lists` | 304 |
| `Domain: LS: Inlay Hints` | 18 |
| `Domain: LS: Organize Imports` | 26 |
| `Domain: LS: Quick Fixes` | 205 |
| `Domain: LS: Refactorings` | 277 |
| `Domain: LS: Signature Help` | 22 |
| `Domain: LS: Symbol Navigation` | 87 |
| `Domain: LS: TSServer` | 77 |

Union of Bug AND matched domains, deduped by issue number: **1,594 closed issues**, of which **901 are fixed-bug candidates**.

## golang/go gopls detail

- closed `gopls` AND `BugReport`: 178
- closed `gopls` AND `NeedsFix`: 151
- closed `gopls` AND `FixPending`: 24

Proxy signal comparison over all closed `gopls`-labeled issues (population 3,496), since gopls fixes land as Gerrit CLs mirrored to golang/tools and often never produce a merged PR inside golang/go itself:
- has a ClosedEvent closer commit: 1,343
- has a go.dev/cl or golang.org/cl link in the last 3 comments: 1,679
- has both: 1,263

## clangd/clangd (separate repo) detail

Label filter used: `bug`. llvm/llvm-project's `label:clangd` row above is kept unchanged - this is an additional, separate source, since clangd/clangd is clangd's primary issue tracker.

Proxy signal comparison over all closed issues in this set (population 126), since clangd fixes land in llvm/llvm-project (cross-repo):
- has a ClosedEvent closer commit: 52
- has a github.com/llvm/llvm-project/commit or /pull link in the last 3 comments: 24
- has both: 2

## pyright detail

- closed issues labeled "addressed in next version": 3,365 (count only; see the dedicated row/section below for the full bug AND addressed-in-next-version breakdown)

## pyright "addressed in next version" detail

This row's evidence is the label combination `bug` AND `addressed in next version`, not a linked PR/commit - the pyright maintainer often closes a fixed bug by comment instead of a GitHub-linked PR, which is why the primary pyright row's fixed-bug-candidate rate is so low (51/3977 = 1.3%).

- closed issues with both labels: 2,469
- of which also have a ClosedEvent closer commit: 0 (0.0%)

## Optional targets (tier 7, counts only)

| Target | Repo | Label filter | Total issues | Closed issues | Closed bug-labeled |
|---|---|---|---:|---:|---:|
| lualls-lua-language-server | LuaLS/lua-language-server | `bug` | 2,421 | 1,729 | 523 |
| omnisharp-roslyn | OmniSharp/omnisharp-roslyn | `bug` | 1,232 | 843 | 67 |
| dart-lang-sdk | dart-lang/sdk | - | SKIPPED: required label(s) ('area-analyzer', 'type-bug') not found on dart-lang/sdk; skipping this target | | |

## Anomalies

**llvm-project-clangd**:
- 46 closed bug-labeled issue(s) carry a 'duplicate'-like label

**microsoft-typescript**:
- 1 closed bug-labeled issue(s) closed by an apparent bot account
- 7 closed bug-labeled issue(s) carry a 'duplicate'-like label
- 345 fixed-bug candidate(s) closed outside the 2019-2026 window

**eclipse-jdtls**:
- 1 closed bug-labeled issue(s) carry a 'duplicate'-like label
- 102 fixed-bug candidate(s) closed outside the 2019-2026 window

**pyright-addressed-in-next-version**:
- bot-closed detection not computed for this row (reuses pyright's row-schema data, which doesn't carry ClosedEvent actor login)

**dart-lang-sdk**:
- ERROR: required label(s) ('area-analyzer', 'type-bug') not found on dart-lang/sdk; skipping this target
- label 'area-analyzer' does not exist on this repo (checked case-insensitively too)

