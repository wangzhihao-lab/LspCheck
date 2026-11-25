# [ts6 6.0.3] mutation:M3 edit is not valid (diagnostics:extra:2554)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2554-mutation-m3-d2ab31`, signature `ts6|r4_edits|diagnostics:extra:2554`, case family `mutation:M3`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/utils/requirement-diff.ts`
3. textDocument/didChange: `change src/utils/requirement-diff.ts (62, 38)-(62, 48) ""`
4. textDocument/didChange: `change src/utils/requirement-diff.ts (60, 63)-(60, 83) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/core/schemas/index.ts`, `test/core/misplaced-delta-files.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `src/utils/requirement-diff.ts` line 61, column 64 (LSP position {line: 60, character: 63}) (M3:quickfix-errors:Remove unused declaration for: 'deltaBlock'); compare with the same query in a fresh session on the same content (expected).

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
  "2554",
  "typescript",
  "Expected 1 arguments, but got 0."
 ]
]
```

Project file `src/utils/requirement-diff.ts`:

```
   1 | import { formatPatch, OMIT_HEADERS, structuredPatch } from 'diff';
   2 | import {
   3 |   extractRequirementsSection,
   4 |   foldRequirementName,
   5 |   normalizeRequirementName,
   6 | } from '../core/parsers/requirement-blocks.js';
     ...
   8 | /** A main-spec requirement block, and how its header matched the delta's. */
   9 | export interface MatchedRequirementBlock {
  10 |   raw: string;
  11 |   /** The header name as the main spec spells it. */
  12 |   name: string;
  13 |   /**
  14 |    * False when the two headers differ only in case or interior spacing. Archive
  15 |    * matches names exactly, so an inexact match is a real problem to report even
  16 |    * though the diff below it is still the one the author meant.
  17 |    */
  18 |   exact: boolean;
  19 | }
     ...
  21 | /**
  22 |  * Find the raw markdown block for a requirement by name in a spec file.
  23 |  *
  24 |  * Delegates to extractRequirementsSection() which already handles code fences,
  25 |  * section boundaries, and requirement header parsing. We just look up by name:
  26 |  * exactly first, then falling back to the shared case/whitespace fold so a
  27 |  * header that differs only in spelling still shows its diff, flagged inexact.
  28 |  *
  29 |  * Returns null if no requirement header matches either way.
  30 |  */
  31 | export function extractRequirementBlock(
  32 |   specContent: string,
  33 |   requirementName: string
  34 | ): MatchedRequirementBlock | null {
  35 |   const parts = extractRequirementsSection(specContent);
  36 |   const targetName = normalizeRequirementName(requirementName);
  37 |   const foldedTarget = foldRequirementName(targetName);
  38 |   let folded: MatchedRequirementBlock | null = null;
     ...
  40 |   for (const block of parts.bodyBlocks) {
  41 |     const name = normalizeRequirementName(block.name);
  42 |     if (name === targetName) {
  43 |       return { raw: block.raw, name, exact: true };
  44 |     }
  45 |     if (!folded && foldRequirementName(name) === foldedTarget) {
  46 |       folded = { raw: block.raw, name, exact: false };
  47 |     }
  48 |   }
     ...
  50 |   return folded;
  51 | }
     ...
  53 | /**
  54 |  * Compute a unified diff between a main-spec requirement block and the delta
  55 |  * block that replaces it. A null main block (new capability) diffs against the
  56 |  * empty string, so every line reads as an addition.
  57 |  *
  58 |  * Uses structuredPatch to retain unified-diff hunk ranges while omitting the
  59 |  * synthetic file headers, since the caller provides its own labeling.
  60 |  */
  61 | export function diffRequirementBlock(baseBlock: string | null, deltaBlock: string, label: string): string {
  62 |   const base = ensureTrailingNewline(baseBlock ?? '');
  63 |   const delta = ensureTrailingNewline(deltaBlock);
  64 |   const patch = structuredPatch(label, label, base, delta);
     ...
  66 |   return formatPatch(patch, OMIT_HEADERS).trimEnd();
  67 | }
     ...
  69 | function ensureTrailingNewline(s: string): string {
  70 |   return s.endsWith('\n') ? s : s + '\n';
  71 | }
     ...
  73 | /**
  74 |  * Build a map from folded RENAMED TO name to the original main-spec name.
  75 |  * Renames apply in source order, so a chain such as A -> B -> C maps C back to
  76 |  * A. That is the block a later MODIFIED C replaces.
  77 |  */
  78 | export function buildRenameMap(renames: Array<{ from: string; to: string }>): Map<string, string> {
  79 |   const map = new Map<string, string>();
  80 |   for (const r of renames) {
  81 |     const from = foldRequirementName(r.from);
  82 |     const original = map.get(from) ?? normalizeRequirementName(r.from);
  83 |     map.delete(from);
  84 |     map.set(foldRequirementName(r.to), original);
  85 |   }
  86 |   return map;
  87 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-2554-mutation-m3-d2ab31/repro.json
```

## Evidence and reduction

- representative 295e3654bbae-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 4.226 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, timings settled, seeds 2

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
