# [ts7 7.0.2] references adds entries after depended-on file round trip

Draft for the author (not filed). Group `ts7-r1-references-extra-h6-574e94`, signature `ts7|r1_history|references:extra`, case family `H6`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/__typetest__/__fixtures__/type.ts`
3. Timing: send the steps 0 ms apart without waiting, then wait until idle.
4. textDocument/didOpen `app/src/main.tsx`, `examples/V7/validationOnFieldBlur.tsx`, `src/logic/skipValidation.ts` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/references` on `src/logic/skipValidation.ts` line 7, column 21 (LSP position {line: 6, character: 20}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.dom.d.ts",
  43346,
  49,
  43346,
  53
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es2021.intl.d.ts",
  161,
  63,
  161,
  67
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es2022.intl.d.ts",
  131,
  63,
  131,
  67
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es5.d.ts",
  1603,
  5,
  1603,
  9
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es5.d.ts",
  1627,
  36,
  1627,
  40
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.esnext.temporal.d.ts",
  116,
  81,
  116,
  85
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/assert.d.ts",
  57,
  33,
  57,
  37
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/assert.d.ts",
  60,
  39,
  60,
  43
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/crypto.d.ts",
  3205,
  44,
  3205,
  48
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/http.d.ts",
  162,
  40,
  162,
  44
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/http2.d.ts",
  356,
  22,
  356,
  26
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/http2.d.ts",
  1309,
  34,
  1309,
  38
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/stream.d.ts",
  94,
  26,
  94,
... (12304 characters)
```

Actual:

```json
[
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.dom.d.ts",
  43346,
  49,
  43346,
  53
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es2021.intl.d.ts",
  161,
  63,
  161,
  67
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es2022.intl.d.ts",
  131,
  63,
  131,
  67
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es5.d.ts",
  1603,
  5,
  1603,
  9
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.es5.d.ts",
  1627,
  36,
  1627,
  40
 ],
 [
  "<servers>/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/lib.esnext.temporal.d.ts",
  116,
  81,
  116,
  85
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/assert.d.ts",
  57,
  33,
  57,
  37
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/assert.d.ts",
  60,
  39,
  60,
  43
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/crypto.d.ts",
  3205,
  44,
  3205,
  48
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/http.d.ts",
  162,
  40,
  162,
  44
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/http2.d.ts",
  356,
  22,
  356,
  26
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/http2.d.ts",
  1309,
  34,
  1309,
  38
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/stream.d.ts",
  94,
  26,
  94,
... (12713 characters)
```

Project file `src/logic/skipValidation.ts`:

```
   1 | import type { ValidationModeFlags } from '../types';
     ...
   3 | export default (
   4 |   isBlurEvent: boolean,
   5 |   isTouched: boolean,
   6 |   isSubmitted: boolean,
   7 |   reValidateMode: Pick<ValidationModeFlags, 'isOnBlur' | 'isOnChange'>,
   8 |   mode: Partial<ValidationModeFlags>,
   9 | ) => {
  10 |   if (mode.isOnAll) {
  11 |     return false;
  12 |   } else if (!isSubmitted && mode.isOnTouch) {
  13 |     return !(isTouched || isBlurEvent);
  14 |   } else if (isSubmitted ? reValidateMode.isOnBlur : mode.isOnBlur) {
  15 |     return !isBlurEvent;
  16 |   } else if (isSubmitted ? reValidateMode.isOnChange : mode.isOnChange) {
  17 |     return isBlurEvent;
  18 |   }
  19 |   return true;
  20 | };
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r1-references-extra-h6-574e94/repro.json
```

## Evidence and reduction

- representative 2ee9fa2c90a7-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 7 -> 1 (5 probes, 76.122 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings race0, race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#3551](https://github.com/microsoft/typescript-go/issues/3551) Baselines: Output file ordering changed + declaration types resolve to any instead of typeof references (closed, 2026-04-23, 2 comments)
- [microsoft/typescript-go#4593](https://github.com/microsoft/typescript-go/issues/4593) File change events always trigger project recheck even if file content hasn't actually changed (closed, 2026-07-10, 0 comments)
- [microsoft/typescript-go#4314](https://github.com/microsoft/typescript-go/issues/4314) Behavior difference: tsgo misses TS2345 when a namespace translator union is called with a template-literal key union (closed, 2026-06-15, 2 comments)
- [microsoft/typescript-go#3508](https://github.com/microsoft/typescript-go/issues/3508) Corsa no longer emits the TS-1 internal diagnostic about pre-emit/post-emit diagnostic count mismatches (closed, 2026-04-22, 2 comments)
- [microsoft/typescript-go#3571](https://github.com/microsoft/typescript-go/issues/3571) Module augmentation not merged when upstream .d.ts uses top-level `export interface` + self-referential `declare module ... export =` (closed, 2026-04-23, 5 comments)
- [microsoft/typescript-go#2222](https://github.com/microsoft/typescript-go/issues/2222) autocomplete references packages don't exist in context on a monorepo (closed, 2025-12-04, 3 comments)
- [microsoft/typescript-go#1713](https://github.com/microsoft/typescript-go/issues/1713) Complains about relative paths in `"paths"` but this works fine in current tsc (closed, 2025-09-11, 9 comments)
- [microsoft/typescript-go#4262](https://github.com/microsoft/typescript-go/issues/4262) Non-deterministic `TS2305 "has no exported member"` errors across project references with `--emitDeclarationOnly` (closed, 2026-06-10, 8 comments)
- queries: `"file changed" in:title repo:microsoft/typescript-go is:issue`; `references extra repo:microsoft/typescript-go is:issue`; `references "file changed" repo:microsoft/typescript-go is:issue`; `references stale repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr574e94-replay-baseline-20260925-153950-88eeb0] stderr: context canceled
[ts7-7.0.2-tr574e94-replay-control-20260925-153950-4d4ca1] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr574e94-replay-control-20260925-153950-4d4ca1] stderr: context canceled
[ts7-7.0.2-tr574e94-replay-history-20260925-154001-6e5b36] stderr: context canceled
```
