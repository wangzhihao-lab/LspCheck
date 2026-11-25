# [ts6 6.0.3] foldingRange adds entries after transformation T2

Draft for the author (not filed). Group `ts6-r5-foldingrange-extra-t2-625065`, signature `ts6|r5_transforms|foldingRange:extra`, case family `T2`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `vadimdemedes/ink@02ae1e59e7c2` (corpus, commit 02ae1e59e7c288e971616100c4c11bcca6b5761b), language typescript

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T2 applied to `test/fixtures/issue-935-overflow-rerender.tsx` (1 edit(s), first [2, 0, 2, 0]).
3. Query `textDocument/foldingRange` on `test/fixtures/issue-935-overflow-rerender.tsx` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  -1,
  1,
  -1,
  "imports"
 ],
 [
  12,
  -1,
  20,
  -1,
  ""
 ],
 [
  12,
  -1,
  21,
  -1,
  ""
 ],
 [
  13,
  -1,
  15,
  -1,
  "comment"
 ],
 [
  17,
  -1,
  18,
  -1,
  "comment"
 ],
 [
  19,
  -1,
  20,
  -1,
  ""
 ],
 [
  20,
  -1,
  20,
  -1,
  ""
 ],
 [
  8,
  -1,
  9,
  -1,
  ""
 ],
 [
  9,
  -1,
  9,
  -1,
  ""
 ]
]
```

Actual:

```json
[
 [
  0,
  -1,
  1,
  -1,
  "imports"
 ],
 [
  12,
  -1,
  20,
  -1,
  ""
 ],
 [
  12,
  -1,
  21,
  -1,
  ""
 ],
 [
  13,
  -1,
  15,
  -1,
  "comment"
 ],
 [
  17,
  -1,
  18,
  -1,
  "comment"
 ],
 [
  19,
  -1,
  20,
  -1,
  ""
 ],
 [
  20,
  -1,
  20,
  -1,
  ""
 ],
 [
  3,
  -1,
  6,
  -1,
  "comment"
 ],
 [
  8,
  -1,
  9,
  -1,
  ""
 ],
 [
  9,
  -1,
  9,
  -1,
  ""
 ]
]
```

Project file `test/fixtures/issue-935-overflow-rerender.tsx`:

```
   1 | import process from 'node:process';
   2 | import {runIssue450RerenderFixture} from './issue-450-fixture-helpers.js';
     ...
   4 | // Pre-existing terminal output that must survive Ink's full-clear fallback.
   5 | const rows = Number(process.argv[2]) || 6;
   6 | for (let index = 0; index < rows; index++) {
   7 | 	process.stdout.write(`#935 scrollback ${index}\n`);
   8 | }
     ...
  10 | runIssue450RerenderFixture({
  11 | 	// Overflow by exactly one row: only the top row scrolls into scrollback per
  12 | 	// frame, so the label row below it stays in the viewport, where a full clear
  13 | 	// erases it before the next frame is written.
  14 | 	heightForFrame: rows => rows + 1,
  15 | 	// One frame's label is longer than the others, so an incomplete clear leaves
  16 | 	// its tail behind (`#450 topSTALE-ROW`) instead of being overwritten.
  17 | 	labelForFrame: frameCount =>
  18 | 		frameCount === 7 ? 'frame 7 STALE-ROW' : `frame ${frameCount}`,
  19 | });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r5-foldingrange-extra-t2-625065/repro.json
```

## Evidence and reduction

- representative df77a21aa659-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#180](https://github.com/typescript-language-server/typescript-language-server/issues/180) Support onTypeFormatting to format comment blocks (open, 2021-01-17, 13 comments)
- [microsoft/TypeScript#64405](https://github.com/microsoft/TypeScript/issues/64405) Incremental check emits locationless TS2589 after a comment-only edit in TypeScript 7 (open, 2026-09-23, 5 comments)
- [microsoft/TypeScript#54338](https://github.com/microsoft/TypeScript/issues/54338) Comment referencing an undefined `ClassDecoratorFunction` type (open, 2023-05-21, 1 comments)
- [microsoft/TypeScript#63841](https://github.com/microsoft/TypeScript/issues/63841) Behavior difference: Comment above `@typedef` does not become comment for the corresponding emitted type in tsgo (open, 2026-06-18, 0 comments)
- [microsoft/TypeScript#63789](https://github.com/microsoft/TypeScript/issues/63789) Inherited methods not merging JSDoc comments (open, 2025-12-06, 6 comments)
- [microsoft/TypeScript#63358](https://github.com/microsoft/TypeScript/issues/63358) TSX error location error with location and JSX comment (open, 2026-04-06, 5 comments)
- [microsoft/TypeScript#49219](https://github.com/microsoft/TypeScript/issues/49219) Allow overriding folding ranges (closed, 2022-05-23, 4 comments)
- [microsoft/TypeScript#23380](https://github.com/microsoft/TypeScript/issues/23380) getOutliningSpans - Return spans for case bodies (closed, 2018-04-12, 3 comments)
- queries: `comment in:title repo:typescript-language-server/typescript-language-server is:issue`; `"folding range" extra repo:typescript-language-server/typescript-language-server is:issue`; `"folding range" comment repo:typescript-language-server/typescript-language-server is:issue`; `"folding range" whitespace repo:typescript-language-server/typescript-language-server is:issue`; `comment in:title repo:microsoft/TypeScript is:issue`; `"folding range" extra repo:microsoft/TypeScript is:issue`; `"folding range" comment repo:microsoft/TypeScript is:issue`; `"folding range" whitespace repo:microsoft/TypeScript is:issue`
