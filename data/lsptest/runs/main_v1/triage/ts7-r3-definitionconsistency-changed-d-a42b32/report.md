# [ts7 7.0.2] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-definitionconsistency-changed-d-a42b32`, signature `ts7|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `upstash/context7@6477e43e31d2` (corpus, commit 6477e43e31d27a5c1bc044506e1c14de15f8a110), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r3-definitionconsistency-changed-d-a42b32/repro.json
```

## Evidence and reduction

- representative 08daa748dcca-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, reduxjs/redux@fb3bad6804d6, upstash/context7@6477e43e31d2, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4908](https://github.com/microsoft/typescript-go/issues/4908) Go-to-definition does not work at the right edge of a JSX tag name (closed, 2026-08-17, 0 comments)
- [microsoft/typescript-go#1885](https://github.com/microsoft/typescript-go/issues/1885) go to definition panic (windows, wsl) (closed, 2025-10-15, 4 comments)
- [microsoft/typescript-go#2209](https://github.com/microsoft/typescript-go/issues/2209) [lsp] Go to Definition missing getter when property returns callable interface (closed, 2025-12-04, 0 comments)
- [microsoft/typescript-go#2839](https://github.com/microsoft/typescript-go/issues/2839) Cannot "go to definition" of a playwright fixture (closed, 2026-02-19, 1 comments)
- [microsoft/typescript-go#2847](https://github.com/microsoft/typescript-go/issues/2847) panic on go-to-type-definition of tuple type (closed, 2026-02-20, 0 comments)
- [microsoft/typescript-go#1673](https://github.com/microsoft/typescript-go/issues/1673) Panic on textDocument/definition (closed, 2025-09-03, 8 comments)
- [microsoft/typescript-go#2183](https://github.com/microsoft/typescript-go/issues/2183) cannot resolve type definition with type:module (closed, 2025-12-03, 8 comments)
- [microsoft/typescript-go#3026](https://github.com/microsoft/typescript-go/issues/3026) TypeScript Native Preview VS Code extension status bar color is confusing (closed, 2026-03-09, 3 comments)
- queries: `"go to definition" in:title repo:microsoft/typescript-go is:issue`; `definition wrong repo:microsoft/typescript-go is:issue`; `definition "go to definition" repo:microsoft/typescript-go is:issue`; `definition inconsistent repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tra42b32-r3-replay-baseline-20260925-154708-95a6c8] stderr: context canceled
[ts7-7.0.2-tra42b32-r3-replay-control-20260925-154718-f06443] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tra42b32-r3-replay-control-20260925-154718-f06443] stderr: context canceled
```
