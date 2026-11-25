# [ts6 6.0.3] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-highlightvsreferences-gained-c-e8db7c`, signature `ts6|r3_routes|highlightVsReferences:gained`, case family `c`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa` (corpus, commit 2250cdcde4aad79d54101c80346df4190e0c2da7), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `scripts/eval_result.ts` at line 27, column 4 (LSP position {line: 26, character: 3}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  26,
  2,
  26,
  5
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r3-highlightvsreferences-gained-c-e8db7c/repro.json
```

## Evidence and reduction

- representative 7587da4972f6-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#961](https://github.com/typescript-language-server/typescript-language-server/issues/961) Find all references does not find import(fileName) of the given file (closed, 2025-07-16, 2 comments)
- [typescript-language-server/typescript-language-server#754](https://github.com/typescript-language-server/typescript-language-server/issues/754) Not able to find references to certain consts (closed, 2023-09-05, 2 comments)
- [typescript-language-server/typescript-language-server#438](https://github.com/typescript-language-server/typescript-language-server/issues/438) By default, ignores some undefined references like: onsole.lg() (closed, 2022-04-20, 2 comments)
- [typescript-language-server/typescript-language-server#206](https://github.com/typescript-language-server/typescript-language-server/issues/206) Method ‘textDocument/references’ does not respect includeDeclarations option (closed, 2021-04-28, 9 comments)
- [typescript-language-server/typescript-language-server#54](https://github.com/typescript-language-server/typescript-language-server/issues/54) project references support (closed, 2018-08-15, 2 comments)
- [typescript-language-server/typescript-language-server#700](https://github.com/typescript-language-server/typescript-language-server/issues/700) Dont find syntax error (closed, 2023-03-09, 1 comments)
- [typescript-language-server/typescript-language-server#724](https://github.com/typescript-language-server/typescript-language-server/issues/724) "typescript.inlayHints.includeInlayParameterNameHints": "all" breaks inference with dangling commas (closed, 2023-05-15, 7 comments)
- [typescript-language-server/typescript-language-server#225](https://github.com/typescript-language-server/typescript-language-server/issues/225) Rename command doesn't work on TS LS  (closed, 2021-06-25, 10 comments)
- queries: `references in:title repo:typescript-language-server/typescript-language-server is:issue`; `highlight unexpected repo:typescript-language-server/typescript-language-server is:issue`; `highlight references repo:typescript-language-server/typescript-language-server is:issue`; `highlight inconsistent repo:typescript-language-server/typescript-language-server is:issue`; `references in:title repo:microsoft/TypeScript is:issue`; `highlight unexpected repo:microsoft/TypeScript is:issue`; `highlight references repo:microsoft/TypeScript is:issue`; `highlight inconsistent repo:microsoft/TypeScript is:issue`
