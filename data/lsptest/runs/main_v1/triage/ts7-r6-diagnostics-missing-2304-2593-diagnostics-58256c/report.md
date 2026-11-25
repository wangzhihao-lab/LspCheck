# [ts7 7.0.2] diagnostics differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-diagnostics-missing-2304-2593-diagnostics-58256c`, signature `ts7|r6_crossimpl|diagnostics:missing:2304,2593`, case family `diagnostics`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/diagnostic` on `src/__tests__/utils/objectHasFunction.test.ts` for the whole file; compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  12,
  4,
  12,
  10,
  0,
  "2304",
  "",
  ""
 ],
 [
  3,
  0,
  3,
  8,
  0,
  "2593",
  "",
  ""
 ],
 [
  4,
  2,
  4,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  5,
  4,
  5,
  10,
  0,
  "2304",
  "",
  ""
 ],
 [
  6,
  4,
  6,
  10,
  0,
  "2304",
  "",
  ""
 ]
]
```

Actual:

```json
[]
```

Project file `src/__tests__/utils/objectHasFunction.test.ts`:

```
   1 | import noop from '../../utils/noop';
   2 | import objectHasFunction from '../../utils/objectHasFunction';
     ...
   4 | describe('objectHasFunction', () => {
   5 |   it('should detect if any object has function', () => {
   6 |     expect(objectHasFunction({})).toBeFalsy();
   7 |     expect(
   8 |       objectHasFunction({
   9 |         test: '',
  10 |       }),
  11 |     ).toBeFalsy();
     ...
  13 |     expect(
  14 |       objectHasFunction({
  15 |         test: noop,
  16 |       }),
  17 |     ).toBeTruthy();
  18 |   });
  19 | });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-diagnostics-missing-2304-2593-diagnostics-58256c/repro.json
```

## Evidence and reduction

- representative f1084e14ba1e-v04: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4745](https://github.com/microsoft/typescript-go/issues/4745) Native API syntactic diagnostics omit start and length (closed, 2026-07-26, 2 comments)
- [microsoft/typescript-go#4249](https://github.com/microsoft/typescript-go/issues/4249) `.getProgramDiagnostics()` is missing in the API (closed, 2026-06-09, 0 comments)
- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4262](https://github.com/microsoft/typescript-go/issues/4262) Non-deterministic `TS2305 "has no exported member"` errors across project references with `--emitDeclarationOnly` (closed, 2026-06-10, 8 comments)
- [microsoft/typescript-go#4378](https://github.com/microsoft/typescript-go/issues/4378) `tsgo --watch` error: "error starting FSEvents stream" on large `node_modules` since the fswatch rewrite (closed, 2026-06-19, 8 comments)
- [microsoft/typescript-go#4827](https://github.com/microsoft/typescript-go/issues/4827) Generic type argument inferred from the wrong inference slot (cyclic union-of-intersections); larger programs show scheduling-dependent diagnostics (closed, 2026-08-04, 1 comments)
- [microsoft/typescript-go#4719](https://github.com/microsoft/typescript-go/issues/4719) tsgo reports type errors in external-library (node_modules) source files that tsc suppresses (closed, 2026-07-23, 2 comments)
- [microsoft/typescript-go#4129](https://github.com/microsoft/typescript-go/issues/4129) tsgo reports compiler-option diagnostics even when syntactic errors exist (closed, 2026-05-31, 0 comments)
- queries: `diagnostics missing repo:microsoft/typescript-go is:issue`; `diagnostics "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr58256c-r6-replay-test-baseline-20260925-165051-4b3e3e] stderr: context canceled
[ts7-7.0.2-tr58256c-r6-replay-test-control-20260925-165106-22b0ef] stderr: context canceled
```
