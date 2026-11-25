# [gopls v0.23.0] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `gopls-r3-definitionconsistency-result-error-0-d-f91fb9`, signature `gopls|r3_routes|definitionConsistency:result->error:0`, case family `d`.

## Server

- gopls v0.23.0; launch `temp/lsp_servers/gopls-v0.23.0/gopls serve`; entry sha256 a8b4a156c328a03f; package version -
- project `SagerNet/sing-box@0d91c4547921` (corpus, commit 0d91c4547921a7b72e9c9913e2bc6f3a556801e2), language go

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start gopls v0.23.0 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `protocol/bridge/linkname_darwin.go` at line 8, column 48 (LSP position {line: 7, character: 47}) gives the expected set; didOpen `protocol/bridge/linkname_darwin.go` and `textDocument/definition` at the reference line 4, column 6 (LSP position {line: 3, character: 5}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "protocol/bridge/linkname_darwin.go",
  3,
  1,
  3,
  9
 ]
]
```

Actual:

```json
[
 "error",
 0
]
```

Project file `protocol/bridge/linkname_darwin.go`:

```
   1 | package bridge
     ...
   3 | import (
   4 | 	"unsafe"
   5 | )
     ...
   7 | //go:linkname unixIoctlPtr golang.org/x/sys/unix.ioctlPtr
   8 | func unixIoctlPtr(fd int, request uint, arg unsafe.Pointer) error
     ...
  10 | //go:linkname unixSysctl golang.org/x/sys/unix.sysctl
  11 | func unixSysctl(mib []int32, old *byte, oldLen *uintptr, newValue *byte, newLen uintptr) error
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/gopls-r3-definitionconsistency-result-error-0-d-f91fb9/repro.json
```

## Evidence and reduction

- representative 74c1574f1393-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects SagerNet/sing-box@0d91c4547921, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [golang/go#66827](https://github.com/golang/go/issues/66827) x/tools/gopls: go to definition within imported modules (open, 2024-04-14, 7 comments)
- [golang/go#40584](https://github.com/golang/go/issues/40584) x/tools/gopls: go to the definition of the only non-test interface implementation (open, 2020-08-05, 2 comments)
- [golang/go#73545](https://github.com/golang/go/issues/73545) x/tools/gopls: go to definition should go to replaced version of module (closed, 2025-04-30, 9 comments)
- [golang/go#70462](https://github.com/golang/go/issues/70462) x/tools/gopls: jump to definition on 'return' should go to the result parameter list (closed, 2024-11-20, 10 comments)
- [golang/go#77131](https://github.com/golang/go/issues/77131) x/tools/gopls: Definition: go:embed directive does not resolve to file location on Windows (closed, 2026-01-08, 12 comments)
- [golang/go#82269](https://github.com/golang/go/issues/82269) x/tools/gopls: add inspect subcommand for gopls cli (open, 2026-10-16, 5 comments)
- [golang/go#83067](https://github.com/golang/go/issues/83067) go/types: Checker.Files panics (in validType) on recursive type (open, 2026-11-14, 7 comments)
- [golang/go#78620](https://github.com/golang/go/issues/78620) x/tools/gopls: frob.Decode panics with "surplus bytes" error (open, 2026-04-10, 9 comments)
- queries: `"go to definition" in:title repo:golang/go is:issue label:gopls`; `definition error repo:golang/go is:issue label:gopls`; `definition "go to definition" repo:golang/go is:issue label:gopls`; `definition inconsistent repo:golang/go is:issue label:gopls`

## Server log excerpt (last confirming replay)

```
[gopls-v0.23.0-trf91fb9-r3-replay-baseline-20261119-000012-a77371] textDocument/definition -> error 0: package "unsafe" has no readable files
[gopls-v0.23.0-trf91fb9-r3-replay-control-20261119-000023-cb5436] textDocument/definition -> error 0: package "unsafe" has no readable files
```
