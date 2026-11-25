# [ts7 7.0.2] hover differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-hover-lost-hover-feed64`, signature `ts7|r6_crossimpl|hover:lost`, case family `hover`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/hover` on `app/src/formState.tsx` line 2, column 13 (LSP position {line: 1, character: 12}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"import useForm"
```

Actual:

```json
null
```

Project file `app/src/formState.tsx`:

```
   1 | import React from 'react';
   2 | import { useForm, ValidationMode } from 'react-hook-form';
   3 | import { useParams } from 'react-router-dom';
     ...
   5 | let renderCounter = 0;
     ...
   7 | const FormState = () => {
   8 |   const { mode } = useParams();
   9 |   const {
  10 |     register,
  11 |     handleSubmit,
  12 |     formState: {
  13 |       dirtyFields,
  14 |       isSubmitted,
  15 |       submitCount,
  16 |       touchedFields,
  17 |       isDirty,
  18 |       isSubmitting,
  19 |       isSubmitSuccessful,
  20 |       isValid,
  21 |     },
  22 |     reset,
  23 |   } = useForm<{
  24 |     firstName: string;
  25 |     lastName: string;
  26 |     select: string;
  27 |     radio: string | null;
  28 |     checkbox: boolean;
  29 |     ['checkbox-checked']: boolean;
  30 |   }>({
  31 |     mode: mode as keyof ValidationMode,
  32 |     defaultValues: {
  33 |       firstName: '',
  34 |       lastName: '',
  35 |       select: '',
  36 |       checkbox: false,
  37 |       radio: null,
  38 |       'checkbox-checked': true,
  39 |     },
  40 |   });
     ...
  42 |   renderCounter++;
     ...
  44 |   return (
  45 |     <form
  46 |       onSubmit={handleSubmit((d) => {
  47 |         console.log(d);
  48 |       })}
  49 |     >
  50 |       <input
  51 |         {...register('firstName', { required: true })}
  52 |         placeholder="firstName"
  53 |       />
  54 |       <input
  55 |         {...register('lastName', { required: true })}
  56 |         placeholder="lastName"
  57 |       />
  58 |       <div id="state">
  59 |         {JSON.stringify({
  60 |           isSubmitted,
  61 |           submitCount,
  62 |           isDirty,
  63 |           isSubmitting,
  64 |           isSubmitSuccessful,
  65 |           isValid,
  66 |           touched: Object.keys(touchedFields),
  67 |           dirty: Object.keys(dirtyFields),
  68 |         })}
  69 |       </div>
  70 |       <select {...register('select')} defaultValue="test">
  71 |         <option value="">Select</option>
  72 |         <option value="test">test</option>
  73 |         <option value="test1">test1</option>
  74 |         <option value="test2">test3</option>
  75 |       </select>
     ...
  77 |       <input type="radio" {...register('radio')} />
     ...
  79 |       <input type="checkbox" {...register('checkbox')} />
  80 |       <input type="checkbox" {...register('checkbox-checked')} />
  81 |       <button id="submit">Submit</button>
  82 |       <button type="button" onClick={() => reset()} id="resetForm">
  83 |         Reset
  84 |       </button>
  85 |       <div id="renderCount">{renderCounter}</div>
  86 |     </form>
  87 |   );
  88 | };
     ...
  90 | export default FormState;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-hover-lost-hover-feed64/repro.json
```

## Evidence and reduction

- representative f1084e14ba1e-v05: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#3605](https://github.com/microsoft/typescript-go/issues/3605) Missing generic param displayed in hover (closed, 2026-04-25, 0 comments)
- [microsoft/typescript-go#3411](https://github.com/microsoft/typescript-go/issues/3411) Missing generic type description in hover (closed, 2026-04-15, 2 comments)
- [microsoft/typescript-go#3607](https://github.com/microsoft/typescript-go/issues/3607) Missing hover for nullable method in type and interface (closed, 2026-04-25, 1 comments)
- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#3422](https://github.com/microsoft/typescript-go/issues/3422) Wrong function signature and missing invoking description in hover (closed, 2026-04-16, 0 comments)
- [microsoft/typescript-go#4677](https://github.com/microsoft/typescript-go/issues/4677) JSDoc (TSDoc ???) is not shown for object literal properties on hover (closed, 2026-07-20, 1 comments)
- [microsoft/typescript-go#4758](https://github.com/microsoft/typescript-go/issues/4758) disableSourceOfProjectReferenceRedirect causes lodash per-method submodule import to resolve to the wrong function (closed, 2026-07-27, 7 comments)
- [microsoft/typescript-go#4683](https://github.com/microsoft/typescript-go/issues/4683) Generic type parameter inferred differently across two call-site positions with opposite variance (narrow type vs union) (closed, 2026-07-20, 2 comments)
- queries: `hover missing repo:microsoft/typescript-go is:issue`; `hover "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trfeed64-r6-replay-test-baseline-20260925-171506-0e6315] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trfeed64-r6-replay-test-baseline-20260925-171506-0e6315] stderr: context canceled
[ts7-7.0.2-trfeed64-r6-replay-test-control-20260925-171521-5ddfd7] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trfeed64-r6-replay-test-control-20260925-171521-5ddfd7] stderr: context canceled
```
