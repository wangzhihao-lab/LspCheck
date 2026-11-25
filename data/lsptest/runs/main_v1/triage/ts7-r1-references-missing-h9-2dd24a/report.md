# [ts7 7.0.2] references misses entries after edit inside a workspace window

Draft for the author (not filed). Group `ts7-r1-references-missing-h9-2dd24a`, signature `ts7|r1_history|references:missing`, case family `H9`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/V7/disableNativeValidation.tsx`
3. textDocument/didOpen: `open src/__tests__/logic/getValidateError.test.ts`
4. textDocument/didOpen: `open src/__tests__/logic/skipValidation.test.ts`
5. textDocument/didOpen: `open app/src/form.tsx`
6. textDocument/didChange: `change app/src/form.tsx (1, 14)-(1, 25) ""`
7. Timing: wait until the server is idle after every step.
8. Query `textDocument/references` on `src/__tests__/logic/getValidateError.test.ts` line 2, column 15 (LSP position {line: 1, character: 14}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/__tests__/logic/getValidateError.test.ts",
  1,
  18,
  1,
  34
 ],
 [
  "src/form.tsx",
  6,
  7,
  6,
  11
 ],
 [
  "src/form.tsx",
  38,
  15,
  38,
  19
 ],
 [
  "src/form.tsx",
  44,
  14,
  44,
  18
 ],
 [
  "src/form.tsx",
  46,
  16,
  46,
  20
 ],
 [
  "src/utils/noop.ts",
  0,
  24,
  0,
  28
 ]
]
```

Actual:

```json
[
 [
  "src/__tests__/logic/getValidateError.test.ts",
  1,
  18,
  1,
  34
 ]
]
```

Project file `src/__tests__/logic/getValidateError.test.ts`:

```
   1 | import getValidateError from '../../logic/getValidateError';
   2 | import noop from '../../utils/noop';
     ...
   4 | describe('getValidateError', () => {
   5 |   it('should return field error in correct format', () => {
   6 |     expect(
   7 |       getValidateError(
   8 |         'This is a required field',
   9 |         {
  10 |           name: 'test1',
  11 |           value: '',
  12 |         },
  13 |         'required',
  14 |       ),
  15 |     ).toEqual({
  16 |       type: 'required',
  17 |       message: 'This is a required field',
  18 |       ref: {
  19 |         name: 'test1',
  20 |         value: '',
  21 |       },
  22 |     });
     ...
  24 |     expect(
  25 |       getValidateError(
  26 |         false,
  27 |         {
  28 |           name: 'test1',
  29 |           value: '',
  30 |         },
  31 |         'required',
  32 |       ),
  33 |     ).toEqual({
  34 |       type: 'required',
  35 |       message: '',
  36 |       ref: {
  37 |         name: 'test1',
  38 |         value: '',
  39 |       },
  40 |     });
  41 |   });
     ...
  43 |   it('should return undefined when called with non string result', () => {
  44 |     expect(getValidateError(undefined, noop)).toBeUndefined();
  45 |   });
  46 | });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r1-references-missing-h9-2dd24a/repro.json
```

## Evidence and reduction

- representative d682da8dbdea-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 14 -> 5 (6 probes, 190.331 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 3

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4262](https://github.com/microsoft/typescript-go/issues/4262) Non-deterministic `TS2305 "has no exported member"` errors across project references with `--emitDeclarationOnly` (closed, 2026-06-10, 8 comments)
- [microsoft/typescript-go#4230](https://github.com/microsoft/typescript-go/issues/4230) Behavior difference: tsgo no longer infer variadic `args` type when `arguments[...]` is referenced inside plain js function body (closed, 2026-06-06, 3 comments)
- [microsoft/typescript-go#3787](https://github.com/microsoft/typescript-go/issues/3787) tsgo and tsc diverge on incomplete composite-ref declaration cache: TS2305 vs filterable TS6305 (closed, 2026-05-09, 2 comments)
- [microsoft/typescript-go#2666](https://github.com/microsoft/typescript-go/issues/2666) `tsgo --build` fails to invalidate incremental cache after dependency update (closed, 2026-02-04, 3 comments)
- [microsoft/typescript-go#3610](https://github.com/microsoft/typescript-go/issues/3610) API: additional Checker methods for transpiler consumers (follow-up to #3403) (closed, 2026-04-25, 2 comments)
- [microsoft/typescript-go#2557](https://github.com/microsoft/typescript-go/issues/2557) Suggestions freeze and stop working until I close and open the file again (closed, 2026-01-21, 11 comments)
- [microsoft/typescript-go#2615](https://github.com/microsoft/typescript-go/issues/2615) Stack overflow in handleDtsMayChangeOfFileAndExportsOfFile with incremental build cache (closed, 2026-01-29, 2 comments)
- [microsoft/typescript-go#2881](https://github.com/microsoft/typescript-go/issues/2881) [ServerErrors][JavaScript] linux-x64-7.0.0-dev.20260223.1 vs  (closed, 2026-02-23, 3 comments)
- queries: `references missing repo:microsoft/typescript-go is:issue`; `references stale repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr2dd24a-replay-baseline-20260925-154537-c75925] stderr: context canceled
[ts7-7.0.2-tr2dd24a-replay-control-20260925-154537-61effb] stderr: context canceled
[ts7-7.0.2-tr2dd24a-replay-history-20260925-154550-cd9973] stderr: context canceled
```
