# [ts7 7.0.2] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-definitionconsistency-lost-d-0129b3`, signature `ts7|r3_routes|definitionConsistency:lost`, case family `d`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `vadimdemedes/ink@02ae1e59e7c2` (corpus, commit 02ae1e59e7c288e971616100c4c11bcca6b5761b), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `test/helpers/create-stdout.ts` at line 8, column 8 (LSP position {line: 7, character: 7}) gives the expected set; didOpen `src/ink.tsx` and `textDocument/definition` at the reference line 147, column 12 (LSP position {line: 146, character: 11}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "node_modules/@types/node/buffer.d.ts",
  87,
  18,
  87,
  24
 ],
 [
  "node_modules/@types/node/compatibility/iterators.d.ts",
  11,
  18,
  11,
  24
 ],
 [
  "node_modules/@types/node/events.d.ts",
  57,
  18,
  57,
  24
 ],
 [
  "node_modules/@types/node/globals.d.ts",
  74,
  18,
  74,
  24
 ],
 [
  "node_modules/@types/node/globals.typedarray.d.ts",
  3,
  14,
  3,
  20
 ],
 [
  "node_modules/@types/node/module.d.ts",
  574,
  18,
  574,
  24
 ],
 [
  "node_modules/@types/node/process.d.ts",
  142,
  18,
  142,
  24
 ],
 [
  "node_modules/@types/node/stream.d.ts",
  1737,
  18,
  1737,
  24
 ],
 [
  "node_modules/@types/node/timers.d.ts",
  12,
  18,
  12,
  24
 ]
]
```

Actual:

```json
[]
```

Project file `src/ink.tsx`:

```
 145 | export type Options = {
 146 | 	stdout: OutputStream;
 147 | 	stdin: NodeJS.ReadableStream;
 148 | 	stderr: OutputStream;
 149 | 	debug: boolean;
 150 | 	exitOnCtrlC: boolean;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r3-definitionconsistency-lost-d-0129b3/repro.json
```

## Evidence and reduction

- representative b5bcb0e49763-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4908](https://github.com/microsoft/typescript-go/issues/4908) Go-to-definition does not work at the right edge of a JSX tag name (closed, 2026-08-17, 0 comments)
- [microsoft/typescript-go#1885](https://github.com/microsoft/typescript-go/issues/1885) go to definition panic (windows, wsl) (closed, 2025-10-15, 4 comments)
- [microsoft/typescript-go#2209](https://github.com/microsoft/typescript-go/issues/2209) [lsp] Go to Definition missing getter when property returns callable interface (closed, 2025-12-04, 0 comments)
- [microsoft/typescript-go#2839](https://github.com/microsoft/typescript-go/issues/2839) Cannot "go to definition" of a playwright fixture (closed, 2026-02-19, 1 comments)
- [microsoft/typescript-go#2847](https://github.com/microsoft/typescript-go/issues/2847) panic on go-to-type-definition of tuple type (closed, 2026-02-20, 0 comments)
- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#3580](https://github.com/microsoft/typescript-go/issues/3580) No code actions available when attempting to use refactorings in VS Code with new typescript-go preview (closed, 2026-04-24, 2 comments)
- [microsoft/typescript-go#2666](https://github.com/microsoft/typescript-go/issues/2666) `tsgo --build` fails to invalidate incremental cache after dependency update (closed, 2026-02-04, 3 comments)
- queries: `"go to definition" in:title repo:microsoft/typescript-go is:issue`; `definition missing repo:microsoft/typescript-go is:issue`; `definition "go to definition" repo:microsoft/typescript-go is:issue`; `definition inconsistent repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr0129b3-r3-replay-baseline-20261118-214911-7b2242] stderr: context canceled
[ts7-7.0.2-tr0129b3-r3-replay-control-20261118-214921-fe3864] stderr: context canceled
```
