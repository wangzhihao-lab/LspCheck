# [ts6 6.0.3] mutation:M1 edit is not valid (diagnostics:extra:2678)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2678-mutation-m1-7b3f3b`, signature `ts6|r4_edits|diagnostics:extra:2678`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `reduxjs/redux@fb3bad6804d6` (corpus, commit fb3bad6804d651b8ae0e909f32765beb989ba6f8), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open test/helpers/reducers.ts`
3. textDocument/didChange: `change test/helpers/reducers.ts (5, 2)-(6, 2) ""`
4. textDocument/didChange: `change test/helpers/reducers.ts (94, 9)-(94, 11) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `test/typescript/enhancers.test-d.ts`, `website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `test/helpers/reducers.ts` line 95, column 10 (LSP position {line: 94, character: 9}) (M1:quickfix-errors:Change spelling to 'SUBSCRIBE_IN_MIDDLE'); compare with the same query in a fresh session on the same content (expected).

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
  "2678",
  "typescript",
  "Type '\"SUBSCRIBE_IN_MIDDLE\"' is not comparable to type '\"UNSUBSCRIBE_IN_MIDDLE\"'."
 ]
]
```

Project file `test/helpers/reducers.ts`:

```
   1 | import {
   2 |   ADD_TODO,
   3 |   DISPATCH_IN_MIDDLE,
   4 |   GET_STATE_IN_MIDDLE,
   5 |   SUBSCRIBE_IN_MIDDLE,
   6 |   UNSUBSCRIBE_IN_MIDDLE,
   7 |   THROW_ERROR
   8 | } from './actionTypes'
     ...
  10 | function id(state: { id: number }[]) {
  11 |   return (
  12 |     state.reduce((result, item) => (item.id > result ? item.id : result), 0) + 1
  13 |   )
  14 | }
     ...
  16 | export interface Todo {
  17 |   id: number
  18 |   text: string
  19 | }
  20 | export type TodoAction = { type: 'ADD_TODO'; text: string }
     ...
  22 | export function todos(state: Todo[] = [], action: TodoAction): Todo[] {
  23 |   switch (action.type) {
  24 |     case ADD_TODO:
  25 |       return [
  26 |         ...state,
  27 |         {
  28 |           id: id(state),
  29 |           text: action.text
  30 |         }
  31 |       ]
  32 |     default:
  33 |       return state
  34 |   }
  35 | }
     ...
  37 | export function todosReverse(state: Todo[] = [], action: TodoAction) {
  38 |   switch (action.type) {
  39 |     case ADD_TODO:
  40 |       return [
  41 |         {
  42 |           id: id(state),
  43 |           text: action.text
  44 |         },
  45 |         ...state
  46 |       ]
  47 |     default:
  48 |       return state
  49 |   }
  50 | }
     ...
  52 | export function dispatchInTheMiddleOfReducer(
  53 |   state = [],
  54 |   action: { type: 'DISPATCH_IN_MIDDLE'; boundDispatchFn: () => void }
  55 | ) {
  56 |   switch (action.type) {
  57 |     case DISPATCH_IN_MIDDLE:
  58 |       action.boundDispatchFn()
  59 |       return state
  60 |     default:
  61 |       return state
  62 |   }
  63 | }
     ...
  65 | export function getStateInTheMiddleOfReducer(
  66 |   state = [],
  67 |   action: { type: 'GET_STATE_IN_MIDDLE'; boundGetStateFn: () => void }
  68 | ) {
  69 |   switch (action.type) {
  70 |     case GET_STATE_IN_MIDDLE:
  71 |       action.boundGetStateFn()
  72 |       return state
  73 |     default:
  74 |       return state
  75 |   }
  76 | }
     ...
  78 | export function subscribeInTheMiddleOfReducer(
  79 |   state = [],
  80 |   action: { type: 'SUBSCRIBE_IN_MIDDLE'; boundSubscribeFn: () => void }
  81 | ) {
  82 |   switch (action.type) {
  83 |     case SUBSCRIBE_IN_MIDDLE:
  84 |       action.boundSubscribeFn()
  85 |       return state
  86 |     default:
  87 |       return state
  88 |   }
  89 | }
     ...
  91 | export function unsubscribeInTheMiddleOfReducer(
  92 |   state = [],
  93 |   action: { type: 'UNSUBSCRIBE_IN_MIDDLE'; boundUnsubscribeFn: () => void }
  94 | ) {
  95 |   switch (action.type) {
  96 |     case UNSUBSCRIBE_IN_MIDDLE:
  97 |       action.boundUnsubscribeFn()
  98 |       return state
  99 |     default:
 100 |       return state
 101 |   }
 102 | }
     ...
 104 | export function errorThrowingReducer(
 105 |   state = [],
 106 |   action: { type: 'THROW_ERROR' }
 107 | ) {
 108 |   switch (action.type) {
 109 |     case THROW_ERROR:
 110 |       throw new Error()
 111 |     default:
 112 |       return state
 113 |   }
 114 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r4-diagnostics-extra-2678-mutation-m1-7b3f3b/repro.json
```

## Evidence and reduction

- representative 96275a6b746e-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 3.95 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects reduxjs/redux@fb3bad6804d6, timings settled, seeds 2

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
