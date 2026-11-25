# [gopls v0.23.0] mutation:M3 edit is not valid (diagnostics:extra:UnusedImport)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-unusedimport-mutation-m3-aefa9e`, signature `gopls|r4_edits|diagnostics:extra:UnusedImport`, case family `mutation:M3`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `abiosoft/colima@bba803d3d6fa` (corpus, commit bba803d3d6fa9372a60f747e5dad4c8e80db7cde), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open cmd/ssh.go`
3. textDocument/didChange: `change cmd/ssh.go (24, 23)-(24, 29) ""`
4. textDocument/didChange: `change cmd/ssh.go (7, 0)-(21, 1) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `environment/container/kubernetes/kubernetes.go`, `util/downloader/http.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `cmd/ssh.go` line 9, column 5 (LSP position {line: 8, character: 4}) (M3:quickfix-errors:Delete var "sshCmd"); compare with the same query in a fresh session on the same content (expected).

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
  "UnusedImport",
  "compiler",
  "\"github.com/spf13/cobra\" imported and not used"
 ]
]
```

Project file `cmd/ssh.go`:

```
   1 | package cmd
     ...
   3 | import (
   4 | 	"github.com/abiosoft/colima/cmd/root"
   5 | 	"github.com/spf13/cobra"
   6 | )
     ...
   8 | // sshCmd represents the ssh command
   9 | var sshCmd = &cobra.Command{
  10 | 	Use:     "ssh",
  11 | 	Aliases: []string{"exec", "x"},
  12 | 	Short:   "SSH into the VM",
  13 | 	Long: `SSH into the VM.
     ...
  15 | Appending additional command runs the command instead.
  16 | e.g. 'colima ssh -- htop' will run htop.
     ...
  18 | It is recommended to specify '--' to differentiate from colima flags.`,
  19 | 	RunE: func(cmd *cobra.Command, args []string) error {
  20 | 		return newApp().SSH(args...)
  21 | 	},
  22 | }
     ...
  24 | func init() {
  25 | 	root.Cmd().AddCommand(sshCmd)
  26 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-diagnostics-extra-unusedimport-mutation-m3-aefa9e/repro.json
```

## Evidence and reduction

- representative bf89675973e9-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 3.628 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects abiosoft/colima@bba803d3d6fa, timings settled, seeds 1

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
