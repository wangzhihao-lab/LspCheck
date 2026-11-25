# [gopls v0.23.0] mutation:M3 edit is not valid (diagnostics:extra:WrongArgCount)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-wrongargcount-mutation-m3-ac10cc`, signature `gopls|r4_edits|diagnostics:extra:WrongArgCount`, case family `mutation:M3`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `schollz/croc@5890191be511` (corpus, commit 5890191be511f9d0e44fc2ccb83c9458ffb86208), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/cli/updatecheck_test.go`
3. textDocument/didChange: `change src/cli/updatecheck_test.go (228, 30)-(228, 73) ""`
4. textDocument/didChange: `change src/cli/updatecheck_test.go (226, 1)-(226, 8) "_"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/comm/comm.go`, `src/croc/overwrite_test.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `src/cli/updatecheck_test.go` line 227, column 2 (LSP position {line: 226, character: 1}) (M3:quickfix-errors:Remove variable checker); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  0,
  0,
  0,
  0,
  1,
  "WrongArgCount",
  "compiler",
  "not enough arguments in call to awaitVersionCheck have (*testing.T) want (*testing.T, versionCheckHandle)"
 ]
]
```

Project file `src/cli/updatecheck_test.go`:

```
 224 | 		t.Fatal(err)
 225 | 	}
 226 | 	var requests atomic.Int32
 227 | 	checker, closeServer := newTestVersionChecker(t, cachePath, now, &requests, http.StatusOK, `{"tag_name":"v11.2.3"}`)
 228 | 	defer closeServer()
 229 | 	result := awaitVersionCheck(t, checker.start(context.Background(), true))
 230 | 	if result.latestVersion != "11.2.3" || requests.Load() != 1 {
 231 | 		t.Fatalf("forced result = %q with %d requests", result.latestVersion, requests.Load())
 232 | 	}
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-diagnostics-extra-wrongargcount-mutation-m3-ac10cc/repro.json
```

## Evidence and reduction

- representative fb67fdd2dc04-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.871 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects schollz/croc@5890191be511, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#68075](https://github.com/golang/go/issues/68075) x/tools/gopls/internal/cmd: `gopls check` doesn't wait for didOpen finish before it makes diagnostics request (open, 2024-06-19, 4 comments)
- [golang/go#41436](https://github.com/golang/go/issues/41436) x/tools/go/analysis: a Diagnostic should indicate when it is a lint-style warning that should be ignored in generated code (open, 2020-09-16, 34 comments)
- [golang/go#70085](https://github.com/golang/go/issues/70085) x/tools/gopls: add refactor.inline.variable-all code action (open, 2024-10-29, 11 comments)
- [golang/go#50151](https://github.com/golang/go/issues/50151) x/tools/gopls: high cpu usage when make changes in package which have some cgo package dependents (open, 2021-12-14, 15 comments)
- [golang/go#54461](https://github.com/golang/go/issues/54461) x/tools/gopls: regtest flakes due to hanging go commands (open, 2022-08-15, 422 comments)
- [golang/go#69646](https://github.com/golang/go/issues/69646) x/tools/gopls: packages.Load failure with conflicting go.work and go.mod toolchain versions (open, 2024-09-16, 5 comments)
- [golang/go#79892](https://github.com/golang/go/issues/79892) x/tools/gopls: mcp go_diagnostics misattributes diagnostics to files[0] (and drops its own) when given multiple files (closed, 2026-06-07, 2 comments)
- [golang/go#68026](https://github.com/golang/go/issues/68026) x/tools/gopls: broken hovering in the builtin file (closed, 2024-06-16, 11 comments)
- queries: `diagnostics extra repo:golang/go is:issue label:gopls`; `diagnostics "wrong edit" repo:golang/go is:issue label:gopls`
