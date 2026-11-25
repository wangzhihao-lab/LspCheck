# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:UntypedNilUse)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70`, signature `gopls|r4_edits|diagnostics:extra:UntypedNilUse`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `spf13/cobra@adbc8813901b` (corpus, commit adbc8813901bba65827259daa8e22ff94ec1f30e), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open command_win.go`
3. textDocument/didChange: `change command_win.go (31, 10)-(31, 27) "MousetrappHelpText"`
4. textDocument/didChange: `change command_win.go (31, 2)-(31, 2) "MousetrappHelpText := nil\n\t\t"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `doc/rest_docs.go`, `powershell_completions_test.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `command_win.go` line 32, column 11 (LSP position {line: 31, character: 10}) (M2:quickfix-errors:Create variable MousetrappHelpText); compare with the same query in a fresh session on the same content (expected).

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
  "UntypedNilUse",
  "compiler",
  "use of untyped nil in assignment [windows,amd64]"
 ]
]
```

Project file `command_win.go`:

```
   1 | // Copyright 2013-2023 The Cobra Authors
   2 | //
   3 | // Licensed under the Apache License, Version 2.0 (the "License");
   4 | // you may not use this file except in compliance with the License.
   5 | // You may obtain a copy of the License at
   6 | //
   7 | //      http://www.apache.org/licenses/LICENSE-2.0
   8 | //
   9 | // Unless required by applicable law or agreed to in writing, software
  10 | // distributed under the License is distributed on an "AS IS" BASIS,
  11 | // WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  12 | // See the License for the specific language governing permissions and
  13 | // limitations under the License.
     ...
  15 | //go:build windows
  16 | // +build windows
     ...
  18 | package cobra
     ...
  20 | import (
  21 | 	"fmt"
  22 | 	"os"
  23 | 	"time"
     ...
  25 | 	"github.com/inconshreveable/mousetrap"
  26 | )
     ...
  28 | var preExecHookFn = preExecHook
     ...
  30 | func preExecHook(c *Command) {
  31 | 	if MousetrapHelpText != "" && mousetrap.StartedByExplorer() {
  32 | 		c.Print(MousetrapHelpText)
  33 | 		if MousetrapDisplayDuration > 0 {
  34 | 			time.Sleep(MousetrapDisplayDuration)
  35 | 		} else {
  36 | 			c.Println("Press return to continue...")
  37 | 			fmt.Scanln()
  38 | 		}
  39 | 		os.Exit(1)
  40 | 	}
  41 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r4-diagnostics-extra-untypedniluse-mutation-m2-354f70/repro.json
```

## Evidence and reduction

- representative 9be4e39bca38-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.134 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects router-for-me/CLIProxyAPI@673131f57484, spf13/cobra@adbc8813901b, timings settled, seeds 2

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
