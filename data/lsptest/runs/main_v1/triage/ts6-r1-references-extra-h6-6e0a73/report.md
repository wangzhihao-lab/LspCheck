# [ts6 6.0.3] references adds entries after depended-on file round trip

Draft for the author (not filed). Group `ts6-r1-references-extra-h6-6e0a73`, signature `ts6|r1_history|references:extra`, case family `H6`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/__typetest__/__fixtures__/type.ts (then 200 ms)`
3. Timing: send the steps 200 ms apart without waiting, then wait until idle.
4. textDocument/didOpen `app/src/main.tsx`, `examples/V7/validationOnFieldBlur.tsx`, `src/logic/skipValidation.ts` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/references` on `src/logic/skipValidation.ts` line 7, column 21 (LSP position {line: 6, character: 20}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.dom.d.ts",
  43346,
  49,
  43346,
  53
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es2021.intl.d.ts",
  161,
  63,
  161,
  67
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es2022.intl.d.ts",
  131,
  63,
  131,
  67
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es5.d.ts",
  1603,
  5,
  1603,
  9
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es5.d.ts",
  1627,
  36,
  1627,
  40
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.esnext.temporal.d.ts",
  116,
  81,
  116,
  85
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  138,
  34,
  142
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  206,
  34,
  210
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  264,
  34,
  268
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  323,
  34,
  327
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/object/object.d.mts",
  16,
  118,
  16,
  122
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/object/object.d.mts",
  16,
  172,
  16,
  
... (5643 characters)
```

Actual:

```json
[
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.dom.d.ts",
  43346,
  49,
  43346,
  53
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es2021.intl.d.ts",
  161,
  63,
  161,
  67
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es2022.intl.d.ts",
  131,
  63,
  131,
  67
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es5.d.ts",
  1603,
  5,
  1603,
  9
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.es5.d.ts",
  1627,
  36,
  1627,
  40
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.esnext.temporal.d.ts",
  116,
  81,
  116,
  85
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  138,
  34,
  142
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  206,
  34,
  210
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  264,
  34,
  268
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/module/infer.d.mts",
  34,
  323,
  34,
  327
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/object/object.d.mts",
  16,
  118,
  16,
  122
 ],
 [
  "node_modules/.pnpm/@sinclair+typebox@0.34.49/node_modules/@sinclair/typebox/build/esm/type/object/object.d.mts",
  16,
  172,
  16,
  
... (6052 characters)
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
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-references-extra-h6-6e0a73/repro.json
```

## Evidence and reduction

- representative 05d21764e97c-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 7 -> 1 (5 probes, 65.508 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, timings race0, race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#926](https://github.com/typescript-language-server/typescript-language-server/issues/926) "Maximum call stack size exceeded" error with Node v23.0.0 in Neovim (closed, 2024-10-19, 5 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#724](https://github.com/typescript-language-server/typescript-language-server/issues/724) "typescript.inlayHints.includeInlayParameterNameHints": "all" breaks inference with dangling commas (closed, 2023-05-15, 7 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#199](https://github.com/typescript-language-server/typescript-language-server/issues/199) Is applyFileRename operational? (closed, 2021-04-03, 3 comments)
- [microsoft/TypeScript#63652](https://github.com/microsoft/TypeScript/issues/63652) Files changed (closed, 2026-07-16, 1 comments)
- [microsoft/TypeScript#63942](https://github.com/microsoft/TypeScript/issues/63942) `tsc -b -w` won't catch error on file changed across project (closed, 2026-08-21, 2 comments)
- queries: `"file changed" in:title repo:typescript-language-server/typescript-language-server is:issue`; `references extra repo:typescript-language-server/typescript-language-server is:issue`; `references "file changed" repo:typescript-language-server/typescript-language-server is:issue`; `references stale repo:typescript-language-server/typescript-language-server is:issue`; `"file changed" in:title repo:microsoft/TypeScript is:issue`; `references extra repo:microsoft/TypeScript is:issue`; `references "file changed" repo:microsoft/TypeScript is:issue`; `references stale repo:microsoft/TypeScript is:issue`
