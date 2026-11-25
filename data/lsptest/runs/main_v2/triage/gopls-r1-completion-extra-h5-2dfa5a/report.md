# [gopls v0.23.0] completion adds entries after file rename round trip

Draft for the author (not filed). Group `gopls-r1-completion-extra-h5-2dfa5a`, signature `gopls|r1_history|completion:extra`, case family `H5`.

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
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/cli/updatecheck_test.go -> src/cli/updatecheck_test_rt.go`
6. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/cli/updatecheck_test_rt.go -> src/cli/updatecheck_test.go`
7. Timing: wait until the server is idle after every step.
8. Query `textDocument/completion` on `src/cli/updatecheck_test.go` line 55, column 15 (LSP position {line: 54, character: 14}); compare with the same query in a fresh session opened on the final content (expected).

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
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-completion-extra-h5-2dfa5a/repro.json
```

## Evidence and reduction

- representative 5817b62f1d51-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 5 (5 probes, 224.163 s, reduced ops confirmed 0/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects schollz/croc@5890191be511, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#51037](https://github.com/golang/go/issues/51037) x/tools/gopls: Add support for workspace/{Will,Did}{Rename,Delete,Create}Files methods (open, 2022-02-06, 1 comments)
- [golang/go#59550](https://github.com/golang/go/issues/59550) x/tools/gopls: rename applies duplicate edits to a file with aliases (symlinks) (open, 2023-04-11, 0 comments)
- [golang/go#69563](https://github.com/golang/go/issues/69563) x/tools/gopls: Show specific file name when renaming failed. (closed, 2024-09-20, 3 comments)
- [golang/go#45317](https://github.com/golang/go/issues/45317) x/tools/gopls: renaming test file package declaration `package_test `-> `package` falsely claims import cycle (closed, 2021-03-31, 3 comments)
- [golang/go#32562](https://github.com/golang/go/issues/32562) x/tools/cmd/gopls: error when renaming a file (closed, 2019-06-12, 1 comments)
- [golang/go#32510](https://github.com/golang/go/issues/32510) x/tools/gopls: bad completion insertion after syntax error (open, 2019-06-09, 2 comments)
- [golang/go#61210](https://github.com/golang/go/issues/61210) x/tools/gopls: offer test function snippets as completion candidates in test files (open, 2023-07-06, 3 comments)
- [golang/go#32768](https://github.com/golang/go/issues/32768) x/tools/gopls: completion offers too many irrelevant candidates in struct literal (open, 2019-06-25, 18 comments)
- queries: `"rename file" in:title repo:golang/go is:issue label:gopls`; `completion extra repo:golang/go is:issue label:gopls`; `completion "rename file" repo:golang/go is:issue label:gopls`; `completion stale repo:golang/go is:issue label:gopls`
