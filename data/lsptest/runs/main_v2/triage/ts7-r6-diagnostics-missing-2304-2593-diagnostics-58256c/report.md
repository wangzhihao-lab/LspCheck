# [ts7 7.0.2] diagnostics differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-diagnostics-missing-2304-2593-diagnostics-58256c`, signature `ts7|r6_crossimpl|diagnostics:missing:2304,2593`, case family `diagnostics`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `hexojs/hexo@751e856691bf` (corpus, commit 751e856691bfe24182cf8763feb29db0422dcfee), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/diagnostic` on `test/scripts/theme_processors/source.ts` for the whole file; compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  10,
  0,
  10,
  8,
  0,
  "2593",
  "",
  ""
 ],
 [
  125,
  2,
  125,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  141,
  2,
  141,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  16,
  19,
  16,
  26,
  0,
  "7006",
  "",
  ""
 ],
 [
  26,
  2,
  26,
  8,
  0,
  "2304",
  "",
  ""
 ],
 [
  34,
  2,
  34,
  7,
  0,
  "2304",
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
  51,
  2,
  51,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  72,
  2,
  72,
  4,
  0,
  "2593",
  "",
  ""
 ],
 [
  99,
  2,
  99,
  4,
  0,
  "2593",
  "",
  ""
 ]
]
```

Actual:

```json
[
 [
  16,
  19,
  16,
  26,
  0,
  "7006",
  "",
  ""
 ]
]
```

Project file `test/scripts/theme_processors/source.ts`:

```
   1 | import { join } from 'path';
   2 | import { mkdirs, rmdir, unlink, writeFile } from 'hexo-fs';
   3 | import BluebirdPromise from 'bluebird';
   4 | import Hexo from '../../../lib/hexo';
   5 | import { source } from '../../../lib/theme/processors/source';
   6 | import chai from 'chai';
   7 | const should = chai.should();
   8 | type SourceParams = Parameters<typeof source['process']>
   9 | type SourceReturn = ReturnType<typeof source['process']>
     ...
  11 | describe('source', () => {
  12 |   const hexo = new Hexo(join(__dirname, 'source_test'), {silent: true});
  13 |   const process: (...args: SourceParams) => BluebirdPromise<SourceReturn> = BluebirdPromise.method(source.process.bind(hexo));
  14 |   const themeDir = join(hexo.base_dir, 'themes', 'test');
  15 |   const Asset = hexo.model('Asset');
     ...
  17 |   function newFile(options) {
  18 |     const { path } = options;
     ...
  20 |     options.params = {path};
  21 |     options.path = 'source/' + path;
  22 |     options.source = join(themeDir, options.path);
     ...
  24 |     return new hexo.theme.File(options);
  25 |   }
     ...
  27 |   before(async () => {
  28 |     await BluebirdPromise.all([
  29 |       mkdirs(themeDir),
  30 |       writeFile(hexo.config_path, 'theme: test')
  31 |     ]);
  32 |     await hexo.init();
  33 |   });
     ...
  35 |   after(() => rmdir(hexo.base_dir));
     ...
  37 |   it('pattern', () => {
  38 |     const { pattern } = source;
     ...
  40 |     pattern.match('source/foo.jpg').should.eql({path: 'foo.jpg'});
  41 |     pattern.match('source/_foo.jpg').should.be.false;
  42 |     pattern.match('source/foo/_bar.jpg').should.be.false;
  43 |     pattern.match('source/foo.jpg~').should.be.false;
  44 |     pattern.match('source/foo.jpg%').should.be.false;
  45 |     pattern.match('layout/foo.swig').should.be.false;
  46 |     pattern.match('layout/foo.njk').should.be.false;
  47 |     pattern.match('package.json').should.be.false;
  48 |     pattern.match('node_modules/test/test.js').should.be.false;
  49 |     pattern.match('source/node_modules/test/test.js').should.be.false;
  50 |   });
     ...
  52 |   it('type: create', async () => {
  53 |     const file = newFile({
  54 |       path: 'style.css',
  55 |       type: 'create'
  56 |     });
     ...
  58 |     const id = 'themes/test/' + file.path;
     ...
  60 |     await writeFile(file.source, 'test');
  61 |     await process(file);
  62 |     const asset = Asset.findById(id);
     ...
  64 |     asset._id.should.eql(id);
  65 |     asset.path.should.eql(file.params.path);
  66 |     asset.modified.should.be.true;
     ...
  68 |     asset.remove();
     ...
  70 |     unlink(file.source);
  71 |   });
     ...
  73 |   it('type: update', async () => {
  74 |     const file = newFile({
  75 |       path: 'style.css',
  76 |       type: 'update'
  77 |     });
     ...
  79 |     const id = 'themes/test/' + file.path;
     ...
  81 |     await BluebirdPromise.all([
  82 |       writeFile(file.source, 'test'),
  83 |       Asset.insert({
  84 |         _id: id,
  85 |         path: file.params.path,
  86 |         modified: false
  87 |       })
  88 |     ]);
  89 |     await process(file);
  90 |     const asset = Asset.findById(id);
     ...
  92 |     asset.modified.should.be.true;
     ...
  94 |     await BluebirdPromise.all([
  95 |       unlink(file.source),
  96 |       Asset.removeById(id)
  97 |     ]);
  98 |   });
     ...
 100 |   it('type: skip', async () => {
 101 |     const file = newFile({
 102 |       path: 'style.css',
 103 |       type: 'skip'
 104 |     });
     ...
 106 |     const id = 'themes/test/' + file.path;
     ...
 108 |     await BluebirdPromise.all([
 109 |       writeFile(file.source, 'test'),
 110 |       Asset.insert({
 111 |         _id: id,
 112 |         path: file.params.path,
 113 |         modified: false
 114 |       })
 115 |     ]);
 116 |     await process(file);
 117 |     const asset = Asset.findById(id);
     ...
 119 |     asset.modified.should.be.false;
 120 |     await BluebirdPromise.all([
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-diagnostics-missing-2304-2593-diagnostics-58256c/repro.json
```

## Evidence and reduction

- representative fd88e2717131-v04: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects hexojs/hexo@751e856691bf, timings settled, seeds 1

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
[ts7-7.0.2-tr58256c-r6-replay-test-baseline-20261118-222902-e7fe74] stderr: context canceled
[ts7-7.0.2-tr58256c-r6-replay-test-baseline-20261118-222902-e7fe74] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr58256c-r6-replay-test-control-20261118-222913-e86fed] stderr: context canceled
```
