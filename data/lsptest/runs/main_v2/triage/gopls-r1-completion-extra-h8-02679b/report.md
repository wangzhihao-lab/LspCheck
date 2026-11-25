# [gopls v0.23.0] completion adds entries after query order

Draft for the author (not filed). Group `gopls-r1-completion-extra-h8-02679b`, signature `gopls|r1_history|completion:extra`, case family `H8`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `schollz/croc@5890191be511` (corpus, commit 5890191be511f9d0e44fc2ccb83c9458ffb86208), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/cli/updatecheck_test.go`
3. textDocument/didOpen: `open src/comm/comm.go`
4. textDocument/didOpen: `open src/croc/overwrite_test.go`
5. textDocument/didChange: `change src/croc/overwrite_test.go (88, 52)-(88, 55) "zz"`
6. textDocument/didChange: `change src/croc/overwrite_test.go (88, 52)-(88, 54) "err"`
7. request: `request src/croc/overwrite_test.go hover at (257, 22)`
8. request: `request src/croc/overwrite_test.go references at (101, 7)`
9. request: `request src/comm/comm.go hover at (212, 13)`
10. request: `request src/croc/overwrite_test.go typeDefinition at (102, 46)`
11. request: `request src/croc/overwrite_test.go documentHighlight at (159, 24)`
12. request: `request src/cli/updatecheck_test.go references at (340, 4)`
13. request: `request src/comm/comm.go completion at (52, 5)`
14. request: `request src/cli/updatecheck_test.go references at (121, 25)`
15. Timing: send the steps 0 ms apart without waiting, then wait until idle.
16. Query `textDocument/completion` on `src/cli/updatecheck_test.go` line 55, column 15 (LSP position {line: 54, character: 14}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "bool"
]
```

Actual:

```json
[
 "atomic.Bool",
 "bool",
 "internalcli.BoolFlag"
]
```

Project file `src/cli/updatecheck_test.go`:

```
  52 | 		name    string
  53 | 		latest  string
  54 | 		current string
  55 | 		want    bool
  56 | 	}{
  57 | 		{name: "major", latest: "12.0.0", current: "11.9.9", want: true},
  58 | 		{name: "minor", latest: "11.3.0", current: "11.2.9", want: true},
     ...
 119 | 	}
 120 | }
     ...
 122 | func TestFetchLatestReleaseHonorsCancellation(t *testing.T) {
 123 | 	started := make(chan struct{})
 124 | 	stopped := make(chan struct{})
 125 | 	client := &http.Client{Transport: roundTripFunc(func(request *http.Request) (*http.Response, error) {
     ...
 339 | 	for _, test := range []struct {
 340 | 		name  string
 341 | 		quiet bool
 342 | 		want  string
 343 | 	}{
 344 | 		{name: "notice", want: want},
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-completion-extra-h8-02679b/repro.json
```

## Evidence and reduction

- representative fb8107233528-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 13 -> 13 (32 probes, 255.551 s, reduced ops confirmed 0/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects schollz/croc@5890191be511, timings race0, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#82624](https://github.com/golang/go/issues/82624) x/tools/gopls: preserve interface method order when generating missing methods (open, 2026-10-27, 3 comments)
- [golang/go#73473](https://github.com/golang/go/issues/73473) x/tools/gopls: modernize.minmax: preserve order of operands, newlines, and comments (closed, 2025-04-22, 9 comments)
- [golang/go#60027](https://github.com/golang/go/issues/60027) x/tools/gopls: WorkspaceSymbol returns strange results in strange order (closed, 2023-05-06, 3 comments)
- [golang/go#46378](https://github.com/golang/go/issues/46378) x/tools/gopls: bad variadic completion ordering (closed, 2021-05-26, 1 comments)
- [golang/go#42626](https://github.com/golang/go/issues/42626) x/tools/gopls: order struct fields completions by definition (closed, 2020-11-16, 1 comments)
- [golang/go#32510](https://github.com/golang/go/issues/32510) x/tools/gopls: bad completion insertion after syntax error (open, 2019-06-09, 2 comments)
- [golang/go#61210](https://github.com/golang/go/issues/61210) x/tools/gopls: offer test function snippets as completion candidates in test files (open, 2023-07-06, 3 comments)
- [golang/go#32768](https://github.com/golang/go/issues/32768) x/tools/gopls: completion offers too many irrelevant candidates in struct literal (open, 2019-06-25, 18 comments)
- queries: `order in:title repo:golang/go is:issue label:gopls`; `completion extra repo:golang/go is:issue label:gopls`; `completion order repo:golang/go is:issue label:gopls`; `completion stale repo:golang/go is:issue label:gopls`
