# [ts6 6.0.3] foldingRange adds entries after transformation T2

Draft for the author (not filed). Group `ts6-r5-foldingrange-extra-t2-625065`, signature `ts6|r5_transforms|foldingRange:extra`, case family `T2`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `ChatGPTNextWeb/NextChat@defdcdb55d85` (corpus, commit defdcdb55d850cd12c4c657eb83729fd66e215c0), language typescript

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T2 applied to `app/components/mask.tsx` (1 edit(s), first [58, 0, 58, 0]).
3. Query `textDocument/foldingRange` on `app/components/mask.tsx` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  -1,
  57,
  -1,
  "imports"
 ],
 [
  100,
  -1,
  100,
  -1,
  ""
 ],
 [
  106,
  -1,
  259,
  -1,
  ""
 ],
 [
  107,
  -1,
  258,
  -1,
  ""
 ],
 [
  109,
  -1,
  113,
  -1,
  ""
 ],
 [
  110,
  -1,
  113,
  -1,
  ""
 ],
 [
  117,
  -1,
  249,
  -1,
  ""
 ],
 [
  118,
  -1,
  118,
  -1,
  ""
 ],
 [
  118,
  -1,
  143,
  -1,
  ""
 ],
 [
  119,
  -1,
  142,
  -1,
  ""
 ],
 [
  120,
  -1,
  128,
  -1,
  ""
 ],
 [
  121,
  -1,
  126,
  -1,
  ""
 ],
 [
  122,
  -1,
  124,
  -1,
  ""
 ],
 [
  131,
  -1,
  141,
  -1,
  ""
 ],
 [
  132,
  -1,
  134,
  -1,
  ""
 ],
 [
  135,
  -1,
  135,
  -1,
  ""
 ],
 [
  138,
  -1,
  138,
  -1,
  ""
 ],
 [
  144,
  -1,
  144,
  -1,
  ""
 ],
 [
  144,
  -1,
  155,
  -1,
  ""
 ],
 [
  145,
  -1,
  154,
  -1,
  ""
 ],
 [
  146,
  -1,
  152,
  -1,
  ""
 ],
 [
  149,
  -1,
  152,
  -1,
  ""
 ],
 [
  150,
  -1,
  151,
  -1,
  ""
 ],
 [
  150,
  -1,
  152,
  -1,
  ""
 ],
 [
  156,
  -1,
  170,
  -1,
  ""
 ],
 [
  157,
  -1,
  157,
  -1,
  ""
 ],
 [
  16,
  -1,
  22,
  -1,
  ""
 ],
 [
  160,
  -1,
  169,
  -1,
  ""
 ],
 [
  161,
  -1,
  167,
  -1,
  ""
 ],
 [
  164,
  -1,
  167,
  -1,
  ""
 ],
 [
  165,
  -1,
  166,
  -1,
  ""
 ],
 [
  165,
  -1,
  167,
  -1,
  ""
 ],
 [
  172,
  -1,
  188,
  -1,
  ""
 ],
 [
  173,
  -1,
  187,
  -1,
  ""
 ],
 [
  174,
  -1,
  174,
  -1,
  ""
 ],
 [
  177,
  -1,
  186,
  -1,
  ""
 ],
 [
  178,
  -1,
  184,
  -1,
  ""
 ],
 [
  181,
  -1,
  184,
  -1,
  ""
 ],
 [
  182,
  -1,
  183,
  -1,
  ""
 ],
 [
  182,
  -1
... (9891 characters)
```

Actual:

```json
[
 [
  0,
  -1,
  57,
  -1,
  "imports"
 ],
 [
  100,
  -1,
  100,
  -1,
  ""
 ],
 [
  106,
  -1,
  259,
  -1,
  ""
 ],
 [
  107,
  -1,
  258,
  -1,
  ""
 ],
 [
  109,
  -1,
  113,
  -1,
  ""
 ],
 [
  110,
  -1,
  113,
  -1,
  ""
 ],
 [
  117,
  -1,
  249,
  -1,
  ""
 ],
 [
  118,
  -1,
  118,
  -1,
  ""
 ],
 [
  118,
  -1,
  143,
  -1,
  ""
 ],
 [
  119,
  -1,
  142,
  -1,
  ""
 ],
 [
  120,
  -1,
  128,
  -1,
  ""
 ],
 [
  121,
  -1,
  126,
  -1,
  ""
 ],
 [
  122,
  -1,
  124,
  -1,
  ""
 ],
 [
  131,
  -1,
  141,
  -1,
  ""
 ],
 [
  132,
  -1,
  134,
  -1,
  ""
 ],
 [
  135,
  -1,
  135,
  -1,
  ""
 ],
 [
  138,
  -1,
  138,
  -1,
  ""
 ],
 [
  144,
  -1,
  144,
  -1,
  ""
 ],
 [
  144,
  -1,
  155,
  -1,
  ""
 ],
 [
  145,
  -1,
  154,
  -1,
  ""
 ],
 [
  146,
  -1,
  152,
  -1,
  ""
 ],
 [
  149,
  -1,
  152,
  -1,
  ""
 ],
 [
  150,
  -1,
  151,
  -1,
  ""
 ],
 [
  150,
  -1,
  152,
  -1,
  ""
 ],
 [
  156,
  -1,
  170,
  -1,
  ""
 ],
 [
  157,
  -1,
  157,
  -1,
  ""
 ],
 [
  16,
  -1,
  22,
  -1,
  ""
 ],
 [
  160,
  -1,
  169,
  -1,
  ""
 ],
 [
  161,
  -1,
  167,
  -1,
  ""
 ],
 [
  164,
  -1,
  167,
  -1,
  ""
 ],
 [
  165,
  -1,
  166,
  -1,
  ""
 ],
 [
  165,
  -1,
  167,
  -1,
  ""
 ],
 [
  172,
  -1,
  188,
  -1,
  ""
 ],
 [
  173,
  -1,
  187,
  -1,
  ""
 ],
 [
  174,
  -1,
  174,
  -1,
  ""
 ],
 [
  177,
  -1,
  186,
  -1,
  ""
 ],
 [
  178,
  -1,
  184,
  -1,
  ""
 ],
 [
  181,
  -1,
  184,
  -1,
  ""
 ],
 [
  182,
  -1,
  183,
  -1,
  ""
 ],
 [
  182,
  -1
... (9934 characters)
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r5-foldingrange-extra-t2-625065/repro.json
```

## Evidence and reduction

- representative 775a755c313e-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, timings settled, seeds 2

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
