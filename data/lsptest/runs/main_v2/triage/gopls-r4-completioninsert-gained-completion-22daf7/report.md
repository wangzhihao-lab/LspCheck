# [gopls v0.23.0] completion edit is not valid (completionInsert:gained)

Draft for the author (not filed). Group `gopls-r4-completioninsert-gained-completion-22daf7`, signature `gopls|r4_edits|completionInsert:gained`, case family `completion`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `docker/compose@c6dffb26bdfd` (corpus, commit c6dffb26bdfd94efb1f4e1c743f1241a150d120a), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/completion` on `cmd/cmdtrace/cmd_span_test.go` at line 29, column 29 (LSP position {line: 28, character: 28}); insert the item: the file must not gain a syntax error.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "missing ',' in parameter list",
 "missing parameter type"
]
```

Project file `cmd/cmdtrace/cmd_span_test.go`:

```
   1 | /*
   2 |    Copyright 2020 Docker Compose CLI authors
     ...
   4 |    Licensed under the Apache License, Version 2.0 (the "License");
   5 |    you may not use this file except in compliance with the License.
   6 |    You may obtain a copy of the License at
     ...
   8 |        http://www.apache.org/licenses/LICENSE-2.0
     ...
  10 |    Unless required by applicable law or agreed to in writing, software
  11 |    distributed under the License is distributed on an "AS IS" BASIS,
  12 |    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  13 |    See the License for the specific language governing permissions and
  14 |    limitations under the License.
  15 | */
     ...
  17 | package cmdtrace
     ...
  19 | import (
  20 | 	"reflect"
  21 | 	"testing"
     ...
  23 | 	"github.com/spf13/cobra"
  24 | 	flag "github.com/spf13/pflag"
     ...
  26 | 	commands "github.com/docker/compose/v5/cmd/compose"
  27 | )
     ...
  29 | func TestGetFlags(t *testing.T) {
  30 | 	// Initialize flagSet with flags
  31 | 	fs := flag.NewFlagSet("up", flag.ContinueOnError)
  32 | 	var (
  33 | 		detach  string
  34 | 		timeout string
  35 | 	)
  36 | 	fs.StringVar(&detach, "detach", "d", "")
  37 | 	fs.StringVar(&timeout, "timeout", "t", "")
  38 | 	_ = fs.Set("detach", "detach")
  39 | 	_ = fs.Set("timeout", "timeout")
     ...
  41 | 	tests := []struct {
  42 | 		name     string
  43 | 		input    *flag.FlagSet
  44 | 		expected []string
  45 | 	}{
  46 | 		{
  47 | 			name:     "NoFlags",
  48 | 			input:    flag.NewFlagSet("NoFlags", flag.ContinueOnError),
  49 | 			expected: nil,
  50 | 		},
  51 | 		{
  52 | 			name:     "Flags",
  53 | 			input:    fs,
  54 | 			expected: []string{"detach", "timeout"},
  55 | 		},
  56 | 	}
     ...
  58 | 	for _, test := range tests {
  59 | 		t.Run(test.name, func(t *testing.T) {
  60 | 			result := getFlags(test.input)
  61 | 			if !reflect.DeepEqual(result, test.expected) {
  62 | 				t.Errorf("Expected %v, but got %v", test.expected, result)
  63 | 			}
  64 | 		})
  65 | 	}
  66 | }
     ...
  68 | func TestCommandName(t *testing.T) {
  69 | 	tests := []struct {
  70 | 		name     string
  71 | 		setupCmd func() *cobra.Command
  72 | 		want     []string
  73 | 	}{
  74 | 		{
  75 | 			name: "docker compose alpha watch -> [watch, alpha]",
  76 | 			setupCmd: func() *cobra.Command {
  77 | 				dockerCmd := &cobra.Command{Use: "docker"}
  78 | 				composeCmd := &cobra.Command{Use: commands.PluginName}
  79 | 				alphaCmd := &cobra.Command{Use: "alpha"}
  80 | 				watchCmd := &cobra.Command{Use: "watch"}
     ...
  82 | 				dockerCmd.AddCommand(composeCmd)
  83 | 				composeCmd.AddCommand(alphaCmd)
  84 | 				alphaCmd.AddCommand(watchCmd)
     ...
  86 | 				return watchCmd
  87 | 			},
  88 | 			want: []string{"watch", "alpha"},
  89 | 		},
  90 | 		{
  91 | 			name: "docker-compose up -> [up]",
  92 | 			setupCmd: func() *cobra.Command {
  93 | 				dockerComposeCmd := &cobra.Command{Use: commands.PluginName}
  94 | 				upCmd := &cobra.Command{Use: "up"}
     ...
  96 | 				dockerComposeCmd.AddCommand(upCmd)
     ...
  98 | 				return upCmd
  99 | 			},
 100 | 			want: []string{"up"},
 101 | 		},
 102 | 	}
     ...
 104 | 	for _, tt := range tests {
 105 | 		t.Run(tt.name, func(t *testing.T) {
 106 | 			cmd := tt.setupCmd()
 107 | 			got := commandName(cmd)
 108 | 			if !reflect.DeepEqual(got, tt.want) {
 109 | 				t.Errorf("commandName() = %v, want %v", got, tt.want)
 110 | 			}
 111 | 		})
 112 | 	}
 113 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r4-completioninsert-gained-completion-22daf7/repro.json
```

## Evidence and reduction

- representative c60222266301-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 2/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects docker/compose@c6dffb26bdfd, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- none found
- queries: `completionInsert unexpected repo:golang/go is:issue label:gopls`; `completionInsert "wrong edit" repo:golang/go is:issue label:gopls`
