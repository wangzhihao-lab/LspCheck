# [ts7 7.0.2] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-definitionconsistency-missing-d-560852`, signature `ts7|r3_routes|definitionConsistency:missing`, case family `d`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `upstash/context7@6477e43e31d2` (corpus, commit 6477e43e31d27a5c1bc044506e1c14de15f8a110), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `packages/sdk/src/http/index.ts` at line 152, column 38 (LSP position {line: 151, character: 37}) gives the expected set; didOpen `packages/sdk/src/http/index.ts` and `textDocument/definition` at the reference line 132, column 13 (LSP position {line: 131, character: 12}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "packages/sdk/src/http/index.ts",
  29,
  2,
  29,
  10
 ],
 [
  "packages/sdk/src/http/index.ts",
  129,
  10,
  129,
  18
 ]
]
```

Actual:

```json
[
 [
  "packages/sdk/src/http/index.ts",
  129,
  10,
  129,
  18
 ]
]
```

Project file `packages/sdk/src/http/index.ts`:

```
 129 |       }
 130 |       let response: Response;
 131 |       try {
 132 |         response = await this.fetch(url, { ...init, headers });
 133 |       } catch (cause) {
 134 |         if (abortState.signal?.aborted) {
 135 |           throw abortError(cause, abortState.timedOut());
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r3-definitionconsistency-missing-d-560852/repro.json
```

## Evidence and reduction

- representative 0b8a8909a573-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, modelcontextprotocol/servers@f46d9578190b, upstash/context7@6477e43e31d2, timings settled, seeds 1, 2

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
[ts7-7.0.2-tr560852-r3-replay-baseline-20260925-155132-84eb92] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr560852-r3-replay-baseline-20260925-155132-84eb92] stderr: context canceled
[ts7-7.0.2-tr560852-r3-replay-control-20260925-155145-48b7d3] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr560852-r3-replay-control-20260925-155145-48b7d3] stderr: context canceled
```
