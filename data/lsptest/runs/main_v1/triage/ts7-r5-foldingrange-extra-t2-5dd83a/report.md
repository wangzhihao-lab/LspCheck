# [ts7 7.0.2] foldingRange adds entries after transformation T2

Draft for the author (not filed). Group `ts7-r5-foldingrange-extra-t2-5dd83a`, signature `ts7|r5_transforms|foldingRange:extra`, case family `T2`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `ChatGPTNextWeb/NextChat@defdcdb55d85` (corpus, commit defdcdb55d850cd12c4c657eb83729fd66e215c0), language typescript

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T2 applied to `app/components/mask.tsx` (1 edit(s), first [58, 0, 58, 0]).
3. Query `textDocument/foldingRange` on `app/components/mask.tsx` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  57,
  24,
  "imports"
 ],
 [
  100,
  21,
  100,
  100,
  ""
 ],
 [
  106,
  9,
  259,
  3,
  ""
 ],
 [
  107,
  4,
  258,
  7,
  ""
 ],
 [
  108,
  6,
  115,
  8,
  ""
 ],
 [
  110,
  35,
  114,
  9,
  ""
 ],
 [
  117,
  6,
  249,
  13,
  ""
 ],
 [
  118,
  8,
  118,
  52,
  ""
 ],
 [
  118,
  8,
  143,
  19,
  ""
 ],
 [
  119,
  10,
  130,
  11,
  ""
 ],
 [
  119,
  10,
  142,
  20,
  ""
 ],
 [
  121,
  14,
  126,
  15,
  ""
 ],
 [
  121,
  14,
  126,
  30,
  ""
 ],
 [
  122,
  40,
  125,
  17,
  ""
 ],
 [
  131,
  12,
  136,
  13,
  ""
 ],
 [
  131,
  12,
  141,
  18,
  ""
 ],
 [
  135,
  21,
  135,
  42,
  ""
 ],
 [
  137,
  14,
  140,
  16,
  ""
 ],
 [
  144,
  8,
  144,
  50,
  ""
 ],
 [
  144,
  8,
  155,
  19,
  ""
 ],
 [
  145,
  10,
  154,
  11,
  ""
 ],
 [
  145,
  10,
  154,
  19,
  ""
 ],
 [
  149,
  27,
  152,
  16,
  ""
 ],
 [
  150,
  30,
  152,
  16,
  ""
 ],
 [
  150,
  40,
  152,
  15,
  ""
 ],
 [
  156,
  8,
  159,
  9,
  ""
 ],
 [
  156,
  8,
  170,
  19,
  ""
 ],
 [
  16,
  7,
  23,
  1,
  ""
 ],
 [
  160,
  10,
  169,
  11,
  ""
 ],
 [
  160,
  10,
  169,
  19,
  ""
 ],
 [
  164,
  28,
  168,
  13,
  ""
 ],
 [
  165,
  30,
  167,
  16,
  ""
 ],
 [
  165,
  40,
  167,
  15,
  ""
 ],
 [
  172,
  41,
  188,
  9,
  ""
 ],
 [
  173,
  10,
  176,
  11,
  ""
 ],
 [
  173,
  10,
  187,
  21,
  ""
 ],
 [
  177,
  12,
  186,
  13,
  ""
 ],
 [
  177,
  12,
  186,
  21,
  ""
 ],
 [
  181,
  30,
  185,
  15,
  ""
 ],
 [
  182,
  32,
  184,
  18,
  "
... (10200 characters)
```

Actual:

```json
[
 [
  0,
  0,
  57,
  24,
  "imports"
 ],
 [
  100,
  21,
  100,
  100,
  ""
 ],
 [
  106,
  9,
  259,
  3,
  ""
 ],
 [
  107,
  4,
  258,
  7,
  ""
 ],
 [
  108,
  6,
  115,
  8,
  ""
 ],
 [
  110,
  35,
  114,
  9,
  ""
 ],
 [
  117,
  6,
  249,
  13,
  ""
 ],
 [
  118,
  8,
  118,
  52,
  ""
 ],
 [
  118,
  8,
  143,
  19,
  ""
 ],
 [
  119,
  10,
  130,
  11,
  ""
 ],
 [
  119,
  10,
  142,
  20,
  ""
 ],
 [
  121,
  14,
  126,
  15,
  ""
 ],
 [
  121,
  14,
  126,
  30,
  ""
 ],
 [
  122,
  40,
  125,
  17,
  ""
 ],
 [
  131,
  12,
  136,
  13,
  ""
 ],
 [
  131,
  12,
  141,
  18,
  ""
 ],
 [
  135,
  21,
  135,
  42,
  ""
 ],
 [
  137,
  14,
  140,
  16,
  ""
 ],
 [
  144,
  8,
  144,
  50,
  ""
 ],
 [
  144,
  8,
  155,
  19,
  ""
 ],
 [
  145,
  10,
  154,
  11,
  ""
 ],
 [
  145,
  10,
  154,
  19,
  ""
 ],
 [
  149,
  27,
  152,
  16,
  ""
 ],
 [
  150,
  30,
  152,
  16,
  ""
 ],
 [
  150,
  40,
  152,
  15,
  ""
 ],
 [
  156,
  8,
  159,
  9,
  ""
 ],
 [
  156,
  8,
  170,
  19,
  ""
 ],
 [
  16,
  7,
  23,
  1,
  ""
 ],
 [
  160,
  10,
  169,
  11,
  ""
 ],
 [
  160,
  10,
  169,
  19,
  ""
 ],
 [
  164,
  28,
  168,
  13,
  ""
 ],
 [
  165,
  30,
  167,
  16,
  ""
 ],
 [
  165,
  40,
  167,
  15,
  ""
 ],
 [
  172,
  41,
  188,
  9,
  ""
 ],
 [
  173,
  10,
  176,
  11,
  ""
 ],
 [
  173,
  10,
  187,
  21,
  ""
 ],
 [
  177,
  12,
  186,
  13,
  ""
 ],
 [
  177,
  12,
  186,
  21,
  ""
 ],
 [
  181,
  30,
  185,
  15,
  ""
 ],
 [
  182,
  32,
  184,
  18,
  "
... (10242 characters)
```

Project file `app/components/mask.tsx`:

```
   1 | import { IconButton } from "./button";
   2 | import { ErrorBoundary } from "./error";
     ...
  56 | } from "@hello-pangea/dnd";
  57 | import { getMessageTextContent } from "../utils";
  58 | import clsx from "clsx";
     ...
  60 | // drag and drop helper function
  61 | function reorder<T>(list: T[], startIndex: number, endIndex: number): T[] {
  62 |   const result = [...list];
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r5-foldingrange-extra-t2-5dd83a/repro.json
```

## Evidence and reduction

- representative ba0ac55b3486-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4722](https://github.com/microsoft/typescript-go/issues/4722) Nested nullish coalescing + comment + ES2018 causes function body to be ignored (closed, 2026-07-23, 1 comments)
- [microsoft/typescript-go#4684](https://github.com/microsoft/typescript-go/issues/4684) VS Code extension does not provide completions for directive comments (closed, 2026-07-20, 4 comments)
- [microsoft/typescript-go#3659](https://github.com/microsoft/typescript-go/issues/3659) Behavior difference: JSDoc comments are stripped for mapped types (closed, 2026-04-29, 2 comments)
- [microsoft/typescript-go#4388](https://github.com/microsoft/typescript-go/issues/4388) Parameters not automatically filled for JSdoc comments (closed, 2026-06-22, 9 comments)
- [microsoft/typescript-go#4016](https://github.com/microsoft/typescript-go/issues/4016) @fileoverview breaks @jsx comments (closed, 2026-05-20, 0 comments)
- queries: `comment in:title repo:microsoft/typescript-go is:issue`; `"folding range" extra repo:microsoft/typescript-go is:issue`; `"folding range" comment repo:microsoft/typescript-go is:issue`; `"folding range" whitespace repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr5dd83a-r5-replay-baseline-20260925-161709-9d9a1d] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr5dd83a-r5-replay-baseline-20260925-161709-9d9a1d] stderr: context canceled
[ts7-7.0.2-tr5dd83a-r5-replay-case-20260925-161841-e0dae1] stderr: context canceled
[ts7-7.0.2-tr5dd83a-r5-replay-control-20260925-161735-a3ff82] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr5dd83a-r5-replay-control-20260925-161735-a3ff82] stderr: context canceled
```
