# [gopls v0.23.0] semanticTokens adds entries after transformation T4

Draft for the author (not filed). Group `gopls-r5-semantictokens-extra-t4-867006`, signature `gopls|r5_transforms|semanticTokens:extra`, case family `T4`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `abiosoft/colima@bba803d3d6fa` (corpus, commit bba803d3d6fa9372a60f747e5dad4c8e80db7cde), language go

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T4 applied to `cmd/ssh.go` (26 edit(s), first [0, 11, 0, 11]).
3. Query `textDocument/semanticTokens/full` on `cmd/ssh.go` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  7,
  "keyword",
  ""
 ],
 [
  0,
  8,
  3,
  "namespace",
  ""
 ],
 [
  10,
  1,
  7,
  "property",
  "slice"
 ],
 [
  10,
  12,
  6,
  "type",
  "defaultLibrary,string"
 ],
 [
  10,
  19,
  6,
  "string",
  ""
 ],
 [
  10,
  27,
  3,
  "string",
  ""
 ],
 [
  11,
  1,
  5,
  "property",
  "string"
 ],
 [
  11,
  10,
  17,
  "string",
  ""
 ],
 [
  12,
  1,
  4,
  "property",
  "string"
 ],
 [
  12,
  7,
  17,
  "string",
  ""
 ],
 [
  14,
  0,
  54,
  "string",
  ""
 ],
 [
  15,
  0,
  40,
  "string",
  ""
 ],
 [
  17,
  0,
  70,
  "string",
  ""
 ],
 [
  18,
  1,
  4,
  "property",
  "signature"
 ],
 [
  18,
  12,
  3,
  "parameter",
  "definition,pointer"
 ],
 [
  18,
  16,
  1,
  "operator",
  ""
 ],
 [
  18,
  17,
  5,
  "namespace",
  ""
 ],
 [
  18,
  23,
  7,
  "type",
  "struct"
 ],
 [
  18,
  32,
  4,
  "parameter",
  "definition,slice"
 ],
 [
  18,
  39,
  6,
  "type",
  "defaultLibrary,string"
 ],
 [
  18,
  47,
  5,
  "type",
  "defaultLibrary,interface"
 ],
 [
  18,
  7,
  4,
  "keyword",
  ""
 ],
 [
  19,
  18,
  3,
  "method",
  "signature"
 ],
 [
  19,
  2,
  6,
  "keyword",
  ""
 ],
 [
  19,
  22,
  4,
  "parameter",
  "slice"
 ],
 [
  19,
  26,
  3,
  "operator",
  ""
 ],
 [
  19,
  9,
  6,
  "function",
  "signature"
 ],
 [
  2,
  0,
  6,
  "keyword",
  ""
 ],
 [
  23,
  0,
  4,
  "keyword",
  ""
 ],
 [
  23,
  5,
  4,
  "function",
  "definition,signature"
 ],
 [
  24,
  1,
  4,
  "namespace",
  ""
 ],
 [
  24,
  12,
  10,
  "method",
  "
... (2072 characters)
```

Actual:

```json
[
 [
  0,
  0,
  7,
  "keyword",
  ""
 ],
 [
  0,
  8,
  3,
  "namespace",
  ""
 ],
 [
  10,
  1,
  7,
  "property",
  "slice"
 ],
 [
  10,
  12,
  6,
  "type",
  "defaultLibrary,string"
 ],
 [
  10,
  19,
  6,
  "string",
  ""
 ],
 [
  10,
  27,
  3,
  "string",
  ""
 ],
 [
  11,
  1,
  5,
  "property",
  "string"
 ],
 [
  11,
  10,
  17,
  "string",
  ""
 ],
 [
  12,
  1,
  4,
  "property",
  "string"
 ],
 [
  12,
  7,
  17,
  "string",
  ""
 ],
 [
  13,
  0,
  0,
  "string",
  ""
 ],
 [
  14,
  0,
  54,
  "string",
  ""
 ],
 [
  15,
  0,
  40,
  "string",
  ""
 ],
 [
  17,
  0,
  70,
  "string",
  ""
 ],
 [
  18,
  1,
  4,
  "property",
  "signature"
 ],
 [
  18,
  12,
  3,
  "parameter",
  "definition,pointer"
 ],
 [
  18,
  16,
  1,
  "operator",
  ""
 ],
 [
  18,
  17,
  5,
  "namespace",
  ""
 ],
 [
  18,
  23,
  7,
  "type",
  "struct"
 ],
 [
  18,
  32,
  4,
  "parameter",
  "definition,slice"
 ],
 [
  18,
  39,
  6,
  "type",
  "defaultLibrary,string"
 ],
 [
  18,
  47,
  5,
  "type",
  "defaultLibrary,interface"
 ],
 [
  18,
  7,
  4,
  "keyword",
  ""
 ],
 [
  19,
  18,
  3,
  "method",
  "signature"
 ],
 [
  19,
  2,
  6,
  "keyword",
  ""
 ],
 [
  19,
  22,
  4,
  "parameter",
  "slice"
 ],
 [
  19,
  26,
  3,
  "operator",
  ""
 ],
 [
  19,
  9,
  6,
  "function",
  "signature"
 ],
 [
  2,
  0,
  6,
  "keyword",
  ""
 ],
 [
  23,
  0,
  4,
  "keyword",
  ""
 ],
 [
  23,
  5,
  4,
  "function",
  "definition,signature"
 ],
 [
  24,
  1,
  4,
  "namespace",
  ""

... (2112 characters)
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r5-semantictokens-extra-t4-867006/repro.json
```

## Evidence and reduction

- representative 9a36d7461bcd-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 27 -> 2 (5 probes, 73.097 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects abiosoft/colima@bba803d3d6fa, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#80666](https://github.com/golang/go/issues/80666) x/tools/gopls: assembly identifier positions drift in CRLF files (closed, 2026-07-31, 3 comments)
- [golang/go#47200](https://github.com/golang/go/issues/47200) x/tools/gopls: autoimport doesn't work properly in VS Code when using CRLF line endings (closed, 2021-07-14, 4 comments)
- [golang/go#46791](https://github.com/golang/go/issues/46791) x/tools/gopls: unimported completions produces invalid edits with windows line endings when CRLF is used (closed, 2021-05-09, 32 comments)
- [golang/go#42923](https://github.com/golang/go/issues/42923) x/tools/gopls: comments duplicated with CRLF files (closed, 2020-12-01, 8 comments)
- [golang/go#41057](https://github.com/golang/go/issues/41057) x/tools/gopls: bad formatting with CRLF line ending (closed, 2020-08-27, 2 comments)
- [golang/go#79524](https://github.com/golang/go/issues/79524) x/tools/gopls: semantic tokens no longer returned (regression in v0.22.0) (closed, 2026-05-19, 11 comments)
- [golang/go#47465](https://github.com/golang/go/issues/47465) x/tools/gopls: initial semantic token request slow (closed, 2021-07-29, 13 comments)
- [golang/go#69341](https://github.com/golang/go/issues/69341) x/tools/gopls: Extract Function refactor doesn't put testing.T/B first (closed, 2024-09-08, 3 comments)
- queries: `CRLF in:title repo:golang/go is:issue label:gopls`; `"semantic tokens" extra repo:golang/go is:issue label:gopls`; `"semantic tokens" CRLF repo:golang/go is:issue label:gopls`; `"semantic tokens" whitespace repo:golang/go is:issue label:gopls`
