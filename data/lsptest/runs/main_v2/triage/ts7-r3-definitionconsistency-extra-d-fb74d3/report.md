# [ts7 7.0.2] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts7-r3-definitionconsistency-extra-d-fb74d3`, signature `ts7|r3_routes|definitionConsistency:extra`, case family `d`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `date-fns/date-fns@f34149bb1ba1` (corpus, commit f34149bb1ba10046453e688207507e0d2c727e00), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `pkgs/core/src/locale/nn/_lib/localize/index.ts` at line 112, column 13 (LSP position {line: 111, character: 12}) gives the expected set; didOpen `pkgs/core/src/locale/_lib/buildLocalizeFn/index.ts` and `textDocument/definition` at the reference line 129, column 20 (LSP position {line: 128, character: 19}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "pkgs/core/src/locale/_lib/buildLocalizeFn/index.ts",
  18,
  6,
  18,
  22
 ]
]
```

Actual:

```json
[
 [
  "pkgs/core/src/locale/_lib/buildLocalizeFn/index.ts",
  17,
  6,
  17,
  22
 ],
 [
  "pkgs/core/src/locale/_lib/buildLocalizeFn/index.ts",
  18,
  6,
  18,
  22
 ]
]
```

Project file `pkgs/core/src/locale/_lib/buildLocalizeFn/index.ts`:

```
   1 | import type { Day, Era, Month, Quarter } from "../../../types.ts";
   2 | import type {
   3 |   LocaleDayPeriod,
   4 |   LocaleUnitValue,
   5 |   LocaleWidth,
   6 |   LocalizeFn,
   7 | } from "../../types.ts";
     ...
   9 | export type BuildLocalizeFnArgs<
  10 |   Value extends LocaleUnitValue,
  11 |   ArgCallback extends LocalizeFnArgCallback<Value> | undefined,
  12 | > = {
  13 |   values: LocalizePeriodValuesMap<Value>;
  14 |   defaultWidth: LocaleWidth;
  15 |   formattingValues?: LocalizePeriodValuesMap<Value>;
  16 |   defaultFormattingWidth?: LocaleWidth;
  17 | } & (ArgCallback extends undefined
  18 |   ? { argumentCallback?: undefined }
  19 |   : { argumentCallback: LocalizeFnArgCallback<Value> });
     ...
  21 | /**
  22 |  * The localize function argument callback which allows to convert raw value to
  23 |  * the actual type.
  24 |  *
  25 |  * @param value - The value to convert
  26 |  *
  27 |  * @returns The converted value
  28 |  */
  29 | export type LocalizeFnArgCallback<Value extends LocaleUnitValue | number> = (
  30 |   value: Value,
  31 | ) => LocalizeUnitIndex<Value>;
     ...
  33 | /**
  34 |  * The map of localized values for each width.
  35 |  */
  36 | export type LocalizePeriodValuesMap<Value extends LocaleUnitValue> = {
  37 |   [Pattern in LocaleWidth]?: LocalizeValues<Value>;
  38 | };
     ...
  40 | /**
  41 |  * The index type of the locale unit value. It types conversion of units of
  42 |  * values that don't start at 0 (i.e. quarters).
  43 |  */
  44 | export type LocalizeUnitIndex<Value extends LocaleUnitValue | number> =
  45 |   Value extends LocaleUnitValue ? keyof LocalizeValues<Value> : number;
     ...
  47 | /**
  48 |  * Converts the unit value to the tuple of values.
  49 |  */
  50 | export type LocalizeValues<Value extends LocaleUnitValue> =
  51 |   Value extends LocaleDayPeriod
  52 |     ? Record<LocaleDayPeriod, string>
  53 |     : Value extends Era
  54 |       ? LocalizeEraValues
  55 |       : Value extends Quarter
  56 |         ? LocalizeQuarterValues
  57 |         : Value extends Day
  58 |           ? LocalizeDayValues
  59 |           : Value extends Month
  60 |             ? LocalizeMonthValues
  61 |             : never;
     ...
  63 | /**
  64 |  * The tuple of localized era values. The first element represents BC,
  65 |  * the second element represents AD.
  66 |  */
  67 | export type LocalizeEraValues = readonly [string, string];
     ...
  69 | /**
  70 |  * The tuple of localized quarter values. The first element represents Q1.
  71 |  */
  72 | export type LocalizeQuarterValues = readonly [string, string, string, string];
     ...
  74 | /**
  75 |  * The tuple of localized day values. The first element represents Sunday.
  76 |  */
  77 | export type LocalizeDayValues = readonly [
  78 |   string,
  79 |   string,
  80 |   string,
  81 |   string,
  82 |   string,
  83 |   string,
  84 |   string,
  85 | ];
     ...
  87 | /**
  88 |  * The tuple of localized month values. The first element represents January.
  89 |  */
  90 | export type LocalizeMonthValues = readonly [
  91 |   string,
  92 |   string,
  93 |   string,
  94 |   string,
  95 |   string,
  96 |   string,
  97 |   string,
  98 |   string,
  99 |   string,
 100 |   string,
 101 |   string,
 102 |   string,
 103 | ];
     ...
 105 | export function buildLocalizeFn<
 106 |   Value extends LocaleUnitValue,
 107 |   ArgCallback extends LocalizeFnArgCallback<Value> | undefined,
 108 | >(args: BuildLocalizeFnArgs<Value, ArgCallback>): LocalizeFn<Value> {
 109 |   return (value, options) => {
 110 |     const context = options?.context ? String(options.context) : "standalone";
     ...
 112 |     let valuesArray: LocalizeValues<Value>;
 113 |     if (context === "formatting" && args.formattingValues) {
 114 |       const defaultWidth = args.defaultFormattingWidth || args.defaultWidth;
 115 |       const width = (
 116 |         options?.width ? String(options.width) : defaultWidth
 117 |       ) as LocaleWidth;
 118 |       valuesArray = (args.formattingValues[width] ||
 119 |         args.formattingValues[defaultWidth]) as LocalizeValues<Value>;
 120 |     } else {
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r3-definitionconsistency-extra-d-fb74d3/repro.json
```

## Evidence and reduction

- representative 605e065dec15-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects date-fns/date-fns@f34149bb1ba1, hexojs/hexo@751e856691bf, vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4908](https://github.com/microsoft/typescript-go/issues/4908) Go-to-definition does not work at the right edge of a JSX tag name (closed, 2026-08-17, 0 comments)
- [microsoft/typescript-go#1885](https://github.com/microsoft/typescript-go/issues/1885) go to definition panic (windows, wsl) (closed, 2025-10-15, 4 comments)
- [microsoft/typescript-go#2209](https://github.com/microsoft/typescript-go/issues/2209) [lsp] Go to Definition missing getter when property returns callable interface (closed, 2025-12-04, 0 comments)
- [microsoft/typescript-go#2839](https://github.com/microsoft/typescript-go/issues/2839) Cannot "go to definition" of a playwright fixture (closed, 2026-02-19, 1 comments)
- [microsoft/typescript-go#2847](https://github.com/microsoft/typescript-go/issues/2847) panic on go-to-type-definition of tuple type (closed, 2026-02-20, 0 comments)
- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4000](https://github.com/microsoft/typescript-go/issues/4000) Make typedef exporting explicit (closed, 2026-05-20, 7 comments)
- [microsoft/typescript-go#4037](https://github.com/microsoft/typescript-go/issues/4037) TS2304 when a generic (@template) function JSDoc contains @overload (closed, 2026-05-23, 5 comments)
- queries: `"go to definition" in:title repo:microsoft/typescript-go is:issue`; `definition extra repo:microsoft/typescript-go is:issue`; `definition "go to definition" repo:microsoft/typescript-go is:issue`; `definition inconsistent repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trfb74d3-r3-replay-baseline-20261118-214745-1f1d5d] stderr: context canceled
[ts7-7.0.2-trfb74d3-r3-replay-control-20261118-214757-e0cd73] stderr: context canceled
```
