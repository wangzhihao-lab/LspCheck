# [gopls v0.23.0] codeAction changes its answer after interleaving of h1-h6, h8, h9

Draft for the author (not filed). Group `gopls-r1-codeaction-changed-h7-383b05`, signature `gopls|r1_history|codeAction:changed`, case family `H7`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `go-gorm/gorm@b3d3bf219f02` (corpus, commit b3d3bf219f0283f8e2e985bac509cb643170f729), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open tests/non_std_test.go`
3. workspace/didChangeConfiguration: `set_config {"gopls": {"completeUnimported": false}}`
4. Timing: wait until the server is idle after every step.
5. textDocument/didOpen `chainable_api.go`, `tests/count_test.go` (the query step opens every target file that is not open), then wait until the server is idle.
6. Query `textDocument/codeAction` on `chainable_api.go` line 18, column 27 (LSP position {line: 17, character: 26}) (diag:17:37); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Add test for Model",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for Model",
  "source.assembly"
 ],
 [
  "Browse documentation for method (*DB).Model",
  "source.doc"
 ],
 [
  "Browse free symbols",
  "source.freesymbols"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Replace interface{} by any",
  "quickfix"
 ],
 [
  "Show compiler optimization details for \"ws\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"gorm\"",
  "source.splitPackage"
 ]
]
```

Actual:

```json
[
 [
  "Add test for Model",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for Model",
  "source.assembly"
 ],
 [
  "Browse documentation for method (*DB).Model",
  "source.doc"
 ],
 [
  "Browse free symbols",
  "source.freesymbols"
 ],
 [
  "Browse gopls feature documentation",
  "gopls.doc.features"
 ],
 [
  "Replace interface{} by any",
  "quickfix"
 ],
 [
  "Replace interface{} by any",
  "quickfix"
 ],
 [
  "Show compiler optimization details for \"ws\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"gorm\"",
  "source.splitPackage"
 ]
]
```

Project file `chainable_api.go`:

```
  15 | //	db.Model(&User{}).Update("name", "hello")
  16 | //	// if user's primary key is non-blank, will use it as condition, then will only update that user's name to `hello`
  17 | //	db.Model(&user).Update("name", "hello")
  18 | func (db *DB) Model(value interface{}) (tx *DB) {
  19 | 	tx = db.getInstance()
  20 | 	tx.Statement.Model = value
  21 | 	return
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-codeaction-changed-h7-383b05/repro.json
```

## Evidence and reduction

- representative ddfee926b769-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 13 -> 2 (11 probes, 361.838 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects go-gorm/gorm@b3d3bf219f02, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [golang/go#81812](https://github.com/golang/go/issues/81812) x/tools/gopls: codeAction/resolve after a document change computes the edit at the old position (open, 2026-09-28, 4 comments)
- [golang/go#70604](https://github.com/golang/go/issues/70604) x/tools/gopls: marker test should ensure type checked file remain type checked after code edits (closed, 2024-11-27, 1 comments)
- [golang/go#59587](https://github.com/golang/go/issues/59587) x/tools/gopls: diagnostics only clear after diagnosticsDelay for edited files (closed, 2023-04-12, 1 comments)
- [golang/go#51325](https://github.com/golang/go/issues/51325) x/tools/gopls: push diagnostics after `go mod edit -go=1.18` (closed, 2022-02-22, 1 comments)
- [golang/go#33989](https://github.com/golang/go/issues/33989) x/tools/gopls: Context cancelled errors after some editing (closed, 2019-08-30, 4 comments)
- [golang/go#70217](https://github.com/golang/go/issues/70217) x/tools/gopls: feature: offer a quickfix to define a struct field on "has no field or method" error (open, 2024-11-06, 8 comments)
- [golang/go#69523](https://github.com/golang/go/issues/69523) x/tools/gopls: long initial workspace load durations for workspace with many packages (open, 2024-09-18, 31 comments)
- [golang/go#50885](https://github.com/golang/go/issues/50885) x/tools/gopls: syntax error in go.mod blocks progress end notification (open, 2022-01-28, 12 comments)
- queries: `"after edit" in:title repo:golang/go is:issue label:gopls`; `"code action" wrong repo:golang/go is:issue label:gopls`; `"code action" "after edit" repo:golang/go is:issue label:gopls`; `"code action" stale repo:golang/go is:issue label:gopls`

## Server log excerpt (last confirming replay)

```
[gopls-v0.23.0-tr383b05-replay-baseline-20261118-215214-14f36e] textDocument/typeDefinition -> error 0: cannot find type name(s) from type interface{}
[gopls-v0.23.0-tr383b05-replay-baseline-20261118-215214-14f36e] textDocument/references -> error 0: no identifier found
[gopls-v0.23.0-tr383b05-replay-control-20261118-215214-d20118] textDocument/typeDefinition -> error 0: cannot find type name(s) from type interface{}
[gopls-v0.23.0-tr383b05-replay-control-20261118-215214-d20118] textDocument/references -> error 0: no identifier found
[gopls-v0.23.0-tr383b05-replay-history-20261118-215219-94b116] textDocument/typeDefinition -> error 0: cannot find type name(s) from type interface{}
[gopls-v0.23.0-tr383b05-replay-history-20261118-215219-94b116] textDocument/references -> error 0: no identifier found
```
