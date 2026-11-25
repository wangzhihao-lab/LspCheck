# [ts7 7.0.2] foldingRange adds entries after transformation T2

Draft for the author (not filed). Group `ts7-r5-foldingrange-extra-t2-5dd83a`, signature `ts7|r5_transforms|foldingRange:extra`, case family `T2`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `vadimdemedes/ink@02ae1e59e7c2` (corpus, commit 02ae1e59e7c288e971616100c4c11bcca6b5761b), language typescript

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T2 applied to `test/fixtures/issue-935-overflow-rerender.tsx` (1 edit(s), first [2, 0, 2, 0]).
3. Query `textDocument/foldingRange` on `test/fixtures/issue-935-overflow-rerender.tsx` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  1,
  74,
  "imports"
 ],
 [
  12,
  26,
  21,
  2,
  ""
 ],
 [
  12,
  27,
  21,
  1,
  ""
 ],
 [
  13,
  1,
  15,
  47,
  "comment"
 ],
 [
  17,
  1,
  18,
  71,
  "comment"
 ],
 [
  19,
  29,
  20,
  64,
  ""
 ],
 [
  20,
  43,
  20,
  64,
  ""
 ],
 [
  8,
  42,
  10,
  1,
  ""
 ],
 [
  9,
  22,
  9,
  50,
  ""
 ]
]
```

Actual:

```json
[
 [
  0,
  0,
  1,
  74,
  "imports"
 ],
 [
  12,
  26,
  21,
  2,
  ""
 ],
 [
  12,
  27,
  21,
  1,
  ""
 ],
 [
  13,
  1,
  15,
  47,
  "comment"
 ],
 [
  17,
  1,
  18,
  71,
  "comment"
 ],
 [
  19,
  29,
  20,
  64,
  ""
 ],
 [
  20,
  43,
  20,
  64,
  ""
 ],
 [
  3,
  0,
  6,
  76,
  "comment"
 ],
 [
  8,
  42,
  10,
  1,
  ""
 ],
 [
  9,
  22,
  9,
  50,
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r5-foldingrange-extra-t2-5dd83a/repro.json
```

## Evidence and reduction

- representative 9932809db252-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4722](https://github.com/microsoft/typescript-go/issues/4722) Nested nullish coalescing + comment + ES2018 causes function body to be ignored (closed, 2026-07-23, 1 comments)
- [microsoft/typescript-go#4684](https://github.com/microsoft/typescript-go/issues/4684) VS Code extension does not provide completions for directive comments (closed, 2026-07-20, 4 comments)
- [microsoft/typescript-go#3659](https://github.com/microsoft/typescript-go/issues/3659) Behavior difference: JSDoc comments are stripped for mapped types (closed, 2026-04-29, 2 comments)
- [microsoft/typescript-go#4388](https://github.com/microsoft/typescript-go/issues/4388) Parameters not automatically filled for JSdoc comments (closed, 2026-06-22, 9 comments)
- [microsoft/typescript-go#4016](https://github.com/microsoft/typescript-go/issues/4016) @fileoverview breaks @jsx comments (closed, 2026-05-20, 0 comments)
- queries: `comment in:title repo:microsoft/typescript-go is:issue`; `"folding range" extra repo:microsoft/typescript-go is:issue`; `"folding range" comment repo:microsoft/typescript-go is:issue`; `"folding range" whitespace repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr5dd83a-r5-replay-baseline-20261118-220855-14b582] stderr: context canceled
[ts7-7.0.2-tr5dd83a-r5-replay-case-20261118-220917-cd7623] stderr: context canceled
[ts7-7.0.2-tr5dd83a-r5-replay-control-20261118-220903-4ac242] stderr: context canceled
```
