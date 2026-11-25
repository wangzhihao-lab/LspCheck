# [gopls v0.23.0] mutation:M3 edit is not valid (diagnostics:extra:WrongArgCount)

Draft for the author (not filed). Group `gopls-r4-diagnostics-extra-wrongargcount-mutation-m3-ac10cc`, signature `gopls|r4_edits|diagnostics:extra:WrongArgCount`, case family `mutation:M3`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `jesseduffield/lazydocker@7e7aadc2071d` (corpus, commit 7e7aadc2071d58031bf2daafca1fbd4093efc23f), language go

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open pkg/gui/focus.go`
3. textDocument/didChange: `change pkg/gui/focus.go (82, 27)-(82, 39) ""`
4. textDocument/didChange: `change pkg/gui/focus.go (77, 1)-(77, 13) "_"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `pkg/gui/menu_panel.go`, `pkg/log/log.go` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `pkg/gui/focus.go` line 78, column 2 (LSP position {line: 77, character: 1}) (M3:quickfix-errors:Remove variable previousView); compare with the same query in a fresh session on the same content (expected).

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
  "not enough arguments in call to gui.switchFocusAux have () want (*gocui.View)"
 ]
]
```

Project file `pkg/gui/focus.go`:

```
   1 | package gui
     ...
   3 | import (
   4 | 	"github.com/jesseduffield/gocui"
   5 | 	"github.com/samber/lo"
   6 | )
     ...
   8 | func (gui *Gui) newLineFocused(v *gocui.View) error {
   9 | 	if v == nil {
  10 | 		return nil
  11 | 	}
     ...
  13 | 	currentListPanel, ok := gui.currentListPanel()
  14 | 	if ok {
  15 | 		return currentListPanel.HandleSelect()
  16 | 	}
     ...
  18 | 	switch v.Name() {
  19 | 	case "confirmation":
  20 | 		return nil
  21 | 	case "main":
  22 | 		v.Highlight = false
  23 | 		return nil
  24 | 	case "filter":
  25 | 		return nil
  26 | 	default:
  27 | 		panic(gui.Tr.NoViewMachingNewLineFocusedSwitchStatement)
  28 | 	}
  29 | }
     ...
  31 | // TODO: move some of this logic into our onFocusLost and onFocus hooks
  32 | func (gui *Gui) switchFocus(newView *gocui.View) error {
  33 | 	gui.Mutexes.ViewStackMutex.Lock()
  34 | 	defer gui.Mutexes.ViewStackMutex.Unlock()
     ...
  36 | 	return gui.switchFocusAux(newView)
  37 | }
     ...
  39 | func (gui *Gui) switchFocusAux(newView *gocui.View) error {
  40 | 	gui.pushView(newView.Name())
  41 | 	gui.Log.Info("setting highlight to true for view " + newView.Name())
  42 | 	gui.Log.Info("new focused view is " + newView.Name())
  43 | 	if _, err := gui.g.SetCurrentView(newView.Name()); err != nil {
  44 | 		return err
  45 | 	}
     ...
  47 | 	gui.g.Cursor = newView.Editable
     ...
  49 | 	if err := gui.renderPanelOptions(); err != nil {
  50 | 		return err
  51 | 	}
     ...
  53 | 	newViewStack := gui.State.ViewStack
     ...
  55 | 	if gui.State.Filter.panel != nil && !lo.Contains(newViewStack, gui.State.Filter.panel.GetView().Name()) {
  56 | 		if err := gui.clearFilter(); err != nil {
  57 | 			return err
  58 | 		}
  59 | 	}
     ...
  61 | 	// TODO: add 'onFocusLost' hook
  62 | 	if !lo.Contains(newViewStack, "menu") {
  63 | 		gui.Views.Menu.Visible = false
  64 | 	}
     ...
  66 | 	return gui.newLineFocused(newView)
  67 | }
     ...
  69 | func (gui *Gui) returnFocus() error {
  70 | 	gui.Mutexes.ViewStackMutex.Lock()
  71 | 	defer gui.Mutexes.ViewStackMutex.Unlock()
     ...
  73 | 	if len(gui.State.ViewStack) <= 1 {
  74 | 		return nil
  75 | 	}
     ...
  77 | 	previousViewName := gui.State.ViewStack[len(gui.State.ViewStack)-2]
  78 | 	previousView, err := gui.g.View(previousViewName)
  79 | 	if err != nil {
  80 | 		return err
  81 | 	}
     ...
  83 | 	return gui.switchFocusAux(previousView)
  84 | }
     ...
  86 | func (gui *Gui) removeViewFromStack(view *gocui.View) {
  87 | 	gui.Mutexes.ViewStackMutex.Lock()
  88 | 	defer gui.Mutexes.ViewStackMutex.Unlock()
     ...
  90 | 	gui.State.ViewStack = lo.Filter(gui.State.ViewStack, func(viewName string, _ int) bool {
  91 | 		return viewName != view.Name()
  92 | 	})
  93 | }
     ...
  95 | // Not to be called directly. Use `switchFocus` instead
  96 | func (gui *Gui) pushView(name string) {
  97 | 	// No matter what view we're pushing, we first remove all popup panels from the stack
  98 | 	// (unless it's the search view because we may be searching the menu panel)
  99 | 	if name != "filter" {
 100 | 		gui.State.ViewStack = lo.Filter(gui.State.ViewStack, func(viewName string, _ int) bool {
 101 | 			return !gui.isPopupPanel(viewName)
 102 | 		})
 103 | 	}
     ...
 105 | 	// If we're pushing a side panel, we remove all other panels
 106 | 	if lo.Contains(gui.sideViewNames(), name) {
 107 | 		gui.State.ViewStack = []string{}
 108 | 	}
     ...
 110 | 	// If we're pushing a panel that's already in the stack, we remove it
 111 | 	gui.State.ViewStack = lo.Filter(gui.State.ViewStack, func(viewName string, _ int) bool {
 112 | 		return viewName != name
 113 | 	})
     ...
 115 | 	gui.State.ViewStack = append(gui.State.ViewStack, name)
 116 | }
     ...
 118 | // excludes popups
 119 | func (gui *Gui) currentStaticViewName() string {
 120 | 	gui.Mutexes.ViewStackMutex.Lock()
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r4-diagnostics-extra-wrongargcount-mutation-m3-ac10cc/repro.json
```

## Evidence and reduction

- representative 5668b20b0d8b-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 5.776 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects jesseduffield/lazydocker@7e7aadc2071d, timings settled, seeds 1

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
