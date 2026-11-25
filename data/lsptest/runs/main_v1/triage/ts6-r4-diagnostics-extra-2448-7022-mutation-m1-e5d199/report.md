# [ts6 6.0.3] mutation:M1 edit is not valid (diagnostics:extra:2448,7022)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2448-7022-mutation-m1-e5d199`, signature `ts6|r4_edits|diagnostics:extra:2448,7022`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `modelcontextprotocol/servers@f46d9578190b` (corpus, commit f46d9578190b476b3501923ea8977d899e8db2cb), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/everything/prompts/resource.ts`
3. textDocument/didChange: `change src/everything/prompts/resource.ts (9, 2)-(10, 2) ""`
4. textDocument/didChange: `change src/everything/prompts/resource.ts (69, 12)-(69, 17) "r"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/everything/prompts/simple.ts`, `src/sequentialthinking/__tests__/input-schema.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `src/everything/prompts/resource.ts` line 70, column 13 (LSP position {line: 69, character: 12}) (M1:quickfix-errors:Change spelling to 'resource'); compare with the same query in a fresh session on the same content (expected).

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
  "2448",
  "typescript",
  "Block-scoped variable 'resource' used before its declaration."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7022",
  "typescript",
  "'resource' implicitly has type 'any' because it does not have a type annotation and is referenced directly or indirectly in its own initializer."
 ]
]
```

Project file `src/everything/prompts/resource.ts`:

```
   1 | import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
   2 | import {
   3 |   resourceTypeCompleter,
   4 |   resourceIdForPromptCompleter,
   5 | } from "../resources/templates.js";
   6 | import {
   7 |   textResource,
   8 |   textResourceUri,
   9 |   blobResourceUri,
  10 |   blobResource,
  11 |   RESOURCE_TYPE_BLOB,
  12 |   RESOURCE_TYPE_TEXT,
  13 |   RESOURCE_TYPES,
  14 | } from "../resources/templates.js";
     ...
  16 | /**
  17 |  * Register a prompt with an embedded resource reference
  18 |  * - Takes a resource type and id
  19 |  * - Returns the corresponding dynamically created resource
  20 |  *
  21 |  * @param server
  22 |  */
  23 | export const registerEmbeddedResourcePrompt = (server: McpServer) => {
  24 |   // Prompt arguments
  25 |   const promptArgsSchema = {
  26 |     resourceType: resourceTypeCompleter,
  27 |     resourceId: resourceIdForPromptCompleter,
  28 |   };
     ...
  30 |   // Register the prompt
  31 |   server.registerPrompt(
  32 |     "resource-prompt",
  33 |     {
  34 |       title: "Resource Prompt",
  35 |       description: "A prompt that includes an embedded resource reference",
  36 |       argsSchema: promptArgsSchema,
  37 |     },
  38 |     (args) => {
  39 |       // Validate resource type argument
  40 |       const resourceType = args.resourceType;
  41 |       if (
  42 |         !RESOURCE_TYPES.includes(
  43 |           resourceType as typeof RESOURCE_TYPE_TEXT | typeof RESOURCE_TYPE_BLOB
  44 |         )
  45 |       ) {
  46 |         throw new Error(
  47 |           `Invalid resourceType: ${args?.resourceType}. Must be ${RESOURCE_TYPE_TEXT} or ${RESOURCE_TYPE_BLOB}.`
  48 |         );
  49 |       }
     ...
  51 |       // Validate resourceId argument
  52 |       const resourceId = Number(args?.resourceId);
  53 |       if (
  54 |         !Number.isFinite(resourceId) ||
  55 |         !Number.isInteger(resourceId) ||
  56 |         resourceId < 1
  57 |       ) {
  58 |         throw new Error(
  59 |           `Invalid resourceId: ${args?.resourceId}. Must be a finite positive integer.`
  60 |         );
  61 |       }
     ...
  63 |       // Get resource based on the resource type
  64 |       const uri =
  65 |         resourceType === RESOURCE_TYPE_TEXT
  66 |           ? textResourceUri(resourceId)
  67 |           : blobResourceUri(resourceId);
  68 |       const resource =
  69 |         resourceType === RESOURCE_TYPE_TEXT
  70 |           ? textResource(uri, resourceId)
  71 |           : blobResource(uri, resourceId);
     ...
  73 |       return {
  74 |         messages: [
  75 |           {
  76 |             role: "user",
  77 |             content: {
  78 |               type: "text",
  79 |               text: `This prompt includes the ${resourceType} resource with id: ${resourceId}. Please analyze the following resource:`,
  80 |             },
  81 |           },
  82 |           {
  83 |             role: "user",
  84 |             content: {
  85 |               type: "resource",
  86 |               resource: resource,
  87 |             },
  88 |           },
  89 |         ],
  90 |       };
  91 |     }
  92 |   );
  93 | };
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-2448-7022-mutation-m1-e5d199/repro.json
```

## Evidence and reduction

- representative 3ee57b1ff483-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 3.941 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects modelcontextprotocol/servers@f46d9578190b, timings settled, seeds 1

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
