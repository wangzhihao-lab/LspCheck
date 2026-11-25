# [gopls v0.23.0] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `gopls-r3-definitionconsistency-changed-d-cf67f4`, signature `gopls|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `gin-gonic/gin@3b08cd7235bd` (corpus, commit 3b08cd7235bd5ad2f055aa9e38135f111f6c5926), language go

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `binding/toml_test.go` at line 5, column 12 (LSP position {line: 4, character: 11}) gives the expected set; didOpen `binding/binding_test.go` and `textDocument/definition` at the reference line 5, column 12 (LSP position {line: 4, character: 11}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "binding/toml_test.go",
  4,
  8,
  4,
  15
 ]
]
```

Actual:

```json
[
 [
  "binding/binding_test.go",
  4,
  8,
  4,
  15
 ]
]
```

Project file `binding/binding_test.go`:

```
   2 | // Use of this source code is governed by a MIT style
   3 | // license that can be found in the LICENSE file.
     ...
   5 | package binding
     ...
   7 | import (
   8 | 	"bytes"
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/gopls-r3-definitionconsistency-changed-d-cf67f4/repro.json
```

## Evidence and reduction

- representative 5915462982a7-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects caddyserver/caddy@c18099a0af5e, gin-gonic/gin@3b08cd7235bd, jesseduffield/lazydocker@7e7aadc2071d, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#66827](https://github.com/golang/go/issues/66827) x/tools/gopls: go to definition within imported modules (open, 2024-04-14, 7 comments)
- [golang/go#40584](https://github.com/golang/go/issues/40584) x/tools/gopls: go to the definition of the only non-test interface implementation (open, 2020-08-05, 2 comments)
- [golang/go#73545](https://github.com/golang/go/issues/73545) x/tools/gopls: go to definition should go to replaced version of module (closed, 2025-04-30, 9 comments)
- [golang/go#70462](https://github.com/golang/go/issues/70462) x/tools/gopls: jump to definition on 'return' should go to the result parameter list (closed, 2024-11-20, 10 comments)
- [golang/go#77131](https://github.com/golang/go/issues/77131) x/tools/gopls: Definition: go:embed directive does not resolve to file location on Windows (closed, 2026-01-08, 12 comments)
- [golang/go#35520](https://github.com/golang/go/issues/35520) x/tools/gopls: improve error message when using wrong go command with Go source distribution (open, 2019-11-12, 16 comments)
- [golang/go#50991](https://github.com/golang/go/issues/50991) x/tools/gopls: -remote=auto doesn't use different addresses for different Go versions (open, 2022-02-03, 7 comments)
- [golang/go#75271](https://github.com/golang/go/issues/75271) x/tools/gopls: InlayHint(constantValues): don't exclude booleans (open, 2025-09-04, 2 comments)
- queries: `"go to definition" in:title repo:golang/go is:issue label:gopls`; `definition wrong repo:golang/go is:issue label:gopls`; `definition "go to definition" repo:golang/go is:issue label:gopls`; `definition inconsistent repo:golang/go is:issue label:gopls`
