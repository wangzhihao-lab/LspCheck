# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:NonSliceableOperand)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a`, signature `gopls|r4_edits|diagnostics:extra:NonSliceableOperand`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `evanw/esbuild@f6058f8364fe` (corpus, commit f6058f8364fe7ab91ca57a83e02577ed74c9cae4), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open internal/css_parser/css_decls_transform.go`
3. textDocument/didChange: `change internal/css_parser/css_decls_transform.go (260, 25)-(260, 29) "arggs"`
4. textDocument/didChange: `change internal/css_parser/css_decls_transform.go (260, 7)-(260, 7) "arggs := 0\n\t\t\t\t\t\t\t"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `internal/js_parser/json_parser.go`, `internal/logger/logger.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `internal/css_parser/css_decls_transform.go` line 261, column 26 (LSP position {line: 260, character: 25}) (M2:quickfix-errors:Create variable arggs); compare with the same query in a fresh session on the same content (expected).

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
  "NonSliceableOperand",
  "compiler",
  "cannot slice arggs (variable of type int)"
 ]
]
```

Project file `internal/css_parser/css_decls_transform.go`:

```
 258 | 						if tx.IsZero() && ty.IsZero() {
 259 | 							// "translate3d(0, 0, tz)" => "translateZ(tz)"
 260 | 							token.Text = "translateZ"
 261 | 							*token.Children = args[4:]
 262 | 						}
 263 | 					}
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-diagnostics-extra-nonsliceableoperand-mutation-m2-d80a9a/repro.json
```

## Evidence and reduction

- representative 31cdc65c834b-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 5.691 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects evanw/esbuild@f6058f8364fe, timings settled, seeds 2

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
