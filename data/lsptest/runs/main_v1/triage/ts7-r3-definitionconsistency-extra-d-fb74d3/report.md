# [ts7 7.0.2] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-definitionconsistency-extra-d-fb74d3`, signature `ts7|r3_routes|definitionConsistency:extra`, case family `d`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `ChatGPTNextWeb/NextChat@defdcdb55d85` (corpus, commit defdcdb55d850cd12c4c657eb83729fd66e215c0), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `app/components/mask.tsx` at line 608, column 25 (LSP position {line: 607, character: 24}) gives the expected set; didOpen `app/masks/cn.ts` and `textDocument/definition` at the reference line 124, column 8 (LSP position {line: 123, character: 7}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "app/store/mask.ts",
  18,
  2,
  18,
  9
 ]
]
```

Actual:

```json
[
 [
  "app/masks/typing.ts",
  4,
  2,
  4,
  9
 ],
 [
  "app/store/mask.ts",
  18,
  2,
  18,
  9
 ]
]
```

Project file `app/masks/cn.ts`:

```
 121 |       compressMessageLengthThreshold: 1000,
 122 |     },
 123 |     lang: "cn",
 124 |     builtin: true,
 125 |     createdAt: 1688899480513,
 126 |   },
 127 |   {
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r3-definitionconsistency-extra-d-fb74d3/repro.json
```

## Evidence and reduction

- representative 0599b23297c7-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, vercel/hyper@30ec0a2a91de, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4908](https://github.com/microsoft/typescript-go/issues/4908) Go-to-definition does not work at the right edge of a JSX tag name (closed, 2026-08-17, 0 comments)
- [microsoft/typescript-go#1885](https://github.com/microsoft/typescript-go/issues/1885) go to definition panic (windows, wsl) (closed, 2025-10-15, 4 comments)
- [microsoft/typescript-go#2209](https://github.com/microsoft/typescript-go/issues/2209) [lsp] Go to Definition missing getter when property returns callable interface (closed, 2025-12-04, 0 comments)
- [microsoft/typescript-go#2839](https://github.com/microsoft/typescript-go/issues/2839) Cannot "go to definition" of a playwright fixture (closed, 2026-02-19, 1 comments)
- [microsoft/typescript-go#2847](https://github.com/microsoft/typescript-go/issues/2847) panic on go-to-type-definition of tuple type (closed, 2026-02-20, 0 comments)
- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4000](https://github.com/microsoft/typescript-go/issues/4000) Make typedef exporting explicit (closed, 2026-05-20, 7 comments)
- [microsoft/typescript-go#4037](https://github.com/microsoft/typescript-go/issues/4037) TS2304 when a generic (@template) function JSDoc contains @overload (closed, 2026-05-23, 5 comments)
- queries: `"go to definition" in:title repo:microsoft/typescript-go is:issue`; `definition extra repo:microsoft/typescript-go is:issue`; `definition "go to definition" repo:microsoft/typescript-go is:issue`; `definition inconsistent repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trfb74d3-r3-replay-baseline-20260925-154918-a80af9] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trfb74d3-r3-replay-baseline-20260925-154918-a80af9] stderr: context canceled
[ts7-7.0.2-trfb74d3-r3-replay-control-20260925-154937-466850] stderr: context canceled
```
