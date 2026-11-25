# [ts7 7.0.2] mutation:M1 edit is not valid (diagnostics:extra:2322,2345)

Draft for the author (not filed). Group `ts7-r4-diagnostics-extra-2322-2345-mutation-m1-5efcb9`, signature `ts7|r4_edits|diagnostics:extra:2322,2345`, case family `mutation:M1`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `hexojs/hexo@751e856691bf` (corpus, commit 751e856691bfe24182cf8763feb29db0422dcfee), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open lib/hexo/scaffold.ts`
3. textDocument/didChange: `change lib/hexo/scaffold.ts (0, 16)-(0, 22) ""`
4. textDocument/didChange: `change lib/hexo/scaffold.ts (5, 0)-(5, 0) "import { join } from 'bluebird';\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `test/fixtures/post_render.ts`, `test/scripts/tags/blockquote.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `lib/hexo/scaffold.ts` line 43, column 13 (LSP position {line: 42, character: 12}) (M1:quickfix-errors:Add import from "bluebird"); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  0,
  0,
  1,
  "2322",
  "ts",
  "Type 'Bluebird<{ name: string; path: string; } | undefined>' is not assignable to type 'Bluebird<{ name: string; path: string; }>'. Type '{ name: string; path: string; } | undefined' is not assignable to type '{ name: string; path: string; }'. Type 'undefined' is not assignable to type '{ name: string; path: string; }'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7053",
  "ts",
  "Element implicitly has an 'any' type because expression of type 'string' can't be used to index type '{ normal: string; }'. No index signature with a parameter of type 'string' was found on type '{ normal: string; }'."
 ]
]
```

Actual:

```json
[
 [
  0,
  0,
  0,
  0,
  1,
  "2322",
  "ts",
  "Type 'Bluebird<{ name: string; path: Bluebird<string[]>; }[]>' is not assignable to type 'Bluebird<{ name: string; path: string; }[]>'. Type '{ name: string; path: Bluebird<string[]>; }[]' is not assignable to type '{ name: string; path: string; }[]'. Type '{ name: string; path: Promise<string[]>; }' is not assignable to type '{ name: string; path: string; }'. Types of property 'path' are incompatible. Type 'Bluebird<string[]>' is not assignable to type 'string'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2322",
  "ts",
  "Type 'Bluebird<{ name: string; path: string; } | undefined>' is not assignable to type 'Bluebird<{ name: string; path: string; }>'. Type '{ name: string; path: string; } | undefined' is not assignable to type '{ name: string; path: string; }'. Type 'undefined' is not assignable to type '{ name: string; path: string; }'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2345",
  "ts",
  "Argument of type 'string | Bluebird<string[]>' is not assignable to parameter of type 'string'. Type 'Bluebird<string[]>' is not assignable to type 'string'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2345",
  "ts",
  "Argument of type 'string | Bluebird<string[]>' is not assignable to parameter of type 'string'. Type 'Bluebird<string[]>' is not assignable to type 'string'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7053",
  "ts",
  "Element implicitly has an 'any' type because expression of type 'string' can't be used to index type '{ normal: string; }'. No 
... (1596 characters)
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r4-diagnostics-extra-2322-2345-mutation-m1-5efcb9/repro.json
```

## Evidence and reduction

- representative 1ebb81637940-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 5.299 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects hexojs/hexo@751e856691bf, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4435](https://github.com/microsoft/typescript-go/issues/4435) Different diagnostics and exit code vs tsc for tsconfig using extends + baseUrl + wildcard paths (closed, 2026-06-24, 1 comments)
- [microsoft/typescript-go#3508](https://github.com/microsoft/typescript-go/issues/3508) Corsa no longer emits the TS-1 internal diagnostic about pre-emit/post-emit diagnostic count mismatches (closed, 2026-04-22, 2 comments)
- [microsoft/typescript-go#3615](https://github.com/microsoft/typescript-go/issues/3615) Server stops responding after `Running scheduled diagnostics refresh` (closed, 2026-04-26, 0 comments)
- [microsoft/typescript-go#4314](https://github.com/microsoft/typescript-go/issues/4314) Behavior difference: tsgo misses TS2345 when a namespace translator union is called with a template-literal key union (closed, 2026-06-15, 2 comments)
- [microsoft/typescript-go#1520](https://github.com/microsoft/typescript-go/issues/1520) --incremental builds are a bit slower after the 20250805 release (closed, 2025-08-05, 5 comments)
- queries: `diagnostics extra repo:microsoft/typescript-go is:issue`; `diagnostics "wrong edit" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr5efcb9-r4-replay-baseline-20261118-215909-40702d] stderr: context canceled
[ts7-7.0.2-tr5efcb9-r4-replay-case-20261118-215854-3ddfb5] stderr: context canceled
[ts7-7.0.2-tr5efcb9-r4-replay-control-20261118-215920-266ec8] stderr: context canceled
```
