# [gopls v0.23.0] references adds entries after file rename round trip

Draft for the author (not filed). Group `gopls-r1-references-extra-h5-e2e003`, signature `gopls|r1_history|references:extra`, case family `H5`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `go-gorm/gorm@b3d3bf219f02` (corpus, commit b3d3bf219f0283f8e2e985bac509cb643170f729), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open tests/non_std_test.go`
3. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename chainable_api.go -> chainable_api_rt.go`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename chainable_api_rt.go -> chainable_api.go`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `chainable_api.go`, `tests/count_test.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/references` on `tests/count_test.go` line 59, column 8 (LSP position {line: 58, character: 7}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/fuzz.go",
  398,
  5,
  398,
  11
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1353,
  17,
  1353,
  23
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1616,
  7,
  1616,
  13
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1758,
  4,
  1758,
  10
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1762,
  4,
  1762,
  10
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1864,
  4,
  1864,
  10
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  2061,
  8,
  2061,
  14
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  2075,
  5,
  2075,
  11
 ],
 [
  "tests/association_generics_test.go",
  266,
  4,
  266,
  10
 ],
 [
  "tests/association_generics_test.go",
  319,
  4,
  319,
  10
 ],
 [
  "tests/association_generics_test.go",
  396,
  4,
  396,
  10
 ],
 [
  "tests/association_generics_test.go",
  400,
  4,
  400,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  23,
  4,
  23,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  126,
  4,
  126,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  130,
  4,
  130,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  141,
  4,
  141,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  160,
  4,
  160,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  16
... (47973 characters)
```

Actual:

```json
[
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/fuzz.go",
  398,
  5,
  398,
  11
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1353,
  17,
  1353,
  23
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1616,
  7,
  1616,
  13
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1758,
  4,
  1758,
  10
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1762,
  4,
  1762,
  10
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  1864,
  4,
  1864,
  10
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  2061,
  8,
  2061,
  14
 ],
 [
  "/opt/homebrew/Cellar/go/1.27.1/libexec/src/testing/testing.go",
  2075,
  5,
  2075,
  11
 ],
 [
  "statement_test.go",
  31,
  6,
  31,
  12
 ],
 [
  "statement_test.go",
  40,
  4,
  40,
  10
 ],
 [
  "statement_test.go",
  66,
  5,
  66,
  11
 ],
 [
  "tests/association_generics_test.go",
  266,
  4,
  266,
  10
 ],
 [
  "tests/association_generics_test.go",
  319,
  4,
  319,
  10
 ],
 [
  "tests/association_generics_test.go",
  396,
  4,
  396,
  10
 ],
 [
  "tests/association_generics_test.go",
  400,
  4,
  400,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  23,
  4,
  23,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  126,
  4,
  126,
  10
 ],
 [
  "tests/associations_belongs_to_test.go",
  130,
  4,
  130,
  10
 ],
 [
  "tests/associations_belongs_to_test.g
... (48129 characters)
```

Project file `tests/count_test.go`:

```
  56 | 	}
     ...
  58 | 	if err := DB.Model(&User{}).Where("name = ?", user1.Name).Or("name = ?", user3.Name).Count(&count).Find(&users).Error; err != nil {
  59 | 		t.Errorf("Count should work, but got err %v", err)
  60 | 	}
     ...
  62 | 	if count != int64(len(users)) {
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-references-extra-h5-e2e003/repro.json
```

## Evidence and reduction

- representative ddfee926b769-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 3 (10 probes, 227.374 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects go-gorm/gorm@b3d3bf219f02, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [golang/go#51037](https://github.com/golang/go/issues/51037) x/tools/gopls: Add support for workspace/{Will,Did}{Rename,Delete,Create}Files methods (open, 2022-02-06, 1 comments)
- [golang/go#59550](https://github.com/golang/go/issues/59550) x/tools/gopls: rename applies duplicate edits to a file with aliases (symlinks) (open, 2023-04-11, 0 comments)
- [golang/go#69563](https://github.com/golang/go/issues/69563) x/tools/gopls: Show specific file name when renaming failed. (closed, 2024-09-20, 3 comments)
- [golang/go#45317](https://github.com/golang/go/issues/45317) x/tools/gopls: renaming test file package declaration `package_test `-> `package` falsely claims import cycle (closed, 2021-03-31, 3 comments)
- [golang/go#32562](https://github.com/golang/go/issues/32562) x/tools/cmd/gopls: error when renaming a file (closed, 2019-06-12, 1 comments)
- [golang/go#81408](https://github.com/golang/go/issues/81408) x/tools/gopls: issues many redundant `go list` invocations concurrently (open, 2026-09-09, 5 comments)
- [golang/go#50151](https://github.com/golang/go/issues/50151) x/tools/gopls: high cpu usage when make changes in package which have some cgo package dependents (open, 2021-12-14, 15 comments)
- [golang/go#38028](https://github.com/golang/go/issues/38028) x/tools/gopls: support change signature refactoring (open, 2020-03-23, 9 comments)
- queries: `"rename file" in:title repo:golang/go is:issue label:gopls`; `references extra repo:golang/go is:issue label:gopls`; `references "rename file" repo:golang/go is:issue label:gopls`; `references stale repo:golang/go is:issue label:gopls`

## Server log excerpt (last confirming replay)

```
[gopls-v0.23.0-tre2e003-replay-baseline-20261118-235642-b7d571] textDocument/typeDefinition -> error 0: cannot find type name(s) from type func(format string, args ...any)
[gopls-v0.23.0-tre2e003-replay-control-20261118-235642-5f1bd2] textDocument/typeDefinition -> error 0: cannot find type name(s) from type func(format string, args ...any)
[gopls-v0.23.0-tre2e003-replay-history-20261118-235647-fd2fe2] textDocument/typeDefinition -> error 0: cannot find type name(s) from type func(format string, args ...any)
```
