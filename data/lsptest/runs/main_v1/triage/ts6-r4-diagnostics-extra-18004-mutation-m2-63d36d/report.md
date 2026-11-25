# [ts6 6.0.3] mutation:M2 edit is not valid (diagnostics:extra:18004)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-18004-mutation-m2-63d36d`, signature `ts6|r4_edits|diagnostics:extra:18004`, case family `mutation:M2`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa` (corpus, commit 2250cdcde4aad79d54101c80346df4190e0c2da7), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open scripts/eval_scenarios/network_test.ts`
3. textDocument/didChange: `change scripts/eval_scenarios/network_test.ts (27, 33)-(27, 39) "pageeId"`
4. textDocument/didChange: `change scripts/eval_scenarios/network_test.ts (23, 4)-(24, 4) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `tests/e2e/telemetry.test.ts`, `tests/trace-processing/ChunkedTraceParser.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `scripts/eval_scenarios/network_test.ts` line 24, column 11 (LSP position {line: 23, character: 10}) (M2:quickfix-errors:Remove unused declaration for: 'pageId'); compare with the same query in a fresh session on the same content (expected).

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
  "18004",
  "typescript",
  "No value exists in scope for the shorthand property 'pageeId'. Either declare one or provide an initializer."
 ]
]
```

Project file `scripts/eval_scenarios/network_test.ts`:

```
   1 | /**
   2 |  * @license
   3 |  * Copyright 2026 Google LLC
   4 |  * SPDX-License-Identifier: Apache-2.0
   5 |  */
     ...
   7 | import assert from 'node:assert';
     ...
   9 | import type {TestScenario} from '../eval_gemini.ts';
     ...
  11 | export const scenario: TestScenario = {
  12 |   prompt: 'Navigate to <TEST_URL> and list all network requests.',
  13 |   maxTurns: 3,
  14 |   htmlRoute: {
  15 |     path: '/network_test.html',
  16 |     htmlContent: `
  17 |       <h1>Network Test</h1>
  18 |       <script>
  19 |         fetch('/network_test.html'); // Self fetch to ensure at least one request
  20 |       </script>
  21 |     `,
  22 |   },
  23 |   expectations: result => {
  24 |     const pageId = result.consumePageNavigation();
  25 |     assert.ok(result.remainingCalls.length >= 1);
  26 |     result.assertNextCall(
  27 |       'list_network_requests',
  28 |       result.hasPageIdRouting ? {pageId} : undefined,
  29 |     );
  30 |   },
  31 | };
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-18004-mutation-m2-63d36d/repro.json
```

## Evidence and reduction

- representative f32275e691ea-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 9.054 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa, timings settled, seeds 1

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
