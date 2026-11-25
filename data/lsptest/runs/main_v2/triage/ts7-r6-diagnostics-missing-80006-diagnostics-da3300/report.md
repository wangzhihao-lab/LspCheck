# [ts7 7.0.2] diagnostics differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-diagnostics-missing-80006-diagnostics-da3300`, signature `ts7|r6_crossimpl|diagnostics:missing:80006`, case family `diagnostics`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `hexojs/hexo@751e856691bf` (corpus, commit 751e856691bfe24182cf8763feb29db0422dcfee), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/diagnostic` on `lib/hexo/scaffold.ts` for the whole file; compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  46,
  2,
  46,
  14,
  0,
  "80006",
  "",
  ""
 ],
 [
  50,
  4,
  50,
  10,
  0,
  "2322",
  "",
  ""
 ],
 [
  59,
  13,
  59,
  32,
  0,
  "7053",
  "",
  ""
 ]
]
```

Actual:

```json
[
 [
  50,
  4,
  50,
  10,
  0,
  "2322",
  "",
  ""
 ],
 [
  59,
  13,
  59,
  32,
  0,
  "7053",
  "",
  ""
 ]
]
```

Project file `lib/hexo/scaffold.ts`:

```
   1 | import { extname, join } from 'path';
   2 | import { exists, listDir, readFile, unlink, writeFile } from 'hexo-fs';
   3 | import type Hexo from './index';
   4 | import type { NodeJSLikeCallback } from '../types';
   5 | import type Promise from 'bluebird';
     ...
   7 | class Scaffold {
   8 |   public context: Hexo;
   9 |   public scaffoldDir: string;
  10 |   public defaults: {
  11 |     normal: string
  12 |   };
     ...
  14 |   constructor(context: Hexo) {
  15 |     this.context = context;
  16 |     this.scaffoldDir = context.scaffold_dir;
  17 |     this.defaults = {
  18 |       normal: [
  19 |         '---',
  20 |         'layout: {{ layout }}',
  21 |         'title: {{ title }}',
  22 |         'date: {{ date }}',
  23 |         'tags:',
  24 |         '---'
  25 |       ].join('\n')
  26 |     };
  27 |   }
     ...
  29 |   _listDir(): Promise<{
  30 |     name: string;
  31 |     path: string;
  32 |   }[]> {
  33 |     const { scaffoldDir } = this;
     ...
  35 |     return exists(scaffoldDir).then(exist => {
  36 |       if (!exist) return [];
     ...
  38 |       return listDir(scaffoldDir, {
  39 |         ignorePattern: /^_|\/_/
  40 |       });
  41 |     }).map(item => ({
  42 |       name: item.substring(0, item.length - extname(item).length),
  43 |       path: join(scaffoldDir, item)
  44 |     }));
  45 |   }
     ...
  47 |   _getScaffold(name: string): Promise<{
  48 |     name: string;
  49 |     path: string;
  50 |   }> {
  51 |     return this._listDir().then(list => list.find(item => item.name === name));
  52 |   }
     ...
  54 |   get(name: string, callback?: NodeJSLikeCallback<any>): Promise<string> {
  55 |     return this._getScaffold(name).then(item => {
  56 |       if (item) {
  57 |         return readFile(item.path);
  58 |       }
     ...
  60 |       return this.defaults[name];
  61 |     }).asCallback(callback);
  62 |   }
     ...
  64 |   set(name: string, content: any, callback?: NodeJSLikeCallback<void>): Promise<void> {
  65 |     const { scaffoldDir } = this;
     ...
  67 |     return this._getScaffold(name).then(item => {
  68 |       let path = item ? item.path : join(scaffoldDir, name);
  69 |       if (!extname(path)) path += '.md';
     ...
  71 |       return writeFile(path, content);
  72 |     }).asCallback(callback);
  73 |   }
     ...
  75 |   remove(name: string, callback?: NodeJSLikeCallback<void>): Promise<void> {
  76 |     return this._getScaffold(name).then(item => {
  77 |       if (!item) return;
     ...
  79 |       return unlink(item.path);
  80 |     }).asCallback(callback);
  81 |   }
  82 | }
     ...
  84 | export = Scaffold;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-diagnostics-missing-80006-diagnostics-da3300/repro.json
```

## Evidence and reduction

- representative 8f90deb06cba-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
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
[ts7-7.0.2-trda3300-r6-replay-test-baseline-20261118-223045-e3ff72] stderr: context canceled
[ts7-7.0.2-trda3300-r6-replay-test-control-20261118-223050-0ee447] stderr: context canceled
```
