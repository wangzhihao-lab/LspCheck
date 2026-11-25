# [ts6 6.0.3] mutation:M1 edit is not valid (diagnostics:extra:2339)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2339-mutation-m1-a8c765`, signature `ts6|r4_edits|diagnostics:extra:2339`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa` (corpus, commit 2250cdcde4aad79d54101c80346df4190e0c2da7), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open scripts/eval_result.ts`
3. textDocument/didChange: `change scripts/eval_result.ts (6, 0)-(7, 0) ""`
4. textDocument/didChange: `change scripts/eval_result.ts (6, 0)-(6, 0) "import { assert } from \"console\";\n\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `scripts/profile/source_map_server.ts`, `tests/shutdown.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `scripts/eval_result.ts` line 47, column 5 (LSP position {line: 46, character: 4}) (M1:quickfix-errors:Add import from "console"); compare with the same query in a fresh session on the same content (expected).

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
  "Property 'deepStrictEqual' does not exist on type '(condition?: unknown, ...data: any[]) => void'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "typescript",
  "Property 'ok' does not exist on type '(condition?: unknown, ...data: any[]) => void'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "typescript",
  "Property 'ok' does not exist on type '(condition?: unknown, ...data: any[]) => void'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "typescript",
  "Property 'ok' does not exist on type '(condition?: unknown, ...data: any[]) => void'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "typescript",
  "Property 'strictEqual' does not exist on type '(condition?: unknown, ...data: any[]) => void'."
 ]
]
```

Project file `scripts/eval_result.ts`:

```
   1 | /**
   2 |  * @license
   3 |  * Copyright 2026 Google LLC
   4 |  * SPDX-License-Identifier: Apache-2.0
   5 |  */
     ...
   7 | import assert from 'node:assert';
     ...
   9 | export interface CapturedFunctionCall {
  10 |   name: string;
  11 |   args: Record<string, unknown>;
  12 | }
     ...
  14 | export class Result {
  15 |   private nextCallIndex = 0;
  16 |   public readonly calls: CapturedFunctionCall[];
  17 |   public readonly serverArgs: string[];
  18 |   /** The model's final response text. */
  19 |   public readonly text: string;
     ...
  21 |   constructor(calls: CapturedFunctionCall[], serverArgs: string[], text = '') {
  22 |     this.calls = calls;
  23 |     this.serverArgs = serverArgs;
  24 |     this.text = text;
  25 |   }
     ...
  27 |   get hasPageIdRouting(): boolean {
  28 |     return !this.serverArgs.includes('--no-page-id-routing');
  29 |   }
     ...
  31 |   get remainingCalls(): CapturedFunctionCall[] {
  32 |     return this.calls.slice(this.nextCallIndex);
  33 |   }
     ...
  35 |   /**
  36 |    * Consumes initial page navigation/setup boilerplate.
  37 |    * - Ignores/skips leading or trailing list_pages calls.
  38 |    * - Asserts that new_page or navigate_page was called.
  39 |    * - Determines the expected pageId.
  40 |    * - Returns the active pageId.
  41 |    */
  42 |   consumePageNavigation(): number | undefined {
  43 |     if (this.calls[this.nextCallIndex]?.name === 'list_pages') {
  44 |       this.nextCallIndex++;
  45 |     }
     ...
  47 |     const navCall = this.calls[this.nextCallIndex];
  48 |     assert.ok(
  49 |       navCall &&
  50 |         (navCall.name === 'new_page' || navCall.name === 'navigate_page'),
  51 |       `Expected navigation call (new_page or navigate_page), but got: ${navCall?.name || 'none'}`,
  52 |     );
  53 |     this.nextCallIndex++;
     ...
  55 |     if (this.calls[this.nextCallIndex]?.name === 'list_pages') {
  56 |       this.nextCallIndex++;
  57 |     }
     ...
  59 |     const isNewPage = navCall.name === 'new_page';
  60 |     let pageId: number | undefined;
  61 |     if (this.hasPageIdRouting) {
  62 |       pageId = isNewPage ? 2 : 1;
  63 |     }
     ...
  65 |     return pageId;
  66 |   }
     ...
  68 |   /**
  69 |    * Asserts that the next call in sequence has the correct name and matches expected arguments.
  70 |    * Increments the internal call index.
  71 |    */
  72 |   assertNextCall(
  73 |     name: string,
  74 |     expectedArgs?: Record<string, unknown>,
  75 |   ): CapturedFunctionCall {
  76 |     const call = this.calls[this.nextCallIndex];
  77 |     assert.ok(
  78 |       call,
  79 |       `Expected call at index ${this.nextCallIndex} (name: '${name}') to exist`,
  80 |     );
  81 |     assert.strictEqual(
  82 |       call.name,
  83 |       name,
  84 |       `Expected call at index ${this.nextCallIndex} to be '${name}', but got '${call.name}'`,
  85 |     );
     ...
  87 |     if (expectedArgs) {
  88 |       for (const entry of Object.entries(expectedArgs)) {
  89 |         const key = entry[0];
  90 |         const value = entry[1];
  91 |         assert.deepStrictEqual(
  92 |           call.args[key],
  93 |           value,
  94 |           `Expected argument '${key}' on call '${name}' to be ${JSON.stringify(value)}, got ${JSON.stringify(call.args[key])}`,
  95 |         );
  96 |       }
  97 |     }
     ...
  99 |     this.nextCallIndex++;
 100 |     return call;
 101 |   }
     ...
 103 |   /**
 104 |    * Asserts that the model's response contains every given substring,
 105 |    * ignoring case.
 106 |    */
 107 |   assertTextIncludes(...substrings: string[]): void {
 108 |     const textInLowerCase = this.text.toLowerCase();
 109 |     for (const substring of substrings) {
 110 |       assert.ok(
 111 |         textInLowerCase.includes(substring.toLowerCase()),
 112 |         `Expected response to mention '${substring}'. Response: ${this.text}`,
 113 |       );
 114 |     }
 115 |   }
 116 | }
     ...
 118 | export interface TestScenario {
 119 |   prompt: string;
 120 |   maxTurns: number;
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-2339-mutation-m1-a8c765/repro.json
```

## Evidence and reduction

- representative 044b664b39ee-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 7.674 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa, timings settled, seeds 1, 2

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
