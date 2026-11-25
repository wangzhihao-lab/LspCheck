# [ts6 6.0.3] quickfix edit is not valid (diagnostics:changed:1064,2322)

Draft for the author (not filed). Group `ts6-r4-diagnostics-changed-1064-2322-quickfix-d597f5`, signature `ts6|r4_edits|diagnostics:changed:1064,2322`, case family `quickfix`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `hexojs/hexo@751e856691bf` (corpus, commit 751e856691bfe24182cf8763feb29db0422dcfee), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. request code actions for the diagnostic {'code': 80006, 'message': 'This may be converted to an async function.', 'range': {'end': {'character': 14, 'line': 46}, 'start': {'character': 2, 'line': 46}}, 'severity': 4} in `lib/hexo/scaffold.ts`; apply the quick fix 'Convert to async function'; wait until idle: the diagnostic must be gone and no error added.

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
  "typescript",
  "Type 'Bluebird<{ name: string; path: string; } | undefined>' is not assignable to type 'Bluebird<{ name: string; path: string; }>'. Type '{ name: string; path: string; } | undefined' is not assignable to type '{ name: string; path: string; }'. Type 'undefined' is not assignable to type '{ name: string; path: string; }'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7053",
  "typescript",
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
  "1064",
  "typescript",
  "The return type of an async function or method must be the global Promise<T> type. Did you mean to write 'Promise<{ name: string; path: string; }>'?"
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2322",
  "typescript",
  "Type '{ name: string; path: string; } | undefined' is not assignable to type '{ name: string; path: string; }'. Type 'undefined' is not assignable to type '{ name: string; path: string; }'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7053",
  "typescript",
  "Element implicitly has an 'any' type because expression of type 'string' can't be used to index type '{ normal: string; }'. No index signature with a parameter of type 'string' was found on type '{ normal: string; }'."
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r4-diagnostics-changed-1064-2322-quickfix-d597f5/repro.json
```

## Evidence and reduction

- representative 76cde4f3a703-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects hexojs/hexo@751e856691bf, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#1136](https://github.com/typescript-language-server/typescript-language-server/issues/1136) Spurious "Cannot find name 'div'" (TS2304) when hover is requested right after didOpen (closed, 2026-09-28, 4 comments)
- [typescript-language-server/typescript-language-server#1093](https://github.com/typescript-language-server/typescript-language-server/issues/1093) Wrong Autocomplete (closed, 2026-05-20, 2 comments)
- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#844](https://github.com/typescript-language-server/typescript-language-server/issues/844) Server crashed when asking for textDocument/codeAction (closed, 2024-01-06, 11 comments)
- [microsoft/TypeScript#50641](https://github.com/microsoft/TypeScript/issues/50641) Suggestion isn't included in quick fixes  (open, 2022-09-05, 1 comments)
- [microsoft/TypeScript#64689](https://github.com/microsoft/TypeScript/issues/64689) TS 7 language server: "Add missing properties" quick fix not offered (open, 2026-10-08, 0 comments)
- [microsoft/TypeScript#37782](https://github.com/microsoft/TypeScript/issues/37782) 'declare method' quick fix for adding a private method (open, 2020-04-03, 20 comments)
- queries: `"quick fix" in:title repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics wrong repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics "quick fix" repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics "wrong edit" repo:typescript-language-server/typescript-language-server is:issue`; `"quick fix" in:title repo:microsoft/TypeScript is:issue`; `diagnostics wrong repo:microsoft/TypeScript is:issue`; `diagnostics "quick fix" repo:microsoft/TypeScript is:issue`; `diagnostics "wrong edit" repo:microsoft/TypeScript is:issue`
