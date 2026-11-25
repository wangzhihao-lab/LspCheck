# [ts6 6.0.3] semanticTokens misses entries after edit inside a workspace window

Draft for the author (not filed). Group `ts6-r1-semantictokens-missing-h9-d686b3`, signature `ts6|r1_history|semanticTokens:missing`, case family `H9`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `reduxjs/redux@fb3bad6804d6` (corpus, commit fb3bad6804d651b8ae0e909f32765beb989ba6f8), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts`
3. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts -> website/plugins/remark-typescript-tools/transpileCodeblocks/plugin_rt.ts`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename website/plugins/remark-typescript-tools/transpileCodeblocks/plugin_rt.ts -> website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `test/helpers/reducers.ts`, `test/typescript/enhancers.test-d.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/semanticTokens/full` on `website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  16,
  17,
  11,
  "interface",
  "declaration"
 ],
 [
  17,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  18,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  20,
  12,
  12,
  "type",
  "declaration"
 ],
 [
  20,
  27,
  6,
  "type",
  "defaultLibrary"
 ],
 [
  20,
  42,
  11,
  "interface",
  ""
 ],
 [
  22,
  10,
  8,
  "interface",
  "declaration"
 ],
 [
  23,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  24,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  25,
  2,
  5,
  "property",
  "declaration"
 ],
 [
  26,
  2,
  6,
  "property",
  "declaration"
 ],
 [
  29,
  5,
  13,
  "type",
  "declaration"
 ],
 [
  30,
  2,
  5,
  "parameter",
  "declaration"
 ],
 [
  30,
  9,
  12,
  "type",
  ""
 ],
 [
  31,
  2,
  10,
  "parameter",
  "declaration"
 ],
 [
  32,
  2,
  16,
  "function",
  "declaration"
 ],
 [
  32,
  21,
  13,
  "type",
  ""
 ],
 [
  33,
  5,
  12,
  "type",
  ""
 ],
 [
  35,
  17,
  27,
  "interface",
  "declaration"
 ],
 [
  36,
  2,
  16,
  "property",
  "declaration"
 ],
 [
  36,
  20,
  16,
  "interface",
  ""
 ],
 [
  37,
  2,
  23,
  "member",
  "declaration"
 ],
 [
  37,
  28,
  13,
  "type",
  ""
 ],
 [
  38,
  2,
  13,
  "member",
  "declaration"
 ],
 [
  38,
  18,
  13,
  "type",
  ""
 ],
 [
  39,
  2,
  24,
  "member",
  "declaration"
 ],
 [
  39,
  36,
  31,
  "function",
  ""
 ],
 [
  40,
  2,
  14,
  "property",
  "declaration"
 ],
 [
  43,
  6,
  9,
  "variable",
  "declaration,readonly"
 ],
 [
  43,
  22,
  7,
  "class",
  "defa
... (22368 characters)
```

Actual:

```json
[
 [
  16,
  17,
  11,
  "interface",
  "declaration"
 ],
 [
  17,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  18,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  20,
  12,
  12,
  "type",
  "declaration"
 ],
 [
  20,
  27,
  6,
  "type",
  "defaultLibrary"
 ],
 [
  20,
  42,
  11,
  "interface",
  ""
 ],
 [
  22,
  10,
  8,
  "interface",
  "declaration"
 ],
 [
  23,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  24,
  2,
  4,
  "property",
  "declaration"
 ],
 [
  25,
  2,
  5,
  "property",
  "declaration"
 ],
 [
  26,
  2,
  6,
  "property",
  "declaration"
 ],
 [
  29,
  5,
  13,
  "type",
  "declaration"
 ],
 [
  30,
  2,
  5,
  "parameter",
  "declaration"
 ],
 [
  30,
  9,
  12,
  "type",
  ""
 ],
 [
  31,
  2,
  10,
  "parameter",
  "declaration"
 ],
 [
  32,
  2,
  16,
  "function",
  "declaration"
 ],
 [
  32,
  21,
  13,
  "type",
  ""
 ],
 [
  33,
  5,
  12,
  "type",
  ""
 ],
 [
  35,
  17,
  27,
  "interface",
  "declaration"
 ],
 [
  36,
  2,
  16,
  "property",
  "declaration"
 ],
 [
  36,
  20,
  16,
  "interface",
  ""
 ],
 [
  37,
  2,
  23,
  "member",
  "declaration"
 ],
 [
  37,
  28,
  13,
  "type",
  ""
 ],
 [
  38,
  2,
  13,
  "member",
  "declaration"
 ],
 [
  38,
  18,
  13,
  "type",
  ""
 ],
 [
  39,
  2,
  24,
  "member",
  "declaration"
 ],
 [
  39,
  36,
  31,
  "function",
  ""
 ],
 [
  40,
  2,
  14,
  "property",
  "declaration"
 ],
 [
  43,
  6,
  9,
  "variable",
  "declaration,readonly"
 ],
 [
  43,
  22,
  7,
  "class",
  "defa
... (22101 characters)
```

Project file `website/plugins/remark-typescript-tools/transpileCodeblocks/plugin.ts`:

```
   1 | import { visit } from 'unist-util-visit';
   2 | // @ts-ignore
   3 | import flatMap from 'unist-util-flatmap';
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-semantictokens-missing-h9-d686b3/repro.json
```

## Evidence and reduction

- representative 257881247893-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 14 -> 3 (27 probes, 644.739 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, reduxjs/redux@fb3bad6804d6, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/TypeScript#44099](https://github.com/microsoft/TypeScript/issues/44099) Function identifiers no longer receive semantic highlighting tokens (open, 2021-05-14, 2 comments)
- [microsoft/TypeScript#57585](https://github.com/microsoft/TypeScript/issues/57585) TypeScript Language Server False Positive Error Reporting (closed, 2024-02-28, 25 comments)
- queries: `"semantic tokens" missing repo:typescript-language-server/typescript-language-server is:issue`; `"semantic tokens" stale repo:typescript-language-server/typescript-language-server is:issue`; `"semantic tokens" missing repo:microsoft/TypeScript is:issue`; `"semantic tokens" stale repo:microsoft/TypeScript is:issue`
