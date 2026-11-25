# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-changed-d-bf619d`, signature `ts6|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `upstash/context7@6477e43e31d2` (corpus, commit 6477e43e31d27a5c1bc044506e1c14de15f8a110), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `packages/sdk/src/commands/command.ts` at line 27, column 16 (LSP position {line: 26, character: 15}) gives the expected set; didOpen `packages/sdk/src/commands/command.ts` and `textDocument/definition` at the reference line 29, column 12 (LSP position {line: 28, character: 11}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "packages/sdk/src/http/types.ts",
  60,
  2,
  60,
  8
 ]
]
```

Actual:

```json
[
 [
  "packages/sdk/src/commands/command.ts",
  26,
  12,
  26,
  18
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r3-definitionconsistency-changed-d-bf619d/repro.json
```

## Evidence and reduction

- representative 05138076f1e7-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects pmndrs/zustand@b57db4f86ef1, reduxjs/redux@fb3bad6804d6, upstash/context7@6477e43e31d2, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#795](https://github.com/typescript-language-server/typescript-language-server/issues/795) Go to definition is not working on neovim (closed, 2023-11-12, 2 comments)
- [typescript-language-server/typescript-language-server#507](https://github.com/typescript-language-server/typescript-language-server/issues/507) Possibility of including Go to Source Definition? (closed, 2022-07-03, 4 comments)
- [typescript-language-server/typescript-language-server#431](https://github.com/typescript-language-server/typescript-language-server/issues/431) Go to definition function broken in monorepo project (closed, 2022-04-10, 4 comments)
- [typescript-language-server/typescript-language-server#216](https://github.com/typescript-language-server/typescript-language-server/issues/216) Multiple and wrong definition (closed, 2021-06-03, 38 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#632](https://github.com/typescript-language-server/typescript-language-server/issues/632) Wrong or confusing Semantic Token Types reported (closed, 2022-11-23, 1 comments)
- [typescript-language-server/typescript-language-server#495](https://github.com/typescript-language-server/typescript-language-server/issues/495) Wrong tsconfig.json being used in monorepo (closed, 2022-06-16, 4 comments)
- queries: `"go to definition" in:title repo:typescript-language-server/typescript-language-server is:issue`; `definition wrong repo:typescript-language-server/typescript-language-server is:issue`; `definition "go to definition" repo:typescript-language-server/typescript-language-server is:issue`; `definition inconsistent repo:typescript-language-server/typescript-language-server is:issue`; `"go to definition" in:title repo:microsoft/TypeScript is:issue`; `definition wrong repo:microsoft/TypeScript is:issue`; `definition "go to definition" repo:microsoft/TypeScript is:issue`; `definition inconsistent repo:microsoft/TypeScript is:issue`
