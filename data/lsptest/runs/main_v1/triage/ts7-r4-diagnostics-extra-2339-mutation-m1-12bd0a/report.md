# [ts7 7.0.2] mutation:M1 edit is not valid (diagnostics:extra:2339)

Draft for the author (not filed). Group `ts7-r4-diagnostics-extra-2339-mutation-m1-12bd0a`, signature `ts7|r4_edits|diagnostics:extra:2339`, case family `mutation:M1`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa` (corpus, commit 2250cdcde4aad79d54101c80346df4190e0c2da7), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open scripts/eval_scenarios/network_test.ts`
3. textDocument/didChange: `change scripts/eval_scenarios/network_test.ts (6, 0)-(7, 0) ""`
4. textDocument/didChange: `change scripts/eval_scenarios/network_test.ts (7, 7)-(7, 7) "{ assert } from 'node:test';\nimport "`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `tests/e2e/telemetry.test.ts`, `tests/trace-processing/ChunkedTraceParser.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `scripts/eval_scenarios/network_test.ts` line 24, column 5 (LSP position {line: 23, character: 4}) (M1:quickfix-errors:Add import from "node:test"); compare with the same query in a fresh session on the same content (expected).

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
  "ts",
  "Property 'ok' does not exist on type 'typeof assert'."
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r4-diagnostics-extra-2339-mutation-m1-12bd0a/repro.json
```

## Evidence and reduction

- representative 085638e189e1-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (1 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4435](https://github.com/microsoft/typescript-go/issues/4435) Different diagnostics and exit code vs tsc for tsconfig using extends + baseUrl + wildcard paths (closed, 2026-06-24, 1 comments)
- [microsoft/typescript-go#3508](https://github.com/microsoft/typescript-go/issues/3508) Corsa no longer emits the TS-1 internal diagnostic about pre-emit/post-emit diagnostic count mismatches (closed, 2026-04-22, 2 comments)
- [microsoft/typescript-go#3615](https://github.com/microsoft/typescript-go/issues/3615) Server stops responding after `Running scheduled diagnostics refresh` (closed, 2026-04-26, 0 comments)
- [microsoft/typescript-go#4314](https://github.com/microsoft/typescript-go/issues/4314) Behavior difference: tsgo misses TS2345 when a namespace translator union is called with a template-literal key union (closed, 2026-06-15, 2 comments)
- [microsoft/typescript-go#1520](https://github.com/microsoft/typescript-go/issues/1520) --incremental builds are a bit slower after the 20250805 release (closed, 2025-08-05, 5 comments)
- queries: `diagnostics extra repo:microsoft/typescript-go is:issue`; `diagnostics "wrong edit" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr12bd0a-r4-replay-baseline-20260925-155629-a72938] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr12bd0a-r4-replay-baseline-20260925-155629-a72938] stderr: context canceled
[ts7-7.0.2-tr12bd0a-r4-replay-case-20260925-155611-b83d8c] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr12bd0a-r4-replay-case-20260925-155611-b83d8c] stderr: context canceled
[ts7-7.0.2-tr12bd0a-r4-replay-control-20260925-155650-40cf88] stderr: context canceled
```
