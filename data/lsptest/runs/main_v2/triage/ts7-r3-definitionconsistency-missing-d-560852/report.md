# [ts7 7.0.2] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-definitionconsistency-missing-d-560852`, signature `ts7|r3_routes|definitionConsistency:missing`, case family `d`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `pear-devs/pear-desktop@3ff0a86231fe` (corpus, commit 3ff0a86231fed97b1a4365de0521fc96794c3f67), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/plugins/equalizer/index.ts` at line 83, column 7 (LSP position {line: 82, character: 6}) gives the expected set; didOpen `src/plugins/captions-selector/back.ts` and `textDocument/definition` at the reference line 30, column 5 (LSP position {line: 29, character: 4}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/plugins/equalizer/index.ts",
  82,
  4,
  82,
  8
 ],
 [
  "src/types/plugins.ts",
  20,
  2,
  20,
  6
 ]
]
```

Actual:

```json
[
 [
  "src/types/plugins.ts",
  20,
  2,
  20,
  6
 ]
]
```

Project file `src/plugins/captions-selector/back.ts`:

```
   1 | import prompt from 'custom-electron-prompt';
     ...
   3 | import { t } from '@/i18n';
   4 | import promptOptions from '@/providers/prompt-options';
   5 | import { createBackend } from '@/utils';
     ...
   7 | export default createBackend({
   8 |   start({ ipc: { handle }, window }) {
   9 |     handle(
  10 |       'peard:captions-selector',
  11 |       async (captionLabels: Record<string, string>, currentIndex: string) =>
  12 |         await prompt(
  13 |           {
  14 |             title: t('plugins.captions-selector.prompt.selector.title'),
  15 |             label: t('plugins.captions-selector.prompt.selector.label', {
  16 |               language:
  17 |                 captionLabels[currentIndex] ||
  18 |                 t('plugins.captions-selector.prompt.selector.none'),
  19 |             }),
  20 |             type: 'select',
  21 |             value: currentIndex,
  22 |             selectOptions: captionLabels,
  23 |             resizable: true,
  24 |             ...promptOptions(),
  25 |           },
  26 |           window,
  27 |         ),
  28 |     );
  29 |   },
  30 |   stop({ ipc: { removeHandler } }) {
  31 |     removeHandler('peard:captions-selector');
  32 |   },
  33 | });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r3-definitionconsistency-missing-d-560852/repro.json
```

## Evidence and reduction

- representative 3e554bc8dfb0-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects pear-devs/pear-desktop@3ff0a86231fe, umami-software/umami@12ad773d621f, timings settled, seeds 2

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
[ts7-7.0.2-tr560852-r3-replay-baseline-20261118-215059-8b8e2c] stderr: context canceled
[ts7-7.0.2-tr560852-r3-replay-control-20261118-215117-34d00b] stderr: context canceled
```
