# [gopls v0.23.0] references adds entries after edit inside a workspace window

Draft for the author (not filed). Group `gopls-r1-references-extra-h9-0290a7`, signature `gopls|r1_history|references:extra`, case family `H9`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `charmbracelet/bubbletea@657aaae216e3` (corpus, commit 657aaae216e3f87df09b60959a9fe5de7b2ca419), language go

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/http/main.go (then 200 ms)`
3. textDocument/didOpen: `open examples/set-window-title/main.go (then 200 ms)`
4. textDocument/didOpen: `open termios_unix.go (then 200 ms)`
5. textDocument/didChange: `change termios_unix.go (8, 1)-(8, 1) "(" (then 200 ms)`
6. textDocument/didClose: `close examples/set-window-title/main.go (then 200 ms)`
7. textDocument/didOpen: `open examples/set-window-title/main.go (then 200 ms)`
8. textDocument/didClose: `close termios_unix.go (then 200 ms)`
9. Timing: send the steps 200 ms apart without waiting, then wait until idle.
10. textDocument/didOpen `mouse.go` (the query step opens every target file that is not open), then wait until the server is idle.
11. Query `textDocument/references` on `examples/http/main.go` line 38, column 43 (LSP position {line: 37, character: 42}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "examples/altscreen-toggle/main.go",
  25,
  40,
  25,
  45
 ],
 [
  "examples/autocomplete/main.go",
  129,
  40,
  129,
  45
 ],
 [
  "examples/canvas/main.go",
  21,
  40,
  21,
  45
 ],
 [
  "examples/capability/main.go",
  16,
  10,
  16,
  15
 ],
 [
  "examples/capability/main.go",
  24,
  40,
  24,
  45
 ],
 [
  "examples/cellbuffer/main.go",
  148,
  40,
  148,
  45
 ],
 [
  "examples/chat/main.go",
  72,
  40,
  72,
  45
 ],
 [
  "examples/clickable/main.go",
  77,
  40,
  77,
  45
 ],
 [
  "examples/colorprofile/main.go",
  16,
  10,
  16,
  15
 ],
 [
  "examples/colorprofile/main.go",
  27,
  40,
  27,
  45
 ],
 [
  "examples/composable-views/main.go",
  80,
  44,
  80,
  49
 ],
 [
  "examples/cursor-style/main.go",
  18,
  40,
  18,
  45
 ],
 [
  "examples/debounce/main.go",
  32,
  40,
  32,
  45
 ],
 [
  "examples/doom-fire/main.go",
  29,
  40,
  29,
  45
 ],
 [
  "examples/dynamic-textarea/main.go",
  41,
  40,
  41,
  45
 ],
 [
  "examples/exec/main.go",
  30,
  40,
  30,
  45
 ],
 [
  "examples/eyes/main.go",
  84,
  40,
  84,
  45
 ],
 [
  "examples/file-picker/main.go",
  32,
  40,
  32,
  45
 ],
 [
  "examples/focus-blur/main.go",
  29,
  40,
  29,
  45
 ],
 [
  "examples/fullscreen/main.go",
  28,
  44,
  28,
  49
 ],
 [
  "examples/glamour/main.go",
  111,
  42,
  111,
  47
 ],
 [
  "examples/help/main.go",
  86,
  40,
  86,
  45
 ],
 [
  "examples/http/main.go",
  37,
  40,
  37,
  45
 ],
 [
  "examples/isbn-form/main.go",
  158,
  40,
  158,
  
... (4841 characters)
```

Actual:

```json
[
 [
  "cursed_renderer_test.go",
  19,
  42,
  19,
  47
 ],
 [
  "examples/altscreen-toggle/main.go",
  25,
  40,
  25,
  45
 ],
 [
  "examples/autocomplete/main.go",
  129,
  40,
  129,
  45
 ],
 [
  "examples/canvas/main.go",
  21,
  40,
  21,
  45
 ],
 [
  "examples/capability/main.go",
  16,
  10,
  16,
  15
 ],
 [
  "examples/capability/main.go",
  24,
  40,
  24,
  45
 ],
 [
  "examples/cellbuffer/main.go",
  148,
  40,
  148,
  45
 ],
 [
  "examples/chat/main.go",
  72,
  40,
  72,
  45
 ],
 [
  "examples/clickable/main.go",
  77,
  40,
  77,
  45
 ],
 [
  "examples/colorprofile/main.go",
  16,
  10,
  16,
  15
 ],
 [
  "examples/colorprofile/main.go",
  27,
  40,
  27,
  45
 ],
 [
  "examples/composable-views/main.go",
  80,
  44,
  80,
  49
 ],
 [
  "examples/cursor-style/main.go",
  18,
  40,
  18,
  45
 ],
 [
  "examples/debounce/main.go",
  32,
  40,
  32,
  45
 ],
 [
  "examples/doom-fire/main.go",
  29,
  40,
  29,
  45
 ],
 [
  "examples/dynamic-textarea/main.go",
  41,
  40,
  41,
  45
 ],
 [
  "examples/exec/main.go",
  30,
  40,
  30,
  45
 ],
 [
  "examples/eyes/main.go",
  84,
  40,
  84,
  45
 ],
 [
  "examples/file-picker/main.go",
  32,
  40,
  32,
  45
 ],
 [
  "examples/focus-blur/main.go",
  29,
  40,
  29,
  45
 ],
 [
  "examples/fullscreen/main.go",
  28,
  44,
  28,
  49
 ],
 [
  "examples/glamour/main.go",
  111,
  42,
  111,
  47
 ],
 [
  "examples/help/main.go",
  86,
  40,
  86,
  45
 ],
 [
  "examples/http/main.go",
  37,
  40,
  37,
  45
 ]
... (5194 characters)
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
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r1-references-extra-h9-0290a7/repro.json
```

## Evidence and reduction

- representative 12cd746378bc-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 18 -> 7 (32 probes, 140.343 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects charmbracelet/bubbletea@657aaae216e3, timings race0, race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#81408](https://github.com/golang/go/issues/81408) x/tools/gopls: issues many redundant `go list` invocations concurrently (open, 2026-09-09, 5 comments)
- [golang/go#50151](https://github.com/golang/go/issues/50151) x/tools/gopls: high cpu usage when make changes in package which have some cgo package dependents (open, 2021-12-14, 15 comments)
- [golang/go#38028](https://github.com/golang/go/issues/38028) x/tools/gopls: support change signature refactoring (open, 2020-03-23, 9 comments)
- [golang/go#64936](https://github.com/golang/go/issues/64936) x/tools/gopls: support for comment rendering (open, 2024-01-02, 9 comments)
- [golang/go#68087](https://github.com/golang/go/issues/68087) x/tools/gopls: `go clean` fails with ENOTEMPTY (openbsd) causing gopls test flakes (open, 2024-06-20, 190 comments)
- [golang/go#40862](https://github.com/golang/go/issues/40862) x/tools/gopls: add codelens to show number of references to each symbol (open, 2020-08-16, 41 comments)
- [golang/go#68002](https://github.com/golang/go/issues/68002) x/tools/gopls: improvements to loading behavior (open, 2024-06-14, 5 comments)
- [golang/go#81400](https://github.com/golang/go/issues/81400) x/tools/gopls: after a workspace load error is fixed, every later go.mod change makes requests fail with "no package metadata" for about a second (closed, 2026-09-09, 5 comments)
- queries: `references extra repo:golang/go is:issue label:gopls`; `references stale repo:golang/go is:issue label:gopls`
