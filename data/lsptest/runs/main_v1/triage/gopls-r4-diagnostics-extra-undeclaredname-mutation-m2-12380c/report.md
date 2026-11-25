# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:UndeclaredName)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c`, signature `gopls|r4_edits|diagnostics:extra:UndeclaredName`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `charmbracelet/bubbletea@657aaae216e3` (corpus, commit 657aaae216e3f87df09b60959a9fe5de7b2ca419), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/http/main.go`
3. textDocument/didChange: `change examples/http/main.go (33, 8)-(33, 13) "moddel"`
4. textDocument/didChange: `change examples/http/main.go (20, 0)-(20, 0) "// Init implements [tea.Model].\nfunc (m model) Init() tea.Cmd {\n\tpanic(\"unimplemented\")\n}\n\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `examples/set-window-title/main.go`, `mouse.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `examples/http/main.go` line 28, column 22 (LSP position {line: 27, character: 21}) (M2:quickfix-errors:Declare missing methods of tea.Model); compare with the same query in a fresh session on the same content (expected).

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
  "UndeclaredName",
  "compiler",
  "undefined: moddel"
 ]
]
```

Project file `examples/http/main.go`:

```
   1 | package main
     ...
   3 | // A simple program that makes a GET request and prints the response status.
     ...
   5 | import (
   6 | 	"fmt"
   7 | 	"log"
   8 | 	"net/http"
   9 | 	"time"
     ...
  11 | 	tea "charm.land/bubbletea/v2"
  12 | )
     ...
  14 | const url = "https://charm.sh/"
     ...
  16 | type model struct {
  17 | 	status int
  18 | 	err    error
  19 | }
     ...
  21 | type statusMsg int
     ...
  23 | type errMsg struct{ error }
     ...
  25 | func (e errMsg) Error() string { return e.error.Error() }
     ...
  27 | func main() {
  28 | 	p := tea.NewProgram(model{})
  29 | 	if _, err := p.Run(); err != nil {
  30 | 		log.Fatal(err)
  31 | 	}
  32 | }
     ...
  34 | func (m model) Init() tea.Cmd {
  35 | 	return checkServer
  36 | }
     ...
  38 | func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
  39 | 	switch msg := msg.(type) {
  40 | 	case tea.KeyPressMsg:
  41 | 		switch msg.String() {
  42 | 		case "q", "ctrl+c", "esc":
  43 | 			return m, tea.Quit
  44 | 		default:
  45 | 			return m, nil
  46 | 		}
     ...
  48 | 	case statusMsg:
  49 | 		m.status = int(msg)
  50 | 		return m, tea.Quit
     ...
  52 | 	case errMsg:
  53 | 		m.err = msg
  54 | 		return m, nil
     ...
  56 | 	default:
  57 | 		return m, nil
  58 | 	}
  59 | }
     ...
  61 | func (m model) View() tea.View {
  62 | 	s := fmt.Sprintf("Checking %s...", url)
  63 | 	if m.err != nil {
  64 | 		s += fmt.Sprintf("something went wrong: %s", m.err)
  65 | 	} else if m.status != 0 {
  66 | 		s += fmt.Sprintf("%d %s", m.status, http.StatusText(m.status))
  67 | 	}
  68 | 	return tea.NewView(s + "\n")
  69 | }
     ...
  71 | func checkServer() tea.Msg {
  72 | 	c := &http.Client{
  73 | 		Timeout: 10 * time.Second,
  74 | 	}
  75 | 	res, err := c.Get(url)
  76 | 	if err != nil {
  77 | 		return errMsg{err}
  78 | 	}
  79 | 	defer res.Body.Close() // nolint:errcheck
     ...
  81 | 	return statusMsg(res.StatusCode)
  82 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r4-diagnostics-extra-undeclaredname-mutation-m2-12380c/repro.json
```

## Evidence and reduction

- representative 4e55ff9e6249-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 3.893 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects charmbracelet/bubbletea@657aaae216e3, jesseduffield/lazydocker@7e7aadc2071d, timings settled, seeds 1

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
