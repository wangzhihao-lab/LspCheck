# [ts7 7.0.2] mutation:M1 edit is not valid (diagnostics:extra:2339,2349,2352)

Draft for the author (not filed). Group `ts7-r4-diagnostics-extra-2339-2349-2352-mutation-m1-47c762`, signature `ts7|r4_edits|diagnostics:extra:2339,2349,2352`, case family `mutation:M1`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `ChatGPTNextWeb/NextChat@defdcdb55d85` (corpus, commit defdcdb55d850cd12c4c657eb83729fd66e215c0), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open app/command.ts`
3. textDocument/didChange: `change app/command.ts (1, 0)-(2, 0) ""`
4. textDocument/didChange: `change app/command.ts (2, 0)-(2, 0) "import { useSearchParams } from \"next/navigation\";\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `app/components/mask.tsx`, `app/utils/store.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `app/command.ts` line 14, column 43 (LSP position {line: 13, character: 42}) (M1:quickfix-errors:Add import from "next/navigation"); compare with the same query in a fresh session on the same content (expected).

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
  "Property 'delete' does not exist on type '[string, string]'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2349",
  "ts",
  "This expression is not callable. Type '[string, string]' has no call signatures."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2352",
  "ts",
  "Conversion of type 'number' to type 'keyof Commands' may be a mistake because neither type sufficiently overlaps with the other. If this was intentional, convert the expression to 'unknown' first."
 ]
]
```

Project file `app/command.ts`:

```
   1 | import { useEffect } from "react";
   2 | import { useSearchParams } from "react-router-dom";
   3 | import Locale from "./locales";
     ...
   5 | type Command = (param: string) => void;
   6 | interface Commands {
   7 |   fill?: Command;
   8 |   submit?: Command;
   9 |   mask?: Command;
  10 |   code?: Command;
  11 |   settings?: Command;
  12 | }
     ...
  14 | export function useCommand(commands: Commands = {}) {
  15 |   const [searchParams, setSearchParams] = useSearchParams();
     ...
  17 |   useEffect(() => {
  18 |     let shouldUpdate = false;
  19 |     searchParams.forEach((param, name) => {
  20 |       const commandName = name as keyof Commands;
  21 |       if (typeof commands[commandName] === "function") {
  22 |         commands[commandName]!(param);
  23 |         searchParams.delete(name);
  24 |         shouldUpdate = true;
  25 |       }
  26 |     });
     ...
  28 |     if (shouldUpdate) {
  29 |       setSearchParams(searchParams);
  30 |     }
  31 |     // eslint-disable-next-line react-hooks/exhaustive-deps
  32 |   }, [searchParams, commands]);
  33 | }
     ...
  35 | interface ChatCommands {
  36 |   new?: Command;
  37 |   newm?: Command;
  38 |   next?: Command;
  39 |   prev?: Command;
  40 |   clear?: Command;
  41 |   fork?: Command;
  42 |   del?: Command;
  43 | }
     ...
  45 | // Compatible with Chinese colon character "："
  46 | export const ChatCommandPrefix = /^[:：]/;
     ...
  48 | export function useChatCommand(commands: ChatCommands = {}) {
  49 |   function extract(userInput: string) {
  50 |     const match = userInput.match(ChatCommandPrefix);
  51 |     if (match) {
  52 |       return userInput.slice(1) as keyof ChatCommands;
  53 |     }
  54 |     return userInput as keyof ChatCommands;
  55 |   }
     ...
  57 |   function search(userInput: string) {
  58 |     const input = extract(userInput);
  59 |     const desc = Locale.Chat.Commands;
  60 |     return Object.keys(commands)
  61 |       .filter((c) => c.startsWith(input))
  62 |       .map((c) => ({
  63 |         title: desc[c as keyof ChatCommands],
  64 |         content: ":" + c,
  65 |       }));
  66 |   }
     ...
  68 |   function match(userInput: string) {
  69 |     const command = extract(userInput);
  70 |     const matched = typeof commands[command] === "function";
     ...
  72 |     return {
  73 |       matched,
  74 |       invoke: () => matched && commands[command]!(userInput),
  75 |     };
  76 |   }
     ...
  78 |   return { match, search };
  79 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r4-diagnostics-extra-2339-2349-2352-mutation-m1-47c762/repro.json
```

## Evidence and reduction

- representative 5b02f641ff24-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 15.509 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, timings settled, seeds 2

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
[ts7-7.0.2-tr47c762-r4-replay-baseline-20260925-160359-3c9f96] stderr: context canceled
[ts7-7.0.2-tr47c762-r4-replay-case-20260925-160319-1a54a6] stderr: context canceled
[ts7-7.0.2-tr47c762-r4-replay-control-20260925-160434-11519d] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr47c762-r4-replay-control-20260925-160434-11519d] stderr: context canceled
```
