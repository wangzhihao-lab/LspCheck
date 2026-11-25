# [ts7 7.0.2] diagnostics differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-diagnostics-missing-2304-2339-2593-diagnostics-31eb88`, signature `ts7|r6_crossimpl|diagnostics:missing:2304,2339,2593`, case family `diagnostics`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `hexojs/hexo@751e856691bf` (corpus, commit 751e856691bfe24182cf8763feb29db0422dcfee), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/diagnostic` on `test/scripts/tags/blockquote.ts` for the whole file; compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  11,
  2,
  11,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  13,
  11,
  13,
  17,
  0,
  "2339",
  "",
  ""
 ],
 [
  16,
  2,
  16,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  18,
  11,
  18,
  17,
  0,
  "2339",
  "",
  ""
 ],
 [
  21,
  2,
  21,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  23,
  11,
  23,
  17,
  0,
  "2339",
  "",
  ""
 ],
 [
  26,
  2,
  26,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  28,
  11,
  28,
  17,
  0,
  "2339",
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
  31,
  2,
  31,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  33,
  11,
  33,
  17,
  0,
  "2339",
  "",
  ""
 ],
 [
  36,
  2,
  36,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  40,
  11,
  40,
  17,
  0,
  "2339",
  "",
  ""
 ],
 [
  7,
  2,
  7,
  8,
  0,
  "2304",
  "",
  ""
 ],
 [
  9,
  14,
  9,
  18,
  0,
  "7006",
  "",
  ""
 ],
 [
  9,
  20,
  9,
  28,
  0,
  "7006",
  "",
  ""
 ]
]
```

Actual:

```json
[
 [
  9,
  14,
  9,
  18,
  0,
  "7006",
  "",
  ""
 ],
 [
  9,
  20,
  9,
  28,
  0,
  "7006",
  "",
  ""
 ]
]
```

Project file `test/scripts/tags/blockquote.ts`:

```
   1 | import Hexo from '../../../lib/hexo';
   2 | import tagBlockquote from '../../../lib/plugins/tag/blockquote';
     ...
   4 | describe('blockquote', () => {
   5 |   const hexo = new Hexo(__dirname);
   6 |   const blockquote = tagBlockquote(hexo);
     ...
   8 |   before(() => hexo.init().then(() => hexo.loadPlugin(require.resolve('hexo-renderer-marked'))));
     ...
  10 |   const bq = (args, content?) => blockquote(args.split(' '), content || '');
     ...
  12 |   it('default', () => {
  13 |     const result = bq('', '123456 **bold** and *italic*');
  14 |     result.should.eql('<blockquote><p>123456 <strong>bold</strong> and <em>italic</em></p>\n</blockquote>');
  15 |   });
     ...
  17 |   it('author', () => {
  18 |     const result = bq('John Doe', '');
  19 |     result.should.eql('<blockquote><footer><strong>John Doe</strong></footer></blockquote>');
  20 |   });
     ...
  22 |   it('source', () => {
  23 |     const result = bq('Jane Austen, Pride and Prejudice');
  24 |     result.should.eql('<blockquote><footer><strong>Jane Austen</strong><cite>Pride and Prejudice</cite></footer></blockquote>');
  25 |   });
     ...
  27 |   it('link', () => {
  28 |     const result = bq('John Doe https://hexo.io/');
  29 |     result.should.eql('<blockquote><footer><strong>John Doe</strong><cite><a href="https://hexo.io/">hexo.io</a></cite></footer></blockquote>');
  30 |   });
     ...
  32 |   it('link title', () => {
  33 |     const result = bq('John Doe https://hexo.io/ Hexo');
  34 |     result.should.eql('<blockquote><footer><strong>John Doe</strong><cite><a href="https://hexo.io/">Hexo</a></cite></footer></blockquote>');
  35 |   });
     ...
  37 |   it('titlecase', () => {
  38 |     hexo.config.titlecase = true;
     ...
  40 |     const result = bq('Jane Austen, pride and prejudice');
  41 |     result.should.eql('<blockquote><footer><strong>Jane Austen</strong><cite>Pride and Prejudice</cite></footer></blockquote>');
     ...
  43 |     hexo.config.titlecase = false;
  44 |   });
  45 | });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-diagnostics-missing-2304-2339-2593-diagnostics-31eb88/repro.json
```

## Evidence and reduction

- representative 8f90deb06cba-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects hexojs/hexo@751e856691bf, timings settled, seeds 2

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
[ts7-7.0.2-tr31eb88-r6-replay-test-baseline-20261118-222644-0a7975] stderr: context canceled
[ts7-7.0.2-tr31eb88-r6-replay-test-control-20261118-222654-8e9008] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr31eb88-r6-replay-test-control-20261118-222654-8e9008] stderr: context canceled
```
