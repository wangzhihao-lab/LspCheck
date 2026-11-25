# [gopls v0.23.0] mutation:M2 edit is not valid (diagnostics:extra:NotAType)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-notatype-mutation-m2-477181`, signature `gopls|r4_edits|diagnostics:extra:NotAType`, case family `mutation:M2`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `charmbracelet/bubbletea@657aaae216e3` (corpus, commit 657aaae216e3f87df09b60959a9fe5de7b2ca419), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/list-default/main.go`
3. textDocument/didChange: `change examples/list-default/main.go (78, 6)-(78, 11) "moddel"`
4. textDocument/didChange: `change examples/list-default/main.go (78, 2)-(78, 2) "oddel := 0\n\tm"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `examples/list-fancy/main.go`, `examples/splash/main.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `examples/list-default/main.go` line 79, column 7 (LSP position {line: 78, character: 6}) (M2:quickfix-errors:Create variable moddel); compare with the same query in a fresh session on the same content (expected).

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
  "NotAType",
  "compiler",
  "moddel (local variable) is not a type"
 ]
]
```

Project file `examples/list-default/main.go`:

```
   1 | package main
     ...
   3 | import (
   4 | 	"fmt"
   5 | 	"os"
     ...
   7 | 	"charm.land/bubbles/v2/list"
   8 | 	tea "charm.land/bubbletea/v2"
   9 | 	"charm.land/lipgloss/v2"
  10 | )
     ...
  12 | var docStyle = lipgloss.NewStyle().Margin(1, 2)
     ...
  14 | type item struct {
  15 | 	title, desc string
  16 | }
     ...
  18 | func (i item) Title() string       { return i.title }
  19 | func (i item) Description() string { return i.desc }
  20 | func (i item) FilterValue() string { return i.title }
     ...
  22 | type model struct {
  23 | 	list list.Model
  24 | }
     ...
  26 | func (m model) Init() tea.Cmd {
  27 | 	return nil
  28 | }
     ...
  30 | func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
  31 | 	switch msg := msg.(type) {
  32 | 	case tea.KeyPressMsg:
  33 | 		if msg.String() == "ctrl+c" {
  34 | 			return m, tea.Quit
  35 | 		}
  36 | 	case tea.WindowSizeMsg:
  37 | 		h, v := docStyle.GetFrameSize()
  38 | 		m.list.SetSize(msg.Width-h, msg.Height-v)
  39 | 	}
     ...
  41 | 	var cmd tea.Cmd
  42 | 	m.list, cmd = m.list.Update(msg)
  43 | 	return m, cmd
  44 | }
     ...
  46 | func (m model) View() tea.View {
  47 | 	v := tea.NewView(docStyle.Render(m.list.View()))
  48 | 	v.AltScreen = true
  49 | 	return v
  50 | }
     ...
  52 | func main() {
  53 | 	items := []list.Item{
  54 | 		item{title: "Raspberry Pi’s", desc: "I have ’em all over my house"},
  55 | 		item{title: "Nutella", desc: "It's good on toast"},
  56 | 		item{title: "Bitter melon", desc: "It cools you down"},
  57 | 		item{title: "Nice socks", desc: "And by that I mean socks without holes"},
  58 | 		item{title: "Eight hours of sleep", desc: "I had this once"},
  59 | 		item{title: "Cats", desc: "Usually"},
  60 | 		item{title: "Plantasia, the album", desc: "My plants love it too"},
  61 | 		item{title: "Pour over coffee", desc: "It takes forever to make though"},
  62 | 		item{title: "VR", desc: "Virtual reality...what is there to say?"},
  63 | 		item{title: "Noguchi Lamps", desc: "Such pleasing organic forms"},
  64 | 		item{title: "Linux", desc: "Pretty much the best OS"},
  65 | 		item{title: "Business school", desc: "Just kidding"},
  66 | 		item{title: "Pottery", desc: "Wet clay is a great feeling"},
  67 | 		item{title: "Shampoo", desc: "Nothing like clean hair"},
  68 | 		item{title: "Table tennis", desc: "It’s surprisingly exhausting"},
  69 | 		item{title: "Milk crates", desc: "Great for packing in your extra stuff"},
  70 | 		item{title: "Afternoon tea", desc: "Especially the tea sandwich part"},
  71 | 		item{title: "Stickers", desc: "The thicker the vinyl the better"},
  72 | 		item{title: "20° Weather", desc: "Celsius, not Fahrenheit"},
  73 | 		item{title: "Warm light", desc: "Like around 2700 Kelvin"},
  74 | 		item{title: "The vernal equinox", desc: "The autumnal equinox is pretty good too"},
  75 | 		item{title: "Gaffer’s tape", desc: "Basically sticky fabric"},
  76 | 		item{title: "Terrycloth", desc: "In other words, towel fabric"},
  77 | 	}
     ...
  79 | 	m := model{list: list.New(items, list.NewDefaultDelegate(), 0, 0)}
  80 | 	m.list.Title = "My Fave Things"
     ...
  82 | 	p := tea.NewProgram(m)
     ...
  84 | 	if _, err := p.Run(); err != nil {
  85 | 		fmt.Println("Error running program:", err)
  86 | 		os.Exit(1)
  87 | 	}
  88 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r4-diagnostics-extra-notatype-mutation-m2-477181/repro.json
```

## Evidence and reduction

- representative 73fef80b14e5-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 3.578 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects charmbracelet/bubbletea@657aaae216e3, fatedier/frp@d20a23299600, timings settled, seeds 1, 2

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
