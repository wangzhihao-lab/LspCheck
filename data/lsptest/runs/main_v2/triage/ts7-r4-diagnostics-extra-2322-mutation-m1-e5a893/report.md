# [ts7 7.0.2] mutation:M1 edit is not valid (diagnostics:extra:2322)

Draft for the author (not filed). Group `ts7-r4-diagnostics-extra-2322-mutation-m1-e5a893`, signature `ts7|r4_edits|diagnostics:extra:2322`, case family `mutation:M1`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Gitlawb/openclaude@5cd11336caea` (corpus, commit 5cd11336caeaf2023ca1e02e5975c761cfc585fe), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/commands/privacy-settings/index.ts`
3. textDocument/didChange: `change src/commands/privacy-settings/index.ts (0, 0)-(1, 0) ""`
4. textDocument/didChange: `change src/commands/privacy-settings/index.ts (0, 9)-(0, 9) "Command } from '@commander-js/extra-typings';\nimport { "`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/components/PromptInput/Notifications.tsx`, `src/utils/log.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `src/commands/privacy-settings/index.ts` line 11, column 13 (LSP position {line: 10, character: 12}) (M1:quickfix-errors:Add import from "@commander-js/extra-typings"); compare with the same query in a fresh session on the same content (expected).

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
  "2322",
  "ts",
  "Type 'string' is not assignable to type '{ (str: string): Command<[], {}>; (): string; }'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2322",
  "ts",
  "Type 'string' is not assignable to type '{ (str: string): Command<[], {}>; (str: string, argsDescription: Record<string, string>): Command<[], {}>; (): string; }'."
 ]
]
```

Project file `src/commands/privacy-settings/index.ts`:

```
   1 | import type { Command } from '../../commands.js'
   2 | import { isConsumerSubscriber } from '../../utils/auth.js'
     ...
   4 | const privacySettings = {
   5 |   type: 'local-jsx',
   6 |   name: 'privacy-settings',
   7 |   description: 'View and update your privacy settings',
   8 |   isEnabled: () => {
   9 |     return isConsumerSubscriber()
  10 |   },
  11 |   load: () => import('./privacy-settings.js'),
  12 | } satisfies Command
     ...
  14 | export default privacySettings
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r4-diagnostics-extra-2322-mutation-m1-e5a893/repro.json
```

## Evidence and reduction

- representative 727adbc07eab-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 13.538 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Gitlawb/openclaude@5cd11336caea, timings settled, seeds 1

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
[ts7-7.0.2-tre5a893-r4-replay-baseline-20261118-215640-bf9a1d] stderr: context canceled
[ts7-7.0.2-tre5a893-r4-replay-case-20261118-215614-3020b3] stderr: context canceled
[ts7-7.0.2-tre5a893-r4-replay-control-20261118-215704-86d7e3] stderr: context canceled
```
