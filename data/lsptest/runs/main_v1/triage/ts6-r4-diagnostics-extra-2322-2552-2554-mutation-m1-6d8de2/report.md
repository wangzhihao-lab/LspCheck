# [ts6 6.0.3] mutation:M1 edit is not valid (diagnostics:extra:2322,2552,2554)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2322-2552-2554-mutation-m1-6d8de2`, signature `ts6|r4_edits|diagnostics:extra:2322,2552,2554`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/core/shared/skill-generation.ts`
3. textDocument/didChange: `change src/core/shared/skill-generation.ts (35, 36)-(36, 26) ""`
4. textDocument/didChange: `change src/core/shared/skill-generation.ts (103, 27)-(103, 35) "Installed"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/telemetry/index.ts`, `test/commands/store-git.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `src/core/shared/skill-generation.ts` line 104, column 21 (LSP position {line: 103, character: 20}) (M1:quickfix-errors:Change spelling to 'resolveInstalledWorkflows'); compare with the same query in a fresh session on the same content (expected).

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
  "typescript",
  "Type '{ template: { instructions: ReadonlySet<string>; name: string; description: string; license?: string | undefined; compatibility?: string | undefined; metadata?: Record<string, string> | undefined; }; dirName: string; workflowId: string; }[]' is not assignable to type 'SkillTemplateEntry[]'. Type '{ template: { instructions: ReadonlySet<string>; name: string; description: string; license?: string; compatibility?: string; metadata?: Record<string, string>; }; dirName: string; workflowId: string; }' is not assignable to type 'SkillTemplateEntry'. The types of 'template.instructions' are incompatible between these types. Type 'ReadonlySet<string>' is not assignable to type 'string'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2552",
  "typescript",
  "Cannot find name 'resolveOptionalWorkflows'. Did you mean 'resolveInstalledWorkflows'?"
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2554",
  "typescript",
  "Expected 0-1 arguments, but got 2."
 ]
]
```

Project file `src/core/shared/skill-generation.ts`:

```
  33 | } from '../templates/skill-templates.js';
  34 | import type { CommandContent } from '../command-generation/index.js';
  35 | import {
  36 |   assertWorkflowConditionalsResolved,
  37 |   resolveOptionalWorkflows,
  38 | } from '../templates/optional-workflow.js';
  39 | import { ALL_WORKFLOWS } from '../profiles.js';
     ...
 101 |   return selected.map(entry => ({
 102 |     ...entry,
 103 |     template: {
 104 |       ...entry.template,
 105 |       instructions: resolveOptionalWorkflows(entry.template.instructions, installed),
 106 |     },
 107 |   }));
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-2322-2552-2554-mutation-m1-6d8de2/repro.json
```

## Evidence and reduction

- representative 2fe2fd5714b0-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (1 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, timings settled, seeds 1

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
