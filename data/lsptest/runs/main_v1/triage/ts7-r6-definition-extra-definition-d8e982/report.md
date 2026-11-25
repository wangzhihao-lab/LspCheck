# [ts7 7.0.2] definition differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-definition-extra-definition-d8e982`, signature `ts7|r6_crossimpl|definition:extra`, case family `definition`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/definition` on `examples/V7/validationOnFieldBlur.tsx` line 1, column 10 (LSP position {line: 0, character: 9}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "node_modules/.pnpm/@types+react-dom@19.2.3_@types+react@19.2.17/node_modules/@types/react-dom/index.d.ts",
  8,
  15,
  8,
  22
 ],
 [
  "node_modules/.pnpm/@types+react@19.2.17/node_modules/@types/react/index.d.ts",
  69,
  18,
  69,
  23
 ]
]
```

Actual:

```json
[
 [
  "node_modules/.pnpm/@types+react-dom@19.2.3_@types+react@19.2.17/node_modules/@types/react-dom/index.d.ts",
  8,
  15,
  8,
  22
 ],
 [
  "node_modules/.pnpm/@types+react@19.2.17/node_modules/@types/react/index.d.ts",
  69,
  18,
  69,
  23
 ],
 [
  "node_modules/@types/react-dom/index.d.ts",
  8,
  15,
  8,
  22
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-definition-extra-definition-d8e982/repro.json
```

## Evidence and reduction

- representative 33f1bc8d2cec-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, vercel/hyper@30ec0a2a91de, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4000](https://github.com/microsoft/typescript-go/issues/4000) Make typedef exporting explicit (closed, 2026-05-20, 7 comments)
- [microsoft/typescript-go#4037](https://github.com/microsoft/typescript-go/issues/4037) TS2304 when a generic (@template) function JSDoc contains @overload (closed, 2026-05-23, 5 comments)
- [microsoft/typescript-go#4532](https://github.com/microsoft/typescript-go/issues/4532) [ServerErrors][TypeScript] main vs  (closed, 2026-07-03, 8 comments)
- [microsoft/typescript-go#3615](https://github.com/microsoft/typescript-go/issues/3615) Server stops responding after `Running scheduled diagnostics refresh` (closed, 2026-04-26, 0 comments)
- [microsoft/typescript-go#4863](https://github.com/microsoft/typescript-go/issues/4863) TS7 fails to emit types for `@type`-annotated functions when they reference externally-defined symbols (closed, 2026-08-10, 0 comments)
- [microsoft/typescript-go#4740](https://github.com/microsoft/typescript-go/issues/4740) Divergence from tsc: assignment accepted by 5.9/6.0 is rejected by `tsgo` (recursive DeepPartial + contravariant `this` + UnionToIntersection cycle, reduced from chart.js) (closed, 2026-07-25, 2 comments)
- [microsoft/typescript-go#4388](https://github.com/microsoft/typescript-go/issues/4388) Parameters not automatically filled for JSdoc comments (closed, 2026-06-22, 9 comments)
- queries: `definition extra repo:microsoft/typescript-go is:issue`; `definition "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trd8e982-r6-replay-test-baseline-20260925-164047-a4e829] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trd8e982-r6-replay-test-baseline-20260925-164047-a4e829] stderr: context canceled
[ts7-7.0.2-trd8e982-r6-replay-test-control-20260925-164111-5932b7] stderr: context canceled
```
