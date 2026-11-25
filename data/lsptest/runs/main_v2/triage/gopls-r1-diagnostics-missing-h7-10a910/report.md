# [gopls v0.23.0] diagnostics misses ? after interleaving of h1-h6, h8, h9

Draft for the author (not filed). Group `gopls-r1-diagnostics-missing-h7-10a910`, signature `gopls|r1_history|diagnostics:missing:?`, case family `H7`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `go-gorm/gorm@b3d3bf219f02` (corpus, commit b3d3bf219f0283f8e2e985bac509cb643170f729), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open schema/relationship.go`
3. textDocument/didOpen: `open tests/joins_test.go`
4. textDocument/didOpen: `open utils/tests/dummy_dialecter.go`
5. textDocument/didClose: `close schema/relationship.go`
6. textDocument/didOpen: `open schema/relationship.go`
7. textDocument/didChange: `change utils/tests/dummy_dialecter.go (2, 5)-(2, 5) "t ("`
8. Timing: wait until the server is idle after every step.
9. Query `textDocument/diagnostic` on `tests/joins_test.go` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  8,
  1,
  8,
  37,
  1,
  "BrokenImport",
  "compiler",
  "could not import github.com/stretchr/testify/assert (no required module provides package \"github.com/stretchr/testify/assert\")"
 ],
 [
  9,
  1,
  9,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package github.com/jinzhu/now (imported by gorm.io/gorm/tests); to add: go get -t gorm.io/gorm/tests"
 ]
]
```

Actual:

```json
[
 [
  8,
  1,
  8,
  37,
  1,
  "BrokenImport",
  "compiler",
  "could not import github.com/stretchr/testify/assert (no required module provides package \"github.com/stretchr/testify/assert\")"
 ]
]
```

Project file `tests/joins_test.go`:

```
   1 | package tests_test
     ...
   3 | import (
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-diagnostics-missing-h7-10a910/repro.json
```

## Evidence and reduction

- representative 43cf47dfbeec-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 15 -> 6 (10 probes, 254.905 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects go-gorm/gorm@b3d3bf219f02, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#81812](https://github.com/golang/go/issues/81812) x/tools/gopls: codeAction/resolve after a document change computes the edit at the old position (open, 2026-09-28, 4 comments)
- [golang/go#70604](https://github.com/golang/go/issues/70604) x/tools/gopls: marker test should ensure type checked file remain type checked after code edits (closed, 2024-11-27, 1 comments)
- [golang/go#59587](https://github.com/golang/go/issues/59587) x/tools/gopls: diagnostics only clear after diagnosticsDelay for edited files (closed, 2023-04-12, 1 comments)
- [golang/go#51325](https://github.com/golang/go/issues/51325) x/tools/gopls: push diagnostics after `go mod edit -go=1.18` (closed, 2022-02-22, 1 comments)
- [golang/go#33989](https://github.com/golang/go/issues/33989) x/tools/gopls: Context cancelled errors after some editing (closed, 2019-08-30, 4 comments)
- [golang/go#57856](https://github.com/golang/go/issues/57856) x/tools/gopls: `infertypeargs` diagnostic is missing `code`/`codeDescription` fields (open, 2023-01-17, 0 comments)
- [golang/go#50320](https://github.com/golang/go/issues/50320) x/tools/gopls: consider merging "missing go.sum entries" errors with the same root cause (open, 2021-12-22, 1 comments)
- [golang/go#50764](https://github.com/golang/go/issues/50764) x/tools/gopls: provide a way to suppress analysis diagnostics for certain files (open, 2022-01-23, 57 comments)
- queries: `"after edit" in:title repo:golang/go is:issue label:gopls`; `diagnostics missing repo:golang/go is:issue label:gopls`; `diagnostics "after edit" repo:golang/go is:issue label:gopls`; `diagnostics stale repo:golang/go is:issue label:gopls`

## Server log excerpt (last confirming replay)

```
[gopls-v0.23.0-tr10a910-replay-baseline-20261118-234942-c76c6f] window/logMessage type 1: 2026/11/18 23:49:48 imports fixes: allImportsFixes: temp/lsptest_runs/gopls-v0.23.0-tr10a910-replay-baseline-20261118-234942-c76c6f/ws/utils/tests/dummy_dialecter.go:3:11: missi
[gopls-v0.23.0-tr10a910-replay-control-20261118-234942-5ca441] window/logMessage type 1: 2026/11/18 23:49:48 imports fixes: allImportsFixes: temp/lsptest_runs/gopls-v0.23.0-tr10a910-replay-control-20261118-234942-5ca441/ws/utils/tests/dummy_dialecter.go:3:11: missing
[gopls-v0.23.0-tr10a910-replay-history-20261118-234948-c7aa39] window/logMessage type 1: 2026/11/18 23:50:11 imports fixes: allImportsFixes: temp/lsptest_runs/gopls-v0.23.0-tr10a910-replay-history-20261118-234948-c7aa39/ws/utils/tests/dummy_dialecter.go:3:11: missing
```
