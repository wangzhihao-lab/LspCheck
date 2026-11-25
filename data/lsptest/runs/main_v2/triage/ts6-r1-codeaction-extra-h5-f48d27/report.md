# [ts6 6.0.3] codeAction adds entries after file rename round trip

Draft for the author (not filed). Group `ts6-r1-codeaction-extra-h5-f48d27`, signature `ts6|r1_history|codeAction:extra`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `hexojs/hexo@751e856691bf` (corpus, commit 751e856691bfe24182cf8763feb29db0422dcfee), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open test/scripts/tags/blockquote.ts`
3. Timing: wait until the server is idle after every step.
4. textDocument/didOpen `lib/hexo/scaffold.ts`, `test/fixtures/post_render.ts` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/codeAction` on `test/scripts/tags/blockquote.ts` line 4, column 1 (LSP position {line: 3, character: 0}) (diag:3:8); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Move to a new file",
  "refactor.move.newFile"
 ]
]
```

Actual:

```json
[
 [
  "Add all missing imports",
  "quickfix"
 ],
 [
  "Add import from \"node:test\"",
  "quickfix"
 ],
 [
  "Move to a new file",
  "refactor.move.newFile"
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-codeaction-extra-h5-f48d27/repro.json
```

## Evidence and reduction

- representative a1d24603cbb6-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 1 (8 probes, 185.38 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects hexojs/hexo@751e856691bf, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#235](https://github.com/typescript-language-server/typescript-language-server/issues/235) Support for auto-import all (closed, 2021-07-11, 10 comments)
- [typescript-language-server/typescript-language-server#894](https://github.com/typescript-language-server/typescript-language-server/issues/894) How to Disable "Move to a new file" action? (closed, 2024-05-09, 2 comments)
- [microsoft/TypeScript#30039](https://github.com/microsoft/TypeScript/issues/30039) Refactor rename file + rename function (open, 2019-01-23, 6 comments)
- [microsoft/TypeScript#29294](https://github.com/microsoft/TypeScript/issues/29294) Rename file when renaming default export (open, 2019-01-05, 0 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `"code action" extra repo:typescript-language-server/typescript-language-server is:issue`; `"code action" "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `"code action" stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `"code action" extra repo:microsoft/TypeScript is:issue`; `"code action" "rename file" repo:microsoft/TypeScript is:issue`; `"code action" stale repo:microsoft/TypeScript is:issue`
