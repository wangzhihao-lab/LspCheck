# [ts7 7.0.2] completion differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-completion-gained-completion-4b6660`, signature `ts7|r6_crossimpl|completion:gained`, case family `completion`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/completion` on `src/__tests__/utils/objectHasFunction.test.ts` line 6, column 44 (LSP position {line: 5, character: 43}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "not",
 "rejects",
 "resolves",
 "toAppearAfter",
 "toAppearBefore",
 "toBe",
 "toBeChecked",
 "toBeCloseTo",
 "toBeDefined",
 "toBeDisabled",
 "toBeEmpty",
 "toBeEmptyDOMElement",
 "toBeEnabled",
 "toBeFalsy",
 "toBeGreaterThan",
 "toBeGreaterThanOrEqual",
 "toBeInTheDOM",
 "toBeInTheDocument",
 "toBeInstanceOf",
 "toBeInvalid",
 "toBeLessThan",
 "toBeLessThanOrEqual",
 "toBeNaN",
 "toBeNull",
 "toBePartiallyChecked",
 "toBePartiallyPressed",
 "toBePressed",
 "toBeRequired",
 "toBeTruthy",
 "toBeUndefined",
 "toBeValid",
 "toBeVisible",
 "toContain",
 "toContainElement",
 "toContainEqual",
 "toContainHTML",
 "toEqual",
 "toHaveAccessibleDescription",
 "toHaveAccessibleErrorMessage",
 "toHaveAccessibleName",
 "toHaveAttribute",
 "toHaveBeenCalled",
 "toHaveBeenCalledTimes",
 "toHaveBeenCalledWith",
 "toHaveBeenLastCalledWith",
 "toHaveBeenNthCalledWith",
 "toHaveClass",
 "toHaveDescription",
 "toHaveDisplayValue",
 "toHaveErrorMessage",
 "toHaveFocus",
 "toHaveFormValues",
 "toHaveLastReturnedWith",
 "toHaveLength",
 "toHaveNthReturnedWith",
 "toHaveProperty",
 "toHaveReturned",
 "toHaveReturnedTimes",
 "toHaveReturnedWith",
 "toHaveRole",
 "toHaveSelection",
 "toHaveStyle",
 "toHaveTextContent",
 "toHaveValue",
 "toMatch",
 "toMatchInlineSnapshot",
 "toMatchObject",
 "toMatchSnapshot",
 "toStrictEqual",
 "toThrow",
 "toThrowErrorMatchingInlineSnapshot",
 "toThrowErrorMatchingSnapshot"
]
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-completion-gained-completion-4b6660/repro.json
```

## Evidence and reduction

- representative f1084e14ba1e-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#2669](https://github.com/microsoft/typescript-go/issues/2669) Completions crash for unrecognized ambiently-defined file extensions (closed, 2026-02-04, 0 comments)
- [microsoft/typescript-go#2497](https://github.com/microsoft/typescript-go/issues/2497) LSP panic in autoimport: unexpected internal symbol name in export (closed, 2026-01-13, 2 comments)
- [microsoft/typescript-go#4380](https://github.com/microsoft/typescript-go/issues/4380) [ServerErrors][TypeScript] main vs  (closed, 2026-06-19, 7 comments)
- [microsoft/typescript-go#2964](https://github.com/microsoft/typescript-go/issues/2964) [ServerErrors][JavaScript] linux-x64-7.0.0-dev.20260303.1 vs  (closed, 2026-03-03, 11 comments)
- [microsoft/typescript-go#2473](https://github.com/microsoft/typescript-go/issues/2473) Autocompletion panics (closed, 2026-01-12, 9 comments)
- [microsoft/typescript-go#4677](https://github.com/microsoft/typescript-go/issues/4677) JSDoc (TSDoc ???) is not shown for object literal properties on hover (closed, 2026-07-20, 1 comments)
- [microsoft/typescript-go#4347](https://github.com/microsoft/typescript-go/issues/4347) CPU usage spikes to 80% to 100% when using `tsgo --lsp --stdio` (closed, 2026-06-17, 5 comments)
- [microsoft/typescript-go#3946](https://github.com/microsoft/typescript-go/issues/3946) Auto-import lowercases internal capitals in PascalCase default-import bindings (closed, 2026-05-18, 0 comments)
- queries: `completion unexpected repo:microsoft/typescript-go is:issue`; `completion "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr4b6660-r6-replay-test-baseline-20260925-163006-9ae492] stderr: context canceled
[ts7-7.0.2-tr4b6660-r6-replay-test-baseline-20260925-163006-9ae492] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr4b6660-r6-replay-test-control-20260925-163026-4c4671] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr4b6660-r6-replay-test-control-20260925-163026-4c4671] stderr: context canceled
```
