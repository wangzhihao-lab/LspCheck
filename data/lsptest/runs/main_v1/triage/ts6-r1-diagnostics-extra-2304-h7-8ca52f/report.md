# [ts6 6.0.3] diagnostics adds 2304 after interleaving of h1-h6, h8, h9

Draft for the author (not filed). Group `ts6-r1-diagnostics-extra-2304-h7-8ca52f`, signature `ts6|r1_history|diagnostics:extra:2304`, case family `H7`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/V7/validationOnFieldBlur.tsx`
3. request: `request examples/V7/validationOnFieldBlur.tsx typeDefinition at (9, 9)`
4. request: `request examples/V7/validationOnFieldBlur.tsx hover at (37, 10)`
5. Timing: send the steps 0 ms apart without waiting, then wait until idle.
6. textDocument/didOpen `app/src/main.tsx`, `src/logic/skipValidation.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/diagnostic` on `examples/V7/validationOnFieldBlur.tsx` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  0,
  26,
  4,
  "6133",
  "typescript",
  "'React' is declared but its value is never read."
 ],
 [
  1,
  0,
  1,
  33,
  4,
  "6133",
  "typescript",
  "'ReactDOM' is declared but its value is never read."
 ],
 [
  2,
  24,
  2,
  41,
  1,
  "2307",
  "typescript",
  "Cannot find module 'react-hook-form' or its corresponding type declarations."
 ],
 [
  12,
  20,
  12,
  24,
  1,
  "7006",
  "typescript",
  "Parameter 'data' implicitly has an 'any' type."
 ],
 [
  38,
  33,
  38,
  44,
  1,
  "2322",
  "typescript",
  "Type '{ children: string; htmlFor: string; placeholder: string; }' is not assignable to type 'DetailedHTMLProps<LabelHTMLAttributes<HTMLLabelElement>, HTMLLabelElement>'. Property 'placeholder' does not exist on type 'DetailedHTMLProps<LabelHTMLAttributes<HTMLLabelElement>, HTMLLabelElement>'."
 ]
]
```

Actual:

```json
[
 [
  0,
  0,
  0,
  26,
  4,
  "6133",
  "typescript",
  "'React' is declared but its value is never read."
 ],
 [
  1,
  0,
  1,
  33,
  4,
  "6133",
  "typescript",
  "'ReactDOM' is declared but its value is never read."
 ],
 [
  2,
  24,
  2,
  41,
  1,
  "2307",
  "typescript",
  "Cannot find module 'react-hook-form' or its corresponding type declarations."
 ],
 [
  12,
  20,
  12,
  24,
  1,
  "7006",
  "typescript",
  "Parameter 'data' implicitly has an 'any' type."
 ],
 [
  37,
  9,
  37,
  12,
  1,
  "2304",
  "typescript",
  "Cannot find name 'div'."
 ],
 [
  38,
  33,
  38,
  44,
  1,
  "2322",
  "typescript",
  "Type '{ children: string; htmlFor: string; placeholder: string; }' is not assignable to type 'DetailedHTMLProps<LabelHTMLAttributes<HTMLLabelElement>, HTMLLabelElement>'. Property 'placeholder' does not exist on type 'DetailedHTMLProps<LabelHTMLAttributes<HTMLLabelElement>, HTMLLabelElement>'."
 ]
]
```

Project file `examples/V7/validationOnFieldBlur.tsx`:

```
   1 | import React from 'react';
   2 | import ReactDOM from 'react-dom';
   3 | import { useForm } from 'react-hook-form';
     ...
   5 | export default function App() {
   6 |   const {
   7 |     register,
   8 |     formState: { errors },
   9 |     handleSubmit,
  10 |   } = useForm({
  11 |     mode: 'onBlur',
  12 |   });
  13 |   const onSubmit = (data) => {
  14 |     alert(JSON.stringify(data));
  15 |   };
     ...
  17 |   return (
  18 |     <div className="App">
  19 |       <form onSubmit={handleSubmit(onSubmit)}>
  20 |         <div>
  21 |           <label htmlFor="firstName">First Name</label>
  22 |           <input
  23 |             placeholder="bill"
  24 |             {...register('firstName', { required: true })}
  25 |           />
  26 |           {errors.firstName && 'This is required'}
  27 |         </div>
     ...
  29 |         <div>
  30 |           <label htmlFor="lastName">Last Name</label>
  31 |           <input
  32 |             placeholder="luo"
  33 |             {...register('lastName', { required: true })}
  34 |           />
  35 |           {errors.lastName && 'This is required'}
  36 |         </div>
     ...
  38 |         <div>
  39 |           <label htmlFor="email" placeholder="bluebill1049@hotmail.com">
  40 |             Email
  41 |           </label>
  42 |           <input {...register('email', { required: true })} />
  43 |           {errors.email && 'This is required'}
  44 |         </div>
  45 |         <button type="submit">Submit</button>
  46 |       </form>
  47 |     </div>
  48 |   );
  49 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-diagnostics-extra-2304-h7-8ca52f/repro.json
```

## Evidence and reduction

- representative 43c648d37a2b-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 11 -> 3 (15 probes, 245.715 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings race0, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#815](https://github.com/typescript-language-server/typescript-language-server/issues/815) TSServer >=4.1.0 never publishes textDocument/publishDiagnostics event (NeoVim) (closed, 2023-11-16, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#724](https://github.com/typescript-language-server/typescript-language-server/issues/724) "typescript.inlayHints.includeInlayParameterNameHints": "all" breaks inference with dangling commas (closed, 2023-05-15, 7 comments)
- [typescript-language-server/typescript-language-server#327](https://github.com/typescript-language-server/typescript-language-server/issues/327) configurable debouncing delays (open, 2021-12-08, 5 comments)
- [typescript-language-server/typescript-language-server#35](https://github.com/typescript-language-server/typescript-language-server/issues/35) Clear diagnostics when closing file (closed, 2018-04-18, 0 comments)
- [microsoft/TypeScript#64405](https://github.com/microsoft/TypeScript/issues/64405) Incremental check emits locationless TS2589 after a comment-only edit in TypeScript 7 (closed, 2026-09-23, 6 comments)
- queries: `"after edit" in:title repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics extra repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics "after edit" repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics stale repo:typescript-language-server/typescript-language-server is:issue`; `"after edit" in:title repo:microsoft/TypeScript is:issue`; `diagnostics extra repo:microsoft/TypeScript is:issue`; `diagnostics "after edit" repo:microsoft/TypeScript is:issue`; `diagnostics stale repo:microsoft/TypeScript is:issue`
