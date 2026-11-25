# [ts6 6.0.3] mutation:M1 edit is not valid (diagnostics:extra:2339,7053)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2339-7053-mutation-m1-2aad71`, signature `ts6|r4_edits|diagnostics:extra:2339,7053`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `chenglou/pretext@2e5e2bdaee39` (corpus, commit 2e5e2bdaee398784b9cf27b24ca96df2e85396b8), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open pages/justification-check.ts`
3. textDocument/didChange: `change pages/justification-check.ts (1, 13)-(1, 25) ""`
4. textDocument/didChange: `change pages/justification-check.ts (20, 21)-(20, 31) "paragraph"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/generated/line-break-data.ts`, `tests/wrapping/fixtures/corpora.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `pages/justification-check.ts` line 21, column 22 (LSP position {line: 20, character: 21}) (M1:quickfix-errors:Change spelling to 'paragraph'); compare with the same query in a fresh session on the same content (expected).

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
  "2339",
  "typescript",
  "Property 'length' does not exist on type 'PositionedLine'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "typescript",
  "Property 'slice' does not exist on type 'PositionedLine'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7053",
  "typescript",
  "Element implicitly has an 'any' type because expression of type 'number' can't be used to index type 'PositionedLine'. No index signature with a parameter of type 'number' was found on type 'PositionedLine'."
 ]
]
```

Project file `pages/justification-check.ts`:

```
   1 | import { createDemoResources, buildDemoFrame } from './demos/justification-comparison.model.ts'
   2 | import { FONT, PARAGRAPHS } from './demos/justification-comparison.data.ts'
   3 | import { buildNavigationPhaseHash } from '../shared/navigation-state.ts'
     ...
   5 | const params = new URLSearchParams(location.search)
   6 | const requestId = params.get('requestId') ?? undefined
   7 | const widths = params.has('full')
   8 |   ? Array.from({ length: 401 }, (_, index) => index + 200)
   9 |   : [200, 364, 490, 491, 492, 493, 494, 495, 496, 497, 498, 600]
     ...
  11 | await document.fonts.load(FONT)
  12 | await document.fonts.ready
  13 | location.hash = buildNavigationPhaseHash('measuring', requestId)
  14 | const resources = createDemoResources()
  15 | const failures: object[] = []
  16 | let testedLines = 0
  17 | for (const colWidth of widths) {
  18 |   const frame = buildDemoFrame(resources, { colWidth, showIndicators: true })
  19 |   for (const name of ['hyphen', 'optimal'] as const) {
  20 |     for (const [paragraphIndex, paragraph] of frame[name].paragraphs.entries()) {
  21 |       const source = PARAGRAPHS[paragraphIndex]!
  22 |       let sourceOffset = 0
  23 |       for (const [lineIndex, line] of paragraph.entries()) {
  24 |         testedLines++
  25 |         // Follow the painter's segment advances, including its chosen spaces.
  26 |         let paintedWidth = 0
  27 |         let text = ''
  28 |         for (const segment of line.segments) {
  29 |           paintedWidth += segment.kind === 'space' && line.spacing.kind === 'justified'
  30 |             ? line.spacing.width : segment.width
  31 |           text += segment.kind === 'space' ? ' ' : segment.text
  32 |         }
  33 |         if (paintedWidth > line.maxWidth + 0.01) {
  34 |           failures.push({ kind: 'overflow', name, colWidth, paragraphIndex, lineIndex, paintedWidth, maxWidth: line.maxWidth, text })
  35 |         }
  36 |         if (line.trailingMarker === 'soft-hyphen' && line.ending === 'wrap') text = text.slice(0, -1)
  37 |         if (source.slice(sourceOffset, sourceOffset + text.length) !== text) {
  38 |           failures.push({ kind: 'source', name, colWidth, paragraphIndex, lineIndex, sourceOffset, text })
  39 |         }
  40 |         sourceOffset += text.length
  41 |         // Spaces consumed at a line boundary are absent from painted segments.
  42 |         while (source[sourceOffset] === ' ') sourceOffset++
  43 |       }
  44 |       if (sourceOffset !== source.length) {
  45 |         failures.push({ kind: 'incomplete-source', name, colWidth, paragraphIndex, sourceOffset })
  46 |       }
  47 |     }
  48 |   }
  49 | }
  50 | const report = {
  51 |   status: 'ready', requestId, userAgent: navigator.userAgent, dpr: devicePixelRatio,
  52 |   testedWidths: widths.length, testedLines, failures,
  53 | }
  54 | document.getElementById('result')!.textContent = JSON.stringify(report, null, 2)
  55 | const endpoint = params.get('reportEndpoint')
  56 | if (endpoint !== null) {
  57 |   location.hash = buildNavigationPhaseHash('posting', requestId)
  58 |   await fetch(endpoint, { method: 'POST', body: JSON.stringify(report) })
  59 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-2339-7053-mutation-m1-2aad71/repro.json
```

## Evidence and reduction

- representative dc251ae86847-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 3.355 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects chenglou/pretext@2e5e2bdaee39, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#815](https://github.com/typescript-language-server/typescript-language-server/issues/815) TSServer >=4.1.0 never publishes textDocument/publishDiagnostics event (NeoVim) (closed, 2023-11-16, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#724](https://github.com/typescript-language-server/typescript-language-server/issues/724) "typescript.inlayHints.includeInlayParameterNameHints": "all" breaks inference with dangling commas (closed, 2023-05-15, 7 comments)
- [microsoft/TypeScript#58262](https://github.com/microsoft/TypeScript/issues/58262) Enable `allowJs` with `isolatedDeclarations` (open, 2024-04-19, 6 comments)
- [microsoft/TypeScript#31849](https://github.com/microsoft/TypeScript/issues/31849) Document --incremental and composite project APIs (open, 2019-06-10, 50 comments)
- [microsoft/TypeScript#41860](https://github.com/microsoft/TypeScript/issues/41860) Richer Diagnostic Display Meta-Issue (open, 2020-12-07, 10 comments)
- queries: `diagnostics extra repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics "wrong edit" repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics extra repo:microsoft/TypeScript is:issue`; `diagnostics "wrong edit" repo:microsoft/TypeScript is:issue`
