# [ts7 7.0.2] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-definitionconsistency-changed-d-a42b32`, signature `ts7|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `packages/web/test/latest-shadow-owned-write-issue-3378.spec.tsx` at line 50, column 19 (LSP position {line: 49, character: 18}) gives the expected set; didOpen `packages/element/test/element.spec.tsx` and `textDocument/definition` at the reference line 159, column 35 (LSP position {line: 158, character: 34}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.dom.d.ts",
  13912,
  8,
  13912,
  19
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.dom.d.ts",
  13913,
  8,
  13913,
  19
 ]
]
```

Actual:

```json
[
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.dom.d.ts",
  13225,
  8,
  13225,
  19
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.dom.d.ts",
  13226,
  8,
  13226,
  19
 ]
]
```

Project file `packages/element/test/element.spec.tsx`:

```
 156 |     );
 157 |     const child = root.querySelector(childTag)!;
     ...
 159 |     expect(child.shadowRoot!.textContent).toBe("ancestor");
 160 |     dispose();
 161 |     root.remove();
 162 |   });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r3-definitionconsistency-changed-d-a42b32/repro.json
```

## Evidence and reduction

- representative 2743534ec8dd-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects DayuanJiang/next-ai-draw-io@58b73ef761d8, solidjs/solid@4b62bc29e04b, umami-software/umami@12ad773d621f, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4908](https://github.com/microsoft/typescript-go/issues/4908) Go-to-definition does not work at the right edge of a JSX tag name (closed, 2026-08-17, 0 comments)
- [microsoft/typescript-go#1885](https://github.com/microsoft/typescript-go/issues/1885) go to definition panic (windows, wsl) (closed, 2025-10-15, 4 comments)
- [microsoft/typescript-go#2209](https://github.com/microsoft/typescript-go/issues/2209) [lsp] Go to Definition missing getter when property returns callable interface (closed, 2025-12-04, 0 comments)
- [microsoft/typescript-go#2839](https://github.com/microsoft/typescript-go/issues/2839) Cannot "go to definition" of a playwright fixture (closed, 2026-02-19, 1 comments)
- [microsoft/typescript-go#2847](https://github.com/microsoft/typescript-go/issues/2847) panic on go-to-type-definition of tuple type (closed, 2026-02-20, 0 comments)
- [microsoft/typescript-go#1673](https://github.com/microsoft/typescript-go/issues/1673) Panic on textDocument/definition (closed, 2025-09-03, 8 comments)
- [microsoft/typescript-go#2183](https://github.com/microsoft/typescript-go/issues/2183) cannot resolve type definition with type:module (closed, 2025-12-03, 8 comments)
- [microsoft/typescript-go#3026](https://github.com/microsoft/typescript-go/issues/3026) TypeScript Native Preview VS Code extension status bar color is confusing (closed, 2026-03-09, 3 comments)
- queries: `"go to definition" in:title repo:microsoft/typescript-go is:issue`; `definition wrong repo:microsoft/typescript-go is:issue`; `definition "go to definition" repo:microsoft/typescript-go is:issue`; `definition inconsistent repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tra42b32-r3-replay-baseline-20261118-214609-29a754] stderr: context canceled
[ts7-7.0.2-tra42b32-r3-replay-control-20261118-214620-c52ca8] stderr: context canceled
```
