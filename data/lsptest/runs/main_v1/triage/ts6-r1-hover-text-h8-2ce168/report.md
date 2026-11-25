# [ts6 6.0.3] hover shows a different text after query order

Draft for the author (not filed). Group `ts6-r1-hover-text-h8-2ce168`, signature `ts6|r1_history|hover:text`, case family `H8`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `upstash/context7@6477e43e31d2` (corpus, commit 6477e43e31d27a5c1bc044506e1c14de15f8a110), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open packages/sdk/src/commands/command.ts`
3. Timing: wait until the server is idle after every step.
4. textDocument/didOpen `packages/cli/src/__tests__/command-auth-wiring.test.ts`, `packages/sdk/src/client.ts` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/hover` on `packages/sdk/src/commands/command.ts` line 14, column 31 (LSP position {line: 13, character: 30}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "type CommandRequest = { cache?: CacheSetting | undefined; body?: unknown; method?: \"GET\" | \"POST\" | undefined; query?: Record<string, string | number | boolean | readonly (string | number | boolean)[] | undefined> | undefined; signal?: AbortSignal | undefined; timeout?: number | false | undefined; }",
 [
  13,
  23,
  13,
  37
 ]
]
```

Actual:

```json
[
 "type CommandRequest = { body?: unknown; method?: \"GET\" | \"POST\" | undefined; query?: Record<string, string | number | boolean | readonly (string | number | boolean)[] | undefined> | undefined; signal?: AbortSignal | undefined; timeout?: number | false | undefined; cache?: CacheSetting | undefined; }",
 [
  13,
  23,
  13,
  37
 ]
]
```

Project file `packages/sdk/src/commands/command.ts`:

```
   1 | import { Context7Error } from "@error";
   2 | import type { Context7Request, Requester } from "@http";
     ...
   4 | export const _ENDPOINTS = ["v2/libs/search", "v2/context", "v3/search"];
     ...
   6 | export type EndpointVariants = (typeof _ENDPOINTS)[number];
     ...
   8 | export type CommandRequest = Omit<Context7Request, "path">;
     ...
  10 | export class Command<TResult> {
  11 |   public readonly request: CommandRequest;
  12 |   public readonly endpoint: EndpointVariants;
     ...
  14 |   constructor(request: CommandRequest, endpoint: EndpointVariants) {
  15 |     this.request = request;
  16 |     this.endpoint = endpoint;
  17 |   }
     ...
  19 |   /**
  20 |    * Execute the command using a client.
  21 |    */
  22 |   public async exec(client: Requester): Promise<TResult> {
  23 |     return this.requestResult<TResult>(client);
  24 |   }
     ...
  26 |   protected async requestResult<T>(client: Requester): Promise<T> {
  27 |     const { result } = await client.request<T>({ ...this.request, path: [this.endpoint] });
     ...
  29 |     if (result === undefined) {
  30 |       throw new Context7Error("Request did not return a result", {
  31 |         code: "invalid_response",
  32 |       });
  33 |     }
     ...
  35 |     return result;
  36 |   }
  37 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-hover-text-h8-2ce168/repro.json
```

## Evidence and reduction

- representative 3f26f1994ad8-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 14 -> 1 (7 probes, 325.833 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects upstash/context7@6477e43e31d2, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#865](https://github.com/typescript-language-server/typescript-language-server/issues/865) Fully resolve type aliases  (closed, 2024-02-02, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#445](https://github.com/typescript-language-server/typescript-language-server/issues/445) Issue with tsconfig and first file opened (closed, 2022-05-03, 4 comments)
- [typescript-language-server/typescript-language-server#803](https://github.com/typescript-language-server/typescript-language-server/issues/803) Server error "Could not find source file" on opening second file in a project with large amount of code (closed, 2023-11-14, 4 comments)
- [typescript-language-server/typescript-language-server#191](https://github.com/typescript-language-server/typescript-language-server/issues/191) doRequestDiagnostics of LspServer looks did not handle err? no 'catch'? (closed, 2021-03-11, 61 comments)
- [microsoft/TypeScript#63758](https://github.com/microsoft/TypeScript/issues/63758) Investigate decorator initialization order re: renames of classes (open, 2026-08-18, 0 comments)
- queries: `order in:title repo:typescript-language-server/typescript-language-server is:issue`; `hover wrong repo:typescript-language-server/typescript-language-server is:issue`; `hover order repo:typescript-language-server/typescript-language-server is:issue`; `hover stale repo:typescript-language-server/typescript-language-server is:issue`; `order in:title repo:microsoft/TypeScript is:issue`; `hover wrong repo:microsoft/TypeScript is:issue`; `hover order repo:microsoft/TypeScript is:issue`; `hover stale repo:microsoft/TypeScript is:issue`
