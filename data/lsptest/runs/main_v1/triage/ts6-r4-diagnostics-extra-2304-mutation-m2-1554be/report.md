# [ts6 6.0.3] mutation:M2 edit is not valid (diagnostics:extra:2304)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2304-mutation-m2-1554be`, signature `ts6|r4_edits|diagnostics:extra:2304`, case family `mutation:M2`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open app/src/main.tsx`
3. textDocument/didChange: `change app/src/main.tsx (6, 0)-(6, 4) "rot"`
4. textDocument/didChange: `change app/src/main.tsx (5, 0)-(6, 0) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `examples/V7/validationOnFieldBlur.tsx`, `src/logic/skipValidation.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `app/src/main.tsx` line 6, column 7 (LSP position {line: 5, character: 6}) (M2:quickfix-errors:Remove unused declaration for: 'root'); compare with the same query in a fresh session on the same content (expected).

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
  "2304",
  "typescript",
  "Cannot find name 'rot'."
 ]
]
```

Project file `app/src/main.tsx`:

```
   1 | import React from 'react';
   2 | import ReactDOM from 'react-dom/client';
   3 | import App from './app';
     ...
   5 | const rootElement = document.getElementById('root')!;
   6 | const root = ReactDOM.createRoot(rootElement);
   7 | root.render(<App />);
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-2304-mutation-m2-1554be/repro.json
```

## Evidence and reduction

- representative 0081742f7574-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 6.611 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 1

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
