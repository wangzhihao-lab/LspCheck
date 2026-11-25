# [ts7 7.0.2] definition differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-definition-changed-definition-1c2318`, signature `ts7|r6_crossimpl|definition:changed`, case family `definition`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `hexojs/hexo@751e856691bf` (corpus, commit 751e856691bfe24182cf8763feb29db0422dcfee), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/definition` on `lib/extend/helper.ts` line 18, column 23 (LSP position {line: 17, character: 22}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "lib/extend/helper.ts",
  2,
  12,
  2,
  17
 ]
]
```

Actual:

```json
[
 [
  "node_modules/hexo-util/dist/index.d.ts",
  0,
  0,
  30,
  0
 ]
]
```

Project file `lib/extend/helper.ts`:

```
   1 | import Hexo from '../hexo';
   2 | import { PageSchema } from '../types';
   3 | import * as hutil from 'hexo-util';
     ...
   5 | interface HexoContext extends Hexo {
   6 |   // get current page information
   7 |   // https://github.com/dimaslanjaka/hexo-renderers/blob/147340f6d03a8d3103e9589ddf86778ed7f9019b/src/helper/related-posts.ts#L106-L113
   8 |   page?: PageSchema;
     ...
  10 |   // hexo-util shims
  11 |   url_for: typeof hutil.url_for;
  12 |   full_url_for: typeof hutil.full_url_for;
  13 |   relative_url: typeof hutil.relative_url;
  14 |   slugize: typeof hutil.slugize;
  15 |   escapeDiacritic: typeof hutil.escapeDiacritic;
  16 |   escapeHTML: typeof hutil.escapeHTML;
  17 |   unescapeHTML: typeof hutil.unescapeHTML;
  18 |   encodeURL: typeof hutil.encodeURL;
  19 |   decodeURL: typeof hutil.decodeURL;
  20 |   escapeRegExp: typeof hutil.escapeRegExp;
  21 |   stripHTML: typeof hutil.stripHTML;
  22 |   stripIndent: typeof hutil.stripIndent;
  23 |   hash: typeof hutil.hash;
  24 |   createSha1Hash: typeof hutil.createSha1Hash;
  25 |   highlight: typeof hutil.highlight;
  26 |   prismHighlight: typeof hutil.prismHighlight;
  27 |   tocObj: typeof hutil.tocObj;
  28 |   wordWrap: typeof hutil.wordWrap;
  29 |   prettyUrls: typeof hutil.prettyUrls;
  30 |   isExternalLink: typeof hutil.isExternalLink;
  31 |   gravatar: typeof hutil.gravatar;
  32 |   htmlTag: typeof hutil.htmlTag;
  33 |   truncate: typeof hutil.truncate;
  34 |   spawn: typeof hutil.spawn;
  35 |   camelCaseKeys: typeof hutil.camelCaseKeys;
  36 |   deepMerge: typeof hutil.deepMerge;
  37 | }
     ...
  39 | interface StoreFunction {
  40 |   (this: HexoContext, ...args: any[]): any;
  41 | }
     ...
  43 | interface Store {
  44 |   [key: string]: StoreFunction;
  45 | }
     ...
  47 | /**
  48 |  * A helper makes it easy to quickly add snippets to your templates. We recommend using helpers instead of templates when you’re dealing with more complicated code.
  49 |  */
  50 | class Helper {
  51 |   public store: Store;
     ...
  53 |   constructor() {
  54 |     this.store = {};
  55 |   }
     ...
  57 |   /**
  58 |    * @returns {Store} - The plugin store
  59 |    */
  60 |   list(): Store {
  61 |     return this.store;
  62 |   }
     ...
  64 |   /**
  65 |    * Get helper plugin function by name
  66 |    * @param {String} name - The name of the helper plugin
  67 |    * @returns {StoreFunction}
  68 |    */
  69 |   get(name: string): StoreFunction {
  70 |     return this.store[name];
  71 |   }
     ...
  73 |   /**
  74 |    * Register a helper plugin
  75 |    * @param {String} name - The name of the helper plugin
  76 |    * @param {StoreFunction} fn - The helper plugin function
  77 |    */
  78 |   register(name: string, fn: StoreFunction): void {
  79 |     if (!name) throw new TypeError('name is required');
  80 |     if (typeof fn !== 'function') throw new TypeError('fn must be a function');
     ...
  82 |     this.store[name] = fn;
  83 |   }
  84 | }
     ...
  86 | export = Helper;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-definition-changed-definition-1c2318/repro.json
```

## Evidence and reduction

- representative fd88e2717131-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects hexojs/hexo@751e856691bf, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#1673](https://github.com/microsoft/typescript-go/issues/1673) Panic on textDocument/definition (closed, 2025-09-03, 8 comments)
- [microsoft/typescript-go#2183](https://github.com/microsoft/typescript-go/issues/2183) cannot resolve type definition with type:module (closed, 2025-12-03, 8 comments)
- [microsoft/typescript-go#3026](https://github.com/microsoft/typescript-go/issues/3026) TypeScript Native Preview VS Code extension status bar color is confusing (closed, 2026-03-09, 3 comments)
- [microsoft/typescript-go#2598](https://github.com/microsoft/typescript-go/issues/2598) Auto-imports broken in JS files when user preferences are used (closed, 2026-01-28, 16 comments)
- [microsoft/typescript-go#829](https://github.com/microsoft/typescript-go/issues/829) const enum is not work (closed, 2025-04-27, 8 comments)
- [microsoft/typescript-go#4863](https://github.com/microsoft/typescript-go/issues/4863) TS7 fails to emit types for `@type`-annotated functions when they reference externally-defined symbols (closed, 2026-08-10, 0 comments)
- [microsoft/typescript-go#4740](https://github.com/microsoft/typescript-go/issues/4740) Divergence from tsc: assignment accepted by 5.9/6.0 is rejected by `tsgo` (recursive DeepPartial + contravariant `this` + UnionToIntersection cycle, reduced from chart.js) (closed, 2026-07-25, 2 comments)
- [microsoft/typescript-go#4388](https://github.com/microsoft/typescript-go/issues/4388) Parameters not automatically filled for JSdoc comments (closed, 2026-06-22, 9 comments)
- queries: `definition wrong repo:microsoft/typescript-go is:issue`; `definition "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr1c2318-r6-replay-test-baseline-20261118-221847-f23073] stderr: context canceled
[ts7-7.0.2-tr1c2318-r6-replay-test-control-20261118-221853-5b662c] stderr: context canceled
```
