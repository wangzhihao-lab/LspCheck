# [ts6 6.0.3] mutation:M3 edit is not valid (diagnostics:extra:2555)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2555-mutation-m3-8de4a9`, signature `ts6|r4_edits|diagnostics:extra:2555`, case family `mutation:M3`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `umami-software/umami@12ad773d621f` (corpus, commit 12ad773d621f51da6e81e9031b458efe56be3e8e), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/app/(main)/settings/websites/WebsitesSettingsPage.tsx`
3. textDocument/didChange: `change src/app/(main)/settings/websites/WebsitesSettingsPage.tsx (11, 30)-(11, 45) ""`
4. textDocument/didChange: `change src/app/(main)/settings/websites/WebsitesSettingsPage.tsx (7, 11)-(7, 19) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/app/(main)/websites/[websiteId]/(reports)/funnels/page.tsx`, `tests/api/helpers/constants.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `src/app/(main)/settings/websites/WebsitesSettingsPage.tsx` line 8, column 14 (LSP position {line: 7, character: 13}) (M3:quickfix-errors:Remove unused declaration for: 'labels'); compare with the same query in a fresh session on the same content (expected).

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
  "2555",
  "typescript",
  "Expected at least 1 arguments, but got 0."
 ]
]
```

Project file `src/app/(main)/settings/websites/WebsitesSettingsPage.tsx`:

```
   1 | 'use client';
   2 | import { Column } from '@umami/react-zen';
   3 | import { WebsitesDataTable } from '@/app/(main)/websites/WebsitesDataTable';
   4 | import { SectionHeader } from '@/components/common/SectionHeader';
   5 | import { useMessages } from '@/components/hooks';
     ...
   7 | export function WebsitesSettingsPage({ teamId }: { teamId: string }) {
   8 |   const { t, labels } = useMessages();
     ...
  10 |   return (
  11 |     <Column gap>
  12 |       <SectionHeader title={t(labels.websites)} />
  13 |       <WebsitesDataTable teamId={teamId} />
  14 |     </Column>
  15 |   );
  16 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r4-diagnostics-extra-2555-mutation-m3-8de4a9/repro.json
```

## Evidence and reduction

- representative 8d087bf282e1-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 15.037 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects umami-software/umami@12ad773d621f, timings settled, seeds 2

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
