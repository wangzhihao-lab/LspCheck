# [ts7 7.0.2] diagnostics differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-diagnostics-moved-6133-diagnostics-5e7a2f`, signature `ts7|r6_crossimpl|diagnostics:moved:6133`, case family `diagnostics`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/diagnostic` on `examples/V7/validationOnFieldBlur.tsx` for the whole file; compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  0,
  26,
  0,
  "6133",
  "",
  ""
 ],
 [
  1,
  0,
  1,
  33,
  0,
  "6133",
  "",
  ""
 ],
 [
  12,
  20,
  12,
  24,
  0,
  "7006",
  "",
  ""
 ],
 [
  2,
  24,
  2,
  41,
  0,
  "2307",
  "",
  ""
 ],
 [
  38,
  33,
  38,
  44,
  0,
  "2322",
  "",
  ""
 ]
]
```

Actual:

```json
[
 [
  0,
  7,
  0,
  12,
  0,
  "6133",
  "",
  ""
 ],
 [
  1,
  7,
  1,
  15,
  0,
  "6133",
  "",
  ""
 ],
 [
  12,
  20,
  12,
  24,
  0,
  "7006",
  "",
  ""
 ],
 [
  2,
  24,
  2,
  41,
  0,
  "2307",
  "",
  ""
 ],
 [
  38,
  33,
  38,
  44,
  0,
  "2322",
  "",
  ""
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-diagnostics-moved-6133-diagnostics-5e7a2f/repro.json
```

## Evidence and reduction

- representative 33f1bc8d2cec-v03: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4745](https://github.com/microsoft/typescript-go/issues/4745) Native API syntactic diagnostics omit start and length (closed, 2026-07-26, 2 comments)
- [microsoft/typescript-go#4827](https://github.com/microsoft/typescript-go/issues/4827) Generic type argument inferred from the wrong inference slot (cyclic union-of-intersections); larger programs show scheduling-dependent diagnostics (closed, 2026-08-04, 1 comments)
- [microsoft/typescript-go#4719](https://github.com/microsoft/typescript-go/issues/4719) tsgo reports type errors in external-library (node_modules) source files that tsc suppresses (closed, 2026-07-23, 2 comments)
- [microsoft/typescript-go#4129](https://github.com/microsoft/typescript-go/issues/4129) tsgo reports compiler-option diagnostics even when syntactic errors exist (closed, 2026-05-31, 0 comments)
- [microsoft/typescript-go#4373](https://github.com/microsoft/typescript-go/issues/4373) Project-reference redirect fails for directory (`index.ts`) subpaths of symlinked packages (closed, 2026-06-19, 0 comments)
- queries: `diagnostics "wrong range" repo:microsoft/typescript-go is:issue`; `diagnostics "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr5e7a2f-r6-replay-test-baseline-20260925-170841-bfdcb8] stderr: context canceled
[ts7-7.0.2-tr5e7a2f-r6-replay-test-control-20260925-170855-f473c0] stderr: context canceled
```
