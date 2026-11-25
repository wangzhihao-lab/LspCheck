# [ts6 6.0.3] semanticTokens changes its answer after file rename round trip

Draft for the author (not filed). Group `ts6-r1-semantictokens-changed-h5-591c42`, signature `ts6|r1_history|semanticTokens:changed`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `pmndrs/zustand@b57db4f86ef1` (corpus, commit b57db4f86ef179285da216eeb291266da82c361c), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/react.ts`
3. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/react.ts -> src/react_rt.ts`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/react_rt.ts -> src/react.ts`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/vanilla/shallow.ts`, `tests/persistSync.test.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/semanticTokens/full` on `tests/persistSync.test.tsx` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  7,
  6,
  21,
  "function",
  "declaration,readonly"
 ],
 [
  7,
  31,
  12,
  "parameter",
  "declaration"
 ],
 [
  8,
  6,
  5,
  "variable",
  "declaration,local"
 ],
 [
  8,
  14,
  12,
  "parameter",
  ""
 ],
 [
  10,
  8,
  7,
  "function",
  "declaration,local,readonly"
 ],
 [
  11,
  4,
  10,
  "class",
  ""
 ],
 [
  12,
  11,
  5,
  "variable",
  "local"
 ],
 [
  14,
  8,
  7,
  "function",
  "declaration,local,readonly"
 ],
 [
  14,
  19,
  4,
  "parameter",
  "declaration"
 ],
 [
  14,
  33,
  8,
  "parameter",
  "declaration"
 ],
 [
  15,
  4,
  10,
  "class",
  ""
 ],
 [
  15,
  15,
  4,
  "parameter",
  ""
 ],
 [
  15,
  21,
  8,
  "parameter",
  ""
 ],
 [
  16,
  4,
  5,
  "variable",
  "local"
 ],
 [
  16,
  12,
  8,
  "parameter",
  ""
 ],
 [
  18,
  8,
  10,
  "function",
  "declaration,local,readonly"
 ],
 [
  18,
  22,
  4,
  "parameter",
  "declaration"
 ],
 [
  19,
  4,
  13,
  "class",
  ""
 ],
 [
  19,
  18,
  4,
  "parameter",
  ""
 ],
 [
  20,
  4,
  5,
  "variable",
  "local"
 ],
 [
  23,
  8,
  10,
  "class",
  "declaration"
 ],
 [
  23,
  21,
  2,
  "variable",
  "readonly"
 ],
 [
  23,
  24,
  2,
  "member",
  ""
 ],
 [
  24,
  8,
  10,
  "class",
  "declaration"
 ],
 [
  24,
  21,
  2,
  "variable",
  "readonly"
 ],
 [
  24,
  24,
  2,
  "member",
  ""
 ],
 [
  25,
  8,
  13,
  "class",
  "declaration"
 ],
 [
  25,
  24,
  2,
  "variable",
  "readonly"
 ],
 [
  25,
  27,
  2,
  "member",
  ""
 ],
 [
  28,
  4,
  7,
  "property",
  "declar
... (48909 characters)
```

Actual:

```json
[
 [
  7,
  6,
  21,
  "function",
  "declaration,readonly"
 ],
 [
  7,
  31,
  12,
  "parameter",
  "declaration"
 ],
 [
  8,
  6,
  5,
  "variable",
  "declaration,local"
 ],
 [
  8,
  14,
  12,
  "parameter",
  ""
 ],
 [
  10,
  8,
  7,
  "function",
  "declaration,local,readonly"
 ],
 [
  11,
  4,
  10,
  "class",
  ""
 ],
 [
  12,
  11,
  5,
  "variable",
  "local"
 ],
 [
  14,
  8,
  7,
  "function",
  "declaration,local,readonly"
 ],
 [
  14,
  19,
  4,
  "parameter",
  "declaration"
 ],
 [
  14,
  33,
  8,
  "parameter",
  "declaration"
 ],
 [
  15,
  4,
  10,
  "class",
  ""
 ],
 [
  15,
  15,
  4,
  "parameter",
  ""
 ],
 [
  15,
  21,
  8,
  "parameter",
  ""
 ],
 [
  16,
  4,
  5,
  "variable",
  "local"
 ],
 [
  16,
  12,
  8,
  "parameter",
  ""
 ],
 [
  18,
  8,
  10,
  "function",
  "declaration,local,readonly"
 ],
 [
  18,
  22,
  4,
  "parameter",
  "declaration"
 ],
 [
  19,
  4,
  13,
  "class",
  ""
 ],
 [
  19,
  18,
  4,
  "parameter",
  ""
 ],
 [
  20,
  4,
  5,
  "variable",
  "local"
 ],
 [
  23,
  8,
  10,
  "class",
  "declaration"
 ],
 [
  23,
  21,
  2,
  "variable",
  "readonly"
 ],
 [
  23,
  24,
  2,
  "member",
  ""
 ],
 [
  24,
  8,
  10,
  "class",
  "declaration"
 ],
 [
  24,
  21,
  2,
  "variable",
  "readonly"
 ],
 [
  24,
  24,
  2,
  "member",
  ""
 ],
 [
  25,
  8,
  13,
  "class",
  "declaration"
 ],
 [
  25,
  24,
  2,
  "variable",
  "readonly"
 ],
 [
  25,
  27,
  2,
  "member",
  ""
 ],
 [
  28,
  4,
  7,
  "property",
  "declar
... (45071 characters)
```

Project file `tests/persistSync.test.tsx`:

```
   1 | /// <reference types="node" />
     ...
   3 | import { afterEach, describe, expect, it, vi } from 'vitest'
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-semantictokens-changed-h5-591c42/repro.json
```

## Evidence and reduction

- representative 210902bea61f-v08: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 3 (11 probes, 219.59 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects pmndrs/zustand@b57db4f86ef1, timings race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#753](https://github.com/typescript-language-server/typescript-language-server/issues/753) angle brackets are not being matched properly, causing keywords to be highlighted as a type (closed, 2023-09-05, 1 comments)
- [typescript-language-server/typescript-language-server#632](https://github.com/typescript-language-server/typescript-language-server/issues/632) Wrong or confusing Semantic Token Types reported (closed, 2022-11-23, 1 comments)
- [microsoft/TypeScript#30039](https://github.com/microsoft/TypeScript/issues/30039) Refactor rename file + rename function (open, 2019-01-23, 6 comments)
- [microsoft/TypeScript#29294](https://github.com/microsoft/TypeScript/issues/29294) Rename file when renaming default export (open, 2019-01-05, 0 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `"semantic tokens" wrong repo:typescript-language-server/typescript-language-server is:issue`; `"semantic tokens" "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `"semantic tokens" stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `"semantic tokens" wrong repo:microsoft/TypeScript is:issue`; `"semantic tokens" "rename file" repo:microsoft/TypeScript is:issue`; `"semantic tokens" stale repo:microsoft/TypeScript is:issue`
