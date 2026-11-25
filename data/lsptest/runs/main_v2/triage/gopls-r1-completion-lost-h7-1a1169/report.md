# [gopls v0.23.0] completion loses its answer after interleaving of h1-h6, h8, h9

Draft for the author (not filed). Group `gopls-r1-completion-lost-h7-1a1169`, signature `gopls|r1_history|completion:lost`, case family `H7`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `iawia002/lux@dd00f6d258d8` (corpus, commit dd00f6d258d80b6684a0b9402d7124e5c18ef42f), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open extractors/streamtape/streamtape_test.go`
3. textDocument/didOpen: `open extractors/yinyuetai/yinyuetai.go`
4. file written on disk, then workspace/didChangeWatchedFiles: `fs_write go.mod (2487 chars)`
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename extractors/geekbang/geekbang_test.go -> extractors/geekbang/geekbang_test_rt.go`
6. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename extractors/geekbang/geekbang_test_rt.go -> extractors/geekbang/geekbang_test.go`
7. file written on disk, then workspace/didChangeWatchedFiles: `fs_write go.mod (2489 chars)`
8. Timing: wait until the server is idle after every step.
9. textDocument/didOpen `extractors/geekbang/geekbang_test.go` (the query step opens every target file that is not open), then wait until the server is idle.
10. Query `textDocument/completion` on `extractors/geekbang/geekbang_test.go` line 12, column 14 (LSP position {line: 11, character: 13}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "string"
]
```

Actual:

```json
[]
```

Project file `extractors/geekbang/geekbang_test.go`:

```
   1 | package geekbang
     ...
   3 | import (
   4 | 	"testing"
     ...
   6 | 	"github.com/iawia002/lux/extractors"
   7 | 	"github.com/iawia002/lux/test"
   8 | )
     ...
  10 | func TestDownload(t *testing.T) {
  11 | 	tests := []struct {
  12 | 		name string
  13 | 		args test.Args
  14 | 	}{
  15 | 		{
  16 | 			name: "normal test",
  17 | 			args: test.Args{
  18 | 				URL:   "https://time.geekbang.org/course/detail/190-97203",
  19 | 				Title: "02 | 内容综述 - 玩转webpack",
  20 | 				Size:  10752472,
  21 | 			},
  22 | 		},
  23 | 	}
  24 | 	for _, tt := range tests {
  25 | 		t.Run(tt.name, func(t *testing.T) {
  26 | 			data, err := New().Extract(tt.args.URL, extractors.Options{})
  27 | 			test.CheckError(t, err)
  28 | 			test.Check(t, tt.args, data[0])
  29 | 		})
  30 | 	}
  31 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-completion-lost-h7-1a1169/repro.json
```

## Evidence and reduction

- representative a182be2619cd-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 7 -> 6 (11 probes, 2432.804 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects iawia002/lux@dd00f6d258d8, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#81812](https://github.com/golang/go/issues/81812) x/tools/gopls: codeAction/resolve after a document change computes the edit at the old position (open, 2026-09-28, 4 comments)
- [golang/go#70604](https://github.com/golang/go/issues/70604) x/tools/gopls: marker test should ensure type checked file remain type checked after code edits (closed, 2024-11-27, 1 comments)
- [golang/go#59587](https://github.com/golang/go/issues/59587) x/tools/gopls: diagnostics only clear after diagnosticsDelay for edited files (closed, 2023-04-12, 1 comments)
- [golang/go#51325](https://github.com/golang/go/issues/51325) x/tools/gopls: push diagnostics after `go mod edit -go=1.18` (closed, 2022-02-22, 1 comments)
- [golang/go#33989](https://github.com/golang/go/issues/33989) x/tools/gopls: Context cancelled errors after some editing (closed, 2019-08-30, 4 comments)
- [golang/go#82092](https://github.com/golang/go/issues/82092) x/tools/gopls: completion: don't suggest selectors that are illegal because of same-depth conflicts (open, 2026-10-09, 6 comments)
- [golang/go#81658](https://github.com/golang/go/issues/81658) x/tools/gopls: completion of receiver types depends on where in the file the type is defined (open, 2026-09-22, 2 comments)
- [golang/go#73426](https://github.com/golang/go/issues/73426) x/tools/gopls: no autocompletion when missing closing parenthesis (open, 2025-04-17, 6 comments)
- queries: `"after edit" in:title repo:golang/go is:issue label:gopls`; `completion missing repo:golang/go is:issue label:gopls`; `completion "after edit" repo:golang/go is:issue label:gopls`; `completion stale repo:golang/go is:issue label:gopls`

## Server log excerpt (last confirming replay)

```
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:11 go/packages.Load #3: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at temp/lsptest_runs/gopls-v0.
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:11 reloading workspace: packages.Load error: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at temp/l
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:11 errors loading workspace: temp/lsptest_runs/gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412/ws/go.mod:59: syntax error (unterminated block starte
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:11 go/packages.Load #4: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at temp/lsptest_runs/gopls-v0.
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:11 MetadataForFile: packages.Load error: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at temp/lspte
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:12 go/packages.Load #5: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at temp/lsptest_runs/gopls-v0.
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:12 MetadataForFile: packages.Load error: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at temp/lspte
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:30:34 failed to get import resolver: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at temp/lsptest_runs
[gopls-v0.23.0-tr1a1169-replay-history-20261118-233004-b13412] window/logMessage type 1: 2026/11/18 23:40:37 no completions found: failed to collect completions: err: exit status 1: stderr: go: errors parsing go.mod: go.mod:59: syntax error (unterminated block started at ~/Developer/
```
