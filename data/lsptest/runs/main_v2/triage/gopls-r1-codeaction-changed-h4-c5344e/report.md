# [gopls v0.23.0] codeAction changes its answer after configuration toggle a->b->a

Draft for the author (not filed). Group `gopls-r1-codeaction-changed-h4-c5344e`, signature `gopls|r1_history|codeAction:changed`, case family `H4`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `go-gorm/gorm@b3d3bf219f02` (corpus, commit b3d3bf219f0283f8e2e985bac509cb643170f729), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open tests/joins_test.go`
3. workspace/didChangeConfiguration: `set_config {"gopls": {"staticcheck": true}}`
4. Timing: wait until the server is idle after every step.
5. textDocument/didOpen `schema/relationship.go`, `utils/tests/dummy_dialecter.go` (the query step opens every target file that is not open), then wait until the server is idle.
6. Query `textDocument/codeAction` on `schema/relationship.go` line 638, column 59 (LSP position {line: 637, character: 58}) (diag:637:69); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Add test for Build",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for Build",
  "source.assembly"
 ],
 [
  "Browse documentation for method (*Constraint).Build",
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
  "Show compiler optimization details for \"schema\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"schema\"",
  "source.splitPackage"
 ],
 [
  "Split results into separate lines",
  "refactor.rewrite.splitLines"
 ]
]
```

Actual:

```json
[
 [
  "Add test for Build",
  "source.addTest"
 ],
 [
  "Browse arm64 assembly for Build",
  "source.assembly"
 ],
 [
  "Browse documentation for method (*Constraint).Build",
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
  "Show compiler optimization details for \"schema\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"schema\"",
  "source.splitPackage"
 ],
 [
  "Split results into separate lines",
  "refactor.rewrite.splitLines"
 ]
]
```

Project file `schema/relationship.go`:

```
 636 | func (constraint *Constraint) GetName() string { return constraint.Name }
     ...
 638 | func (constraint *Constraint) Build() (sql string, vars []interface{}) {
 639 | 	sql = "CONSTRAINT ? FOREIGN KEY ? REFERENCES ??"
 640 | 	if constraint.OnDelete != "" {
 641 | 		sql += " ON DELETE " + constraint.OnDelete
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-codeaction-changed-h4-c5344e/repro.json
```

## Evidence and reduction

- representative 43cf47dfbeec-v03: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 2 (6 probes, 122.562 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects go-gorm/gorm@b3d3bf219f02, zeromicro/go-zero@5b1b5bdc3adc, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#56158](https://github.com/golang/go/issues/56158) x/tools/gopls: diagnostics not cleared after configuration change (closed, 2022-10-11, 2 comments)
- [golang/go#70217](https://github.com/golang/go/issues/70217) x/tools/gopls: feature: offer a quickfix to define a struct field on "has no field or method" error (open, 2024-11-06, 8 comments)
- [golang/go#69523](https://github.com/golang/go/issues/69523) x/tools/gopls: long initial workspace load durations for workspace with many packages (open, 2024-09-18, 31 comments)
- [golang/go#50885](https://github.com/golang/go/issues/50885) x/tools/gopls: syntax error in go.mod blocks progress end notification (open, 2022-01-28, 12 comments)
- [golang/go#75527](https://github.com/golang/go/issues/75527) x/tools/gopls: Extract Function: shouldReturn appears at wrong index of ReturnStmt.Results (closed, 2025-09-18, 4 comments)
- [golang/go#77543](https://github.com/golang/go/issues/77543) x/tools/gopls: refactor.inline.variable sometimes (erroneously) inlines initial declarations (closed, 2026-02-11, 6 comments)
- [golang/go#78600](https://github.com/golang/go/issues/78600) x/tools/gopls: Disabled analyzers gets enabled by default (closed, 2026-04-09, 2 comments)
- [golang/go#54007](https://github.com/golang/go/issues/54007) x/tools/gopls: Either gopls cache always invalidates on 2nd save for M1 mac (or darwin, not sure) or vs code extension host fails, same config works perfectly on linux. (closed, 2022-07-16, 4 comments)
- queries: `"configuration change" in:title repo:golang/go is:issue label:gopls`; `"code action" wrong repo:golang/go is:issue label:gopls`; `"code action" "configuration change" repo:golang/go is:issue label:gopls`; `"code action" stale repo:golang/go is:issue label:gopls`

## Server log excerpt (last confirming replay)

```
[gopls-v0.23.0-trc5344e-replay-baseline-20261118-214242-05f6f5] textDocument/typeDefinition -> error 0: cannot find type name(s) from type interface{}
[gopls-v0.23.0-trc5344e-replay-baseline-20261118-214242-05f6f5] textDocument/references -> error 0: no identifier found
[gopls-v0.23.0-trc5344e-replay-control-20261118-214242-08dbdb] textDocument/typeDefinition -> error 0: cannot find type name(s) from type interface{}
[gopls-v0.23.0-trc5344e-replay-control-20261118-214242-08dbdb] textDocument/references -> error 0: no identifier found
[gopls-v0.23.0-trc5344e-replay-history-20261118-214246-2d4d23] textDocument/typeDefinition -> error 0: cannot find type name(s) from type interface{}
[gopls-v0.23.0-trc5344e-replay-history-20261118-214246-2d4d23] textDocument/references -> error 0: no identifier found
```
