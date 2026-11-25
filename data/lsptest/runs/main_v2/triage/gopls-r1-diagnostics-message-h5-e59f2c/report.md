# [gopls v0.23.0] diagnostics rewords ? after file rename round trip

Draft for the author (not filed). Group `gopls-r1-diagnostics-message-h5-e59f2c`, signature `gopls|r1_history|diagnostics:message:?`, case family `H5`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `go-gorm/gorm@b3d3bf219f02` (corpus, commit b3d3bf219f0283f8e2e985bac509cb643170f729), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open migrator/column_type.go (then 200 ms)`
3. textDocument/didOpen: `open tests/hooks_test.go (then 200 ms)`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename clause/joins.go -> clause/joins_rt.go (then 200 ms)`
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename clause/joins_rt.go -> clause/joins.go (then 200 ms)`
6. Timing: send the steps 200 ms apart without waiting, then wait until idle.
7. textDocument/didOpen `clause/joins.go` (the query step opens every target file that is not open), then wait until the server is idle.
8. Query `textDocument/diagnostic` on `tests/hooks_test.go` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package github.com/jinzhu/inflection (imported by gorm.io/gorm/schema); to add: go get gorm.io/gorm/schema@v1.31.0"
 ],
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package github.com/jinzhu/now (imported by gorm.io/gorm/tests); to add: go get -t gorm.io/gorm/tests"
 ],
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package golang.org/x/text/cases (imported by gorm.io/gorm/schema); to add: go get gorm.io/gorm/schema@v1.31.0"
 ],
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package golang.org/x/text/language (imported by gorm.io/gorm/schema); to add: go get gorm.io/gorm/schema@v1.31.0"
 ]
]
```

Actual:

```json
[
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package github.com/jinzhu/inflection (imported by gorm.io/gorm/schema); to add: go get gorm.io/gorm/schema@v1.31.0"
 ],
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package github.com/jinzhu/now (imported by gorm.io/gorm); to add: go get gorm.io/gorm@v1.31.0"
 ],
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package golang.org/x/text/cases (imported by gorm.io/gorm/schema); to add: go get gorm.io/gorm/schema@v1.31.0"
 ],
 [
  10,
  1,
  10,
  15,
  1,
  "",
  "compiler",
  "error while importing gorm.io/gorm: missing go.sum entry for module providing package golang.org/x/text/language (imported by gorm.io/gorm/schema); to add: go get gorm.io/gorm/schema@v1.31.0"
 ]
]
```

Project file `tests/hooks_test.go`:

```
   1 | package tests_test
     ...
   3 | import (
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-diagnostics-message-h5-e59f2c/repro.json
```

## Evidence and reduction

- representative 56aea42fc074-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 4 (13 probes, 104.763 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects go-gorm/gorm@b3d3bf219f02, timings race0, race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#51037](https://github.com/golang/go/issues/51037) x/tools/gopls: Add support for workspace/{Will,Did}{Rename,Delete,Create}Files methods (open, 2022-02-06, 1 comments)
- [golang/go#59550](https://github.com/golang/go/issues/59550) x/tools/gopls: rename applies duplicate edits to a file with aliases (symlinks) (open, 2023-04-11, 0 comments)
- [golang/go#69563](https://github.com/golang/go/issues/69563) x/tools/gopls: Show specific file name when renaming failed. (closed, 2024-09-20, 3 comments)
- [golang/go#45317](https://github.com/golang/go/issues/45317) x/tools/gopls: renaming test file package declaration `package_test `-> `package` falsely claims import cycle (closed, 2021-03-31, 3 comments)
- [golang/go#32562](https://github.com/golang/go/issues/32562) x/tools/cmd/gopls: error when renaming a file (closed, 2019-06-12, 1 comments)
- [golang/go#42154](https://github.com/golang/go/issues/42154) x/tools/gopls: improve diagnostics for empty go files (open, 2020-10-22, 12 comments)
- [golang/go#54987](https://github.com/golang/go/issues/54987) x/tools/gopls: revisit the inconsistent vendoring error diagnostics message (open, 2022-09-09, 0 comments)
- [golang/go#75107](https://github.com/golang/go/issues/75107) x/tools/gopls: umbrella for marker test flakes (open, 2025-08-20, 414 comments)
- queries: `"rename file" in:title repo:golang/go is:issue label:gopls`; `diagnostics message repo:golang/go is:issue label:gopls`; `diagnostics "rename file" repo:golang/go is:issue label:gopls`; `diagnostics stale repo:golang/go is:issue label:gopls`
