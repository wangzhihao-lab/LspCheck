# [ts6 6.0.3] mutation:M1 edit is not valid (diagnostics:extra:2339,6133)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2339-6133-mutation-m1-4cd363`, signature `ts6|r4_edits|diagnostics:extra:2339,6133`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `vadimdemedes/ink@02ae1e59e7c2` (corpus, commit 02ae1e59e7c288e971616100c4c11bcca6b5761b), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/components/FocusContext.ts`
3. textDocument/didChange: `change src/components/FocusContext.ts (0, 0)-(1, 0) ""`
4. textDocument/didChange: `change src/components/FocusContext.ts (31, 0)-(31, 0) "function createContext<T>(arg0: { activeId: undefined; add(): void; remove(): void; activate(): void; deactivate(): void; enableFocus(): void; disableFocus(): void; focusNext(): void; focusPrevious(): void; focus(): void; }) {\n\tthrow new Error(\"Function not implemented.\");\n}\n\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/dom.ts`, `test/colon-colors.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `src/components/FocusContext.ts` line 16, column 22 (LSP position {line: 15, character: 21}) (M1:quickfix-errors:Add missing function declaration 'createContext'); compare with the same query in a fresh session on the same content (expected).

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
  "typescript",
  "Property 'displayName' does not exist on type 'void'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "6133",
  "typescript",
  "'T' is declared but its value is never read."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "6133",
  "typescript",
  "'arg0' is declared but its value is never read."
 ]
]
```

Project file `src/components/FocusContext.ts`:

```
   1 | import {createContext} from 'react';
     ...
   3 | export type Props = {
   4 | 	readonly activeId?: string;
   5 | 	readonly add: (id: string, options: {autoFocus: boolean}) => void;
   6 | 	readonly remove: (id: string) => void;
   7 | 	readonly activate: (id: string) => void;
   8 | 	readonly deactivate: (id: string) => void;
   9 | 	readonly enableFocus: () => void;
  10 | 	readonly disableFocus: () => void;
  11 | 	readonly focusNext: () => void;
  12 | 	readonly focusPrevious: () => void;
  13 | 	readonly focus: (id: string) => void;
  14 | };
     ...
  16 | // eslint-disable-next-line @typescript-eslint/naming-convention
  17 | const FocusContext = createContext<Props>({
  18 | 	activeId: undefined,
  19 | 	add() {},
  20 | 	remove() {},
  21 | 	activate() {},
  22 | 	deactivate() {},
  23 | 	enableFocus() {},
  24 | 	disableFocus() {},
  25 | 	focusNext() {},
  26 | 	focusPrevious() {},
  27 | 	focus() {},
  28 | });
     ...
  30 | FocusContext.displayName = 'InternalFocusContext';
     ...
  32 | export default FocusContext;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r4-diagnostics-extra-2339-6133-mutation-m1-4cd363/repro.json
```

## Evidence and reduction

- representative 634d2a95e4c7-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 6.034 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 1

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
