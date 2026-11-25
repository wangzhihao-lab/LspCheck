# [ts7 7.0.2] documentSymbol changes its answer after transformation T3

Draft for the author (not filed). Group `ts7-r5-documentsymbol-changed-t3-8eae6d`, signature `ts7|r5_transforms|documentSymbol:changed`, case family `T3`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `reduxjs/redux@fb3bad6804d6` (corpus, commit fb3bad6804d651b8ae0e909f32765beb989ba6f8), language typescript

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T3 applied to `website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts` (357 edit(s), first [16, 30, 16, 30]).
3. Query `textDocument/documentSymbol` on `website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "(typeof node.meta === 'string' && {\n                meta: node.meta.replace(\n                  /(title=['\"].*)\\.t(sx?)(.*\")/,\n                  '$1.j$...",
  7,
  350,
  14,
  355,
  16
 ],
 [
  "CodeNode",
  11,
  22,
  0,
  27,
  1
 ],
 [
  "Compiler",
  13,
  3,
  9,
  3,
  17
 ],
 [
  "CompilerSettings",
  13,
  4,
  14,
  4,
  30
 ],
 [
  "ImportDeclaration",
  13,
  12,
  14,
  12,
  31
 ],
 [
  "MdxJsxFlowElement",
  13,
  14,
  14,
  14,
  31
 ],
 [
  "MdxjsEsm",
  13,
  13,
  14,
  13,
  22
 ],
 [
  "Node",
  13,
  10,
  14,
  10,
  18
 ],
 [
  "Parent",
  13,
  10,
  20,
  10,
  26
 ],
 [
  "Plugin",
  13,
  9,
  14,
  9,
  20
 ],
 [
  "PostProcessor",
  5,
  29,
  0,
  33,
  18
 ],
 [
  "TranspileCodeblocksSettings",
  11,
  35,
  0,
  41,
  1
 ],
 [
  "TranspiledFile",
  13,
  4,
  32,
  4,
  46
 ],
 [
  "VFile",
  13,
  11,
  14,
  11,
  19
 ],
 [
  "VirtualFile",
  11,
  16,
  0,
  19,
  1
 ],
 [
  "VirtualFiles",
  5,
  20,
  0,
  20,
  55
 ],
 [
  "assembleReplacementNodes",
  13,
  50,
  4,
  50,
  62
 ],
 [
  "assembleReplacementNodes",
  7,
  39,
  2,
  39,
  68
 ],
 [
  "attributes",
  7,
  227,
  6,
  326,
  7
 ],
 [
  "attributes",
  7,
  331,
  10,
  331,
  79
 ],
 [
  "attributes",
  7,
  345,
  10,
  345,
  79
 ],
 [
  "body",
  7,
  127,
  16,
  144,
  17
 ],
 [
  "body",
  7,
  240,
  16,
  319,
  17
 ],
 [
  "body",
  7,
  97,
  16,
  114,
  17
 ],
 [
  "children",
  7,
  327,
  6,
  367,
  7
 ],
 [
  "children",
  7,
  332,
  10,
  3
... (10235 characters)
```

Actual:

```json
[
 [
  "(typeof node.meta === 'string' && {  \t\n                meta: node.meta.replace(\n                  /(title=['\"].*)\\.t(sx?)(.*\")/,\n                  '$1...",
  7,
  350,
  14,
  355,
  16
 ],
 [
  "CodeNode",
  11,
  22,
  0,
  27,
  1
 ],
 [
  "Compiler",
  13,
  3,
  9,
  3,
  17
 ],
 [
  "CompilerSettings",
  13,
  4,
  14,
  4,
  30
 ],
 [
  "ImportDeclaration",
  13,
  12,
  14,
  12,
  31
 ],
 [
  "MdxJsxFlowElement",
  13,
  14,
  14,
  14,
  31
 ],
 [
  "MdxjsEsm",
  13,
  13,
  14,
  13,
  22
 ],
 [
  "Node",
  13,
  10,
  14,
  10,
  18
 ],
 [
  "Parent",
  13,
  10,
  20,
  10,
  26
 ],
 [
  "Plugin",
  13,
  9,
  14,
  9,
  20
 ],
 [
  "PostProcessor",
  5,
  29,
  0,
  33,
  18
 ],
 [
  "TranspileCodeblocksSettings",
  11,
  35,
  0,
  41,
  1
 ],
 [
  "TranspiledFile",
  13,
  4,
  32,
  4,
  46
 ],
 [
  "VFile",
  13,
  11,
  14,
  11,
  19
 ],
 [
  "VirtualFile",
  11,
  16,
  0,
  19,
  1
 ],
 [
  "VirtualFiles",
  5,
  20,
  0,
  20,
  55
 ],
 [
  "assembleReplacementNodes",
  13,
  50,
  4,
  50,
  62
 ],
 [
  "assembleReplacementNodes",
  7,
  39,
  2,
  39,
  68
 ],
 [
  "attributes",
  7,
  227,
  6,
  326,
  7
 ],
 [
  "attributes",
  7,
  331,
  10,
  331,
  79
 ],
 [
  "attributes",
  7,
  345,
  10,
  345,
  79
 ],
 [
  "body",
  7,
  127,
  16,
  144,
  17
 ],
 [
  "body",
  7,
  240,
  16,
  319,
  17
 ],
 [
  "body",
  7,
  97,
  16,
  114,
  17
 ],
 [
  "children",
  7,
  327,
  6,
  367,
  7
 ],
 [
  "children",
  7,
  332,
  10,
  
... (10236 characters)
```

Project file `website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts`:

```
   1 | import { visit } from 'unist-util-visit';
   2 | // @ts-ignore
   3 | import flatMap from 'unist-util-flatmap';
     ...
 348 |             {
 349 |               ...node,
 350 |               lang: 'js',
 351 |               ...(typeof node.meta === 'string' && {
 352 |                 meta: node.meta.replace(
 353 |                   /(title=['"].*)\.t(sx?)(.*")/,
 354 |                   '$1.j$2$3'
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r5-documentsymbol-changed-t3-8eae6d/repro.json
```

## Evidence and reduction

- representative 89cafd55dfec-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 358 -> 2 (14 probes, 244.774 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects reduxjs/redux@fb3bad6804d6, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#1439](https://github.com/microsoft/typescript-go/issues/1439) Support `LocationLink` in go-to-definition (closed, 2025-07-23, 2 comments)
- queries: `"trailing whitespace" in:title repo:microsoft/typescript-go is:issue`; `"document symbol" wrong repo:microsoft/typescript-go is:issue`; `"document symbol" "trailing whitespace" repo:microsoft/typescript-go is:issue`; `"document symbol" whitespace repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr8eae6d-r5-replay-baseline-20260925-160948-4a105f] stderr: context canceled
[ts7-7.0.2-tr8eae6d-r5-replay-case-20260925-160959-ab6661] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr8eae6d-r5-replay-case-20260925-160959-ab6661] stderr: context canceled
[ts7-7.0.2-tr8eae6d-r5-replay-control-20260925-160952-917bd1] stderr: context canceled
```
