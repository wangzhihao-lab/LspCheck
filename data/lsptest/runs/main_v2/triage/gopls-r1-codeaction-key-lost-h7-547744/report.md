# [gopls v0.23.0] codeAction is not answered after interleaving of h1-h6, h8, h9

Draft for the author (not filed). Group `gopls-r1-codeaction-key-lost-h7-547744`, signature `gopls|r1_history|codeAction:key-lost`, case family `H7`.

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
9. Query `textDocument/codeAction` on `tests/joins_test.go` line 10, column 2 (LSP position {line: 9, character: 1}) (diag:9:15); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Browse documentation for package gorm",
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
  "Convert to raw string literal",
  "refactor.rewrite.changeQuote"
 ],
 [
  "Show compiler optimization details for \"tests\"",
  "source.toggleCompilerOptDetails"
 ],
 [
  "Split package \"tests_test\"",
  "source.splitPackage"
 ],
 [
  "go get package gorm.io/gorm",
  "quickfix"
 ]
]
```

Actual:

```json
[
 "missing-key"
]
```

Project file `tests/joins_test.go`:

```
   7 | 	"testing"
     ...
   9 | 	"github.com/stretchr/testify/assert"
  10 | 	"gorm.io/gorm"
  11 | 	. "gorm.io/gorm/utils/tests"
  12 | )
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-codeaction-key-lost-h7-547744/repro.json
```

## Evidence and reduction

- representative 43cf47dfbeec-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 15 -> 6 (10 probes, 250.19 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects go-gorm/gorm@b3d3bf219f02, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#81812](https://github.com/golang/go/issues/81812) x/tools/gopls: codeAction/resolve after a document change computes the edit at the old position (open, 2026-09-28, 4 comments)
- [golang/go#70604](https://github.com/golang/go/issues/70604) x/tools/gopls: marker test should ensure type checked file remain type checked after code edits (closed, 2024-11-27, 1 comments)
- [golang/go#59587](https://github.com/golang/go/issues/59587) x/tools/gopls: diagnostics only clear after diagnosticsDelay for edited files (closed, 2023-04-12, 1 comments)
- [golang/go#51325](https://github.com/golang/go/issues/51325) x/tools/gopls: push diagnostics after `go mod edit -go=1.18` (closed, 2022-02-22, 1 comments)
- [golang/go#33989](https://github.com/golang/go/issues/33989) x/tools/gopls: Context cancelled errors after some editing (closed, 2019-08-30, 4 comments)
- [golang/go#74644](https://github.com/golang/go/issues/74644) x/tools/gopls: Misguided missing method code action (open, 2025-07-16, 5 comments)
- [golang/go#82624](https://github.com/golang/go/issues/82624) x/tools/gopls: preserve interface method order when generating missing methods (open, 2026-10-27, 3 comments)
- [golang/go#39805](https://github.com/golang/go/issues/39805) x/tools/gopls: convert 'gofumpt' from formatter to code action provider (open, 2020-06-24, 5 comments)
- queries: `"after edit" in:title repo:golang/go is:issue label:gopls`; `"code action" missing repo:golang/go is:issue label:gopls`; `"code action" "after edit" repo:golang/go is:issue label:gopls`; `"code action" stale repo:golang/go is:issue label:gopls`

## Server log excerpt (last confirming replay)

```
[gopls-v0.23.0-tr547744-replay-baseline-20261118-215850-f70b6e] textDocument/typeDefinition -> error 0: no enclosing expression has a type
[gopls-v0.23.0-tr547744-replay-baseline-20261118-215850-f70b6e] window/logMessage type 1: 2026/11/18 21:58:54 imports fixes: allImportsFixes: temp/lsptest_runs/gopls-v0.23.0-tr547744-replay-baseline-20261118-215850-f70b6e/ws/utils/tests/dummy_dialecter.go:3:11: missi
[gopls-v0.23.0-tr547744-replay-control-20261118-215850-47a4ec] textDocument/typeDefinition -> error 0: no enclosing expression has a type
[gopls-v0.23.0-tr547744-replay-control-20261118-215850-47a4ec] window/logMessage type 1: 2026/11/18 21:58:54 imports fixes: allImportsFixes: temp/lsptest_runs/gopls-v0.23.0-tr547744-replay-control-20261118-215850-47a4ec/ws/utils/tests/dummy_dialecter.go:3:11: missing
[gopls-v0.23.0-tr547744-replay-history-20261118-215854-90d8bc] textDocument/typeDefinition -> error 0: no enclosing expression has a type
[gopls-v0.23.0-tr547744-replay-history-20261118-215854-90d8bc] window/logMessage type 1: 2026/11/18 21:59:17 imports fixes: allImportsFixes: temp/lsptest_runs/gopls-v0.23.0-tr547744-replay-history-20261118-215854-90d8bc/ws/utils/tests/dummy_dialecter.go:3:11: missing
```
