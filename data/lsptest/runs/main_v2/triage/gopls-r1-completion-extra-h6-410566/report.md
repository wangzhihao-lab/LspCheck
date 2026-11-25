# [gopls v0.23.0] completion adds entries after depended-on file round trip

Draft for the author (not filed). Group `gopls-r1-completion-extra-h6-410566`, signature `gopls|r1_history|completion:extra`, case family `H6`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `zeromicro/go-zero@5b1b5bdc3adc` (corpus, commit 5b1b5bdc3adcc189b3bd8b77f2cc8a363ec3374c), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open core/logx/syslog_test.go`
3. textDocument/didOpen: `open tools/goctl/internal/cobrax/cobrax.go`
4. textDocument/didOpen: `open zrpc/server_test.go`
5. file written on disk, then workspace/didChangeWatchedFiles: `fs_write tools/goctl/util/ctx/context.go (1979 chars)`
6. file written on disk, then workspace/didChangeWatchedFiles: `fs_write tools/goctl/util/ctx/context.go (1978 chars)`
7. Timing: wait until the server is idle after every step.
8. Query `textDocument/completion` on `tools/goctl/internal/cobrax/cobrax.go` line 49, column 67 (LSP position {line: 48, character: 66}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "string"
]
```

Actual:

```json
[
 "fmt.GoStringer",
 "fmt.Stringer",
 "string"
]
```

Project file `tools/goctl/internal/cobrax/cobrax.go`:

```
   1 | package cobrax
     ...
   3 | import (
   4 | 	"fmt"
     ...
   6 | 	"github.com/spf13/cobra"
   7 | 	"github.com/spf13/pflag"
   8 | 	"github.com/zeromicro/go-zero/tools/goctl/internal/flags"
   9 | )
     ...
  11 | type Option func(*cobra.Command)
     ...
  13 | func WithRunE(runE func(*cobra.Command, []string) error) Option {
  14 | 	return func(cmd *cobra.Command) {
  15 | 		cmd.RunE = runE
  16 | 	}
  17 | }
     ...
  19 | func WithRun(run func(*cobra.Command, []string)) Option {
  20 | 	return func(cmd *cobra.Command) {
  21 | 		cmd.Run = run
  22 | 	}
  23 | }
     ...
  25 | func WithArgs(arg cobra.PositionalArgs) Option {
  26 | 	return func(command *cobra.Command) {
  27 | 		command.Args = arg
  28 | 	}
  29 | }
     ...
  31 | func WithHidden() Option {
  32 | 	return func(command *cobra.Command) {
  33 | 		command.Hidden = true
  34 | 	}
  35 | }
     ...
  37 | type Command struct {
  38 | 	*cobra.Command
  39 | }
     ...
  41 | type FlagSet struct {
  42 | 	*pflag.FlagSet
  43 | }
     ...
  45 | func (f *FlagSet) StringVar(p *string, name string) {
  46 | 	f.StringVarWithDefaultValue(p, name, "")
  47 | }
     ...
  49 | func (f *FlagSet) StringVarWithDefaultValue(p *string, name string, value string) {
  50 | 	f.FlagSet.StringVar(p, name, value, "")
  51 | }
     ...
  53 | func (f *FlagSet) StringVarP(p *string, name, shorthand string) {
  54 | 	f.StringVarPWithDefaultValue(p, name, shorthand, "")
  55 | }
     ...
  57 | func (f *FlagSet) StringVarPWithDefaultValue(p *string, name, shorthand string, value string) {
  58 | 	f.FlagSet.StringVarP(p, name, shorthand, value, "")
  59 | }
     ...
  61 | func (f *FlagSet) BoolVar(p *bool, name string) {
  62 | 	f.BoolVarWithDefaultValue(p, name, false)
  63 | }
     ...
  65 | func (f *FlagSet) BoolVarWithDefaultValue(p *bool, name string, value bool) {
  66 | 	f.FlagSet.BoolVar(p, name, value, "")
  67 | }
     ...
  69 | func (f *FlagSet) BoolVarP(p *bool, name, shorthand string) {
  70 | 	f.BoolVarPWithDefaultValue(p, name, shorthand, false)
  71 | }
     ...
  73 | func (f *FlagSet) BoolVarPWithDefaultValue(p *bool, name, shorthand string, value bool) {
  74 | 	f.FlagSet.BoolVarP(p, name, shorthand, value, "")
  75 | }
     ...
  77 | func (f *FlagSet) IntVar(p *int, name string) {
  78 | 	f.IntVarWithDefaultValue(p, name, 0)
  79 | }
     ...
  81 | func (f *FlagSet) IntVarWithDefaultValue(p *int, name string, value int) {
  82 | 	f.FlagSet.IntVar(p, name, value, "")
  83 | }
     ...
  85 | func (f *FlagSet) StringSliceVarP(p *[]string, name, shorthand string) {
  86 | 	f.FlagSet.StringSliceVarP(p, name, shorthand, []string{}, "")
  87 | }
     ...
  89 | func (f *FlagSet) StringSliceVarPWithDefaultValue(p *[]string, name, shorthand string, value []string) {
  90 | 	f.FlagSet.StringSliceVarP(p, name, shorthand, value, "")
  91 | }
     ...
  93 | func (f *FlagSet) StringSliceVar(p *[]string, name string) {
  94 | 	f.StringSliceVarWithDefaultValue(p, name, []string{})
  95 | }
     ...
  97 | func (f *FlagSet) StringSliceVarWithDefaultValue(p *[]string, name string, value []string) {
  98 | 	f.FlagSet.StringSliceVar(p, name, value, "")
  99 | }
     ...
 101 | func NewCommand(use string, opts ...Option) *Command {
 102 | 	c := &Command{
 103 | 		Command: &cobra.Command{
 104 | 			Use: use,
 105 | 		},
 106 | 	}
     ...
 108 | 	for _, opt := range opts {
 109 | 		opt(c.Command)
 110 | 	}
     ...
 112 | 	return c
 113 | }
     ...
 115 | func (c *Command) AddCommand(cmds ...*Command) {
 116 | 	for _, cmd := range cmds {
 117 | 		c.Command.AddCommand(cmd.Command)
 118 | 	}
 119 | }
     ...
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r1-completion-extra-h6-410566/repro.json
```

## Evidence and reduction

- representative 5839938760f5-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 5 (4 probes, 168.436 s, reduced ops confirmed 0/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects zeromicro/go-zero@5b1b5bdc3adc, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [golang/go#50748](https://github.com/golang/go/issues/50748) x/tools/gopls/internal/regtest/workspace: frequent failures in TestWatchReplaceTargets with ‘Unmet: completed work "diagnosing files changed on disk"’ (closed, 2022-01-21, 3 comments)
- [golang/go#54983](https://github.com/golang/go/issues/54983) x/tools/gopls: resend diagnostics for changed files (closed, 2022-09-09, 2 comments)
- [golang/go#42499](https://github.com/golang/go/issues/42499) x/tools/gopls: add a second analysis diagnostics pass for changed files (closed, 2020-11-11, 1 comments)
- [golang/go#32510](https://github.com/golang/go/issues/32510) x/tools/gopls: bad completion insertion after syntax error (open, 2019-06-09, 2 comments)
- [golang/go#61210](https://github.com/golang/go/issues/61210) x/tools/gopls: offer test function snippets as completion candidates in test files (open, 2023-07-06, 3 comments)
- [golang/go#32768](https://github.com/golang/go/issues/32768) x/tools/gopls: completion offers too many irrelevant candidates in struct literal (open, 2019-06-25, 18 comments)
- [golang/go#63282](https://github.com/golang/go/issues/63282) x/tools/gopls: express completion scoring in terms of down-ranking factors (open, 2023-09-28, 2 comments)
- [golang/go#65944](https://github.com/golang/go/issues/65944) x/tools/gopls: extract variable returns an extra lhs expression and no template edit support is available (open, 2024-02-22, 5 comments)
- queries: `"file changed" in:title repo:golang/go is:issue label:gopls`; `completion extra repo:golang/go is:issue label:gopls`; `completion "file changed" repo:golang/go is:issue label:gopls`; `completion stale repo:golang/go is:issue label:gopls`
