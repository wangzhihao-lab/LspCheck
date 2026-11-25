# [ts7 7.0.2] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-highlightvsreferences-gained-c-9f16d3`, signature `ts7|r3_routes|highlightVsReferences:gained`, case family `c`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `examples/V7/validationOnFieldBlur.tsx` at line 38, column 11 (LSP position {line: 37, character: 10}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  37,
  8,
  37,
  13
 ],
 [
  43,
  8,
  43,
  14
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
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r3-highlightvsreferences-gained-c-9f16d3/repro.json
```

## Evidence and reduction

- representative 6a9eee1ad5c6-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects ChromeDevTools/chrome-devtools-mcp@2250cdcde4aa, react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4262](https://github.com/microsoft/typescript-go/issues/4262) Non-deterministic `TS2305 "has no exported member"` errors across project references with `--emitDeclarationOnly` (closed, 2026-06-10, 8 comments)
- [microsoft/typescript-go#4614](https://github.com/microsoft/typescript-go/issues/4614) `tsc -b --watch` takes tens of seconds to start watching on a large project-references solution (`computeDesiredWatches` is O(files × dirs)) (closed, 2026-07-13, 2 comments)
- [microsoft/typescript-go#4334](https://github.com/microsoft/typescript-go/issues/4334) No "Find file references" upon clicking on typescript file (closed, 2026-06-16, 1 comments)
- [microsoft/typescript-go#4425](https://github.com/microsoft/typescript-go/issues/4425) Panic (nil deref) in checker.GetBaseTypes for plain type references (e.g. `string[]`) via the API (closed, 2026-06-24, 2 comments)
- [microsoft/typescript-go#3596](https://github.com/microsoft/typescript-go/issues/3596) TS2883 regression in --build with project references on inferred export from referenced package (closed, 2026-04-24, 2 comments)
- [microsoft/typescript-go#2473](https://github.com/microsoft/typescript-go/issues/2473) Autocompletion panics (closed, 2026-01-12, 9 comments)
- [microsoft/typescript-go#3508](https://github.com/microsoft/typescript-go/issues/3508) Corsa no longer emits the TS-1 internal diagnostic about pre-emit/post-emit diagnostic count mismatches (closed, 2026-04-22, 2 comments)
- [microsoft/typescript-go#1328](https://github.com/microsoft/typescript-go/issues/1328) Declaration emit missing `declare const` for symbols imported from a `#subpath_import` (closed, 2025-07-01, 7 comments)
- queries: `references in:title repo:microsoft/typescript-go is:issue`; `highlight unexpected repo:microsoft/typescript-go is:issue`; `highlight references repo:microsoft/typescript-go is:issue`; `highlight inconsistent repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr9f16d3-r3-replay-baseline-20260925-155321-f9e4b4] stderr: context canceled
[ts7-7.0.2-tr9f16d3-r3-replay-control-20260925-155334-7cac8d] stderr: context canceled
```
