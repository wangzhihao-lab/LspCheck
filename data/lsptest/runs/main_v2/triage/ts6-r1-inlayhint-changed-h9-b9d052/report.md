# [ts6 6.0.3] inlayHint changes its answer after edit inside a workspace window

Draft for the author (not filed). Group `ts6-r1-inlayhint-changed-h9-b9d052`, signature `ts6|r1_history|inlayHint:changed`, case family `H9`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `Gitlawb/openclaude@5cd11336caea` (corpus, commit 5cd11336caeaf2023ca1e02e5975c761cfc585fe), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/context/repoMap/repoMap.test.ts`
3. textDocument/didOpen: `open src/utils/envFile.ts`
4. textDocument/didOpen: `open src/utils/model/modelOptions.ts`
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/utils/model/modelOptions.ts -> src/utils/model/modelOptions_rt.ts`
6. textDocument/didChange: `change src/context/repoMap/repoMap.test.ts (419, 47)-(419, 55) "lastFile_x"`
7. textDocument/didChange: `change src/context/repoMap/repoMap.test.ts (419, 47)-(419, 57) "lastFile"`
8. textDocument/didChange: `change src/utils/envFile.ts (86, 9)-(86, 10) ""`
9. textDocument/didSave (the buffer is written to disk): `save src/utils/envFile.ts`
10. textDocument/didChange: `change src/utils/envFile.ts (86, 9)-(86, 9) "X"`
11. textDocument/didSave (the buffer is written to disk): `save src/utils/envFile.ts`
12. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/utils/model/modelOptions_rt.ts -> src/utils/model/modelOptions.ts`
13. Timing: wait until the server is idle after every step.
14. Query `textDocument/inlayHint` on `src/utils/model/modelOptions.ts` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  92,
  53,
  "searchString:"
 ],
 [
  95,
  12,
  ": string"
 ],
 [
  95,
  27,
  "start:"
 ],
 [
  96,
  11,
  ": number"
 ],
 [
  96,
  27,
  "searchString:"
 ],
 [
  101,
  26,
  "start:"
 ],
 [
  101,
  29,
  "end:"
 ],
 [
  102,
  22,
  "start:"
 ],
 [
  123,
  15,
  ": Pick<ModelOption, 'value' | 'switchToProfileId'>[]"
 ],
 [
  123,
  33,
  "predicate:"
 ],
 [
  123,
  39,
  ": Pick<ModelOption, 'value' | 'switchToProfileId'>"
 ],
 [
  128,
  14,
  ": GlobalConfig"
 ],
 [
  129,
  19,
  ": string | null"
 ],
 [
  147,
  12,
  ": boolean"
 ],
 [
  148,
  27,
  ": string"
 ],
 [
  154,
  22,
  ": string"
 ],
 [
  154,
  51,
  "setting:"
 ],
 [
  167,
  81,
  "setting:"
 ],
 [
  176,
  58,
  "fastMode:"
 ],
 [
  184,
  79,
  "setting:"
 ],
 [
  184,
  120,
  "model:"
 ],
 [
  190,
  15,
  ": string | undefined"
 ],
 [
  190,
  40,
  "model:"
 ],
 [
  195,
  12,
  ": boolean"
 ],
 [
  196,
  25,
  ": string | undefined"
 ],
 [
  199,
  14,
  ": boolean"
 ],
 [
  199,
  30,
  "model:"
 ],
 [
  215,
  12,
  ": boolean"
 ],
 [
  219,
  73,
  "model:"
 ],
 [
  226,
  12,
  ": boolean"
 ],
 [
  227,
  23,
  ": string | undefined"
 ],
 [
  230,
  14,
  ": boolean"
 ],
 [
  230,
  30,
  "model:"
 ],
 [
  252,
  12,
  ": boolean"
 ],
 [
  256,
  83,
  "fastMode:"
 ],
 [
  256,
  93,
  "model:"
 ],
 [
  262,
  12,
  ": boolean"
 ],
 [
  266,
  83,
  "fastMode:"
 ],
 [
  266,
  93,
  "model:"
 ],
 [
  272,
  12,
  ": boolean"
 ],
 [
  276,
  83,
  "fastMode:"
 ],
 [
  276,
  9
... (11770 characters)
```

Actual:

```json
[
 [
  92,
  53,
  "searchString:"
 ],
 [
  95,
  12,
  ": string"
 ],
 [
  95,
  27,
  "start:"
 ],
 [
  96,
  11,
  ": number"
 ],
 [
  96,
  27,
  "searchString:"
 ],
 [
  101,
  26,
  "start:"
 ],
 [
  101,
  29,
  "end:"
 ],
 [
  102,
  22,
  "start:"
 ],
 [
  123,
  15,
  ": Pick<ModelOption, 'value' | 'switchToProfileId'>[]"
 ],
 [
  123,
  33,
  "predicate:"
 ],
 [
  123,
  39,
  ": Pick<ModelOption, 'value' | 'switchToProfileId'>"
 ],
 [
  128,
  14,
  ": GlobalConfig"
 ],
 [
  129,
  19,
  ": string | null"
 ],
 [
  147,
  12,
  ": boolean"
 ],
 [
  148,
  27,
  ": string"
 ],
 [
  154,
  22,
  ": string"
 ],
 [
  154,
  51,
  "setting:"
 ],
 [
  167,
  81,
  "setting:"
 ],
 [
  176,
  58,
  "fastMode:"
 ],
 [
  184,
  79,
  "setting:"
 ],
 [
  184,
  120,
  "model:"
 ],
 [
  190,
  15,
  ": string | undefined"
 ],
 [
  190,
  40,
  "model:"
 ],
 [
  195,
  12,
  ": boolean"
 ],
 [
  196,
  25,
  ": string | undefined"
 ],
 [
  199,
  14,
  ": boolean"
 ],
 [
  199,
  30,
  "model:"
 ],
 [
  215,
  12,
  ": boolean"
 ],
 [
  219,
  73,
  "model:"
 ],
 [
  226,
  12,
  ": boolean"
 ],
 [
  227,
  23,
  ": string | undefined"
 ],
 [
  230,
  14,
  ": boolean"
 ],
 [
  230,
  30,
  "model:"
 ],
 [
  252,
  12,
  ": boolean"
 ],
 [
  256,
  83,
  "fastMode:"
 ],
 [
  256,
  93,
  "model:"
 ],
 [
  262,
  12,
  ": boolean"
 ],
 [
  266,
  83,
  "fastMode:"
 ],
 [
  266,
  93,
  "model:"
 ],
 [
  272,
  12,
  ": boolean"
 ],
 [
  276,
  83,
  "fastMode:"
 ],
 [
  276,
  9
... (11767 characters)
```

Project file `src/utils/model/modelOptions.ts`:

```
   1 | // biome-ignore-all assist/source/organizeImports: internal-only import markers must not be reordered
   2 | import { getInitialMainLoopModel } from '../../bootstrap/state.js'
   3 | import { getCatalogEntriesForRoute } from '../../integrations/index.js'
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-inlayhint-changed-h9-b9d052/repro.json
```

## Evidence and reduction

- representative e760eab91233-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 11 -> 11 (21 probes, 1818.261 s, reduced ops confirmed 2/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Gitlawb/openclaude@5cd11336caea, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#738](https://github.com/typescript-language-server/typescript-language-server/issues/738) Do not send paddingLeft = true for type parameters' hints (closed, 2023-07-07, 7 comments)
- [typescript-language-server/typescript-language-server#258](https://github.com/typescript-language-server/typescript-language-server/issues/258) Support inlay hints (closed, 2021-09-16, 0 comments)
- [typescript-language-server/typescript-language-server#264](https://github.com/typescript-language-server/typescript-language-server/issues/264) Inlay Hints return empty result (closed, 2021-10-06, 4 comments)
- [microsoft/TypeScript#45928](https://github.com/microsoft/TypeScript/issues/45928) Show function return type inlay hints even for JS functions that have explicit type annotations (open, 2021-09-17, 3 comments)
- [microsoft/TypeScript#55486](https://github.com/microsoft/TypeScript/issues/55486) TypeScript 5.3 Iteration Plan (closed, 2023-08-23, 41 comments)
- [microsoft/TypeScript#63800](https://github.com/microsoft/TypeScript/issues/63800) API usage patterns for complex editor extensions (open, 2026-02-18, 56 comments)
- [microsoft/TypeScript#44960](https://github.com/microsoft/TypeScript/issues/44960) Crash in inlay hints (closed, 2021-07-09, 2 comments)
- [microsoft/TypeScript#56078](https://github.com/microsoft/TypeScript/issues/56078) Parameter inlay hints show the wrong parameter names (closed, 2023-10-12, 2 comments)
- queries: `"inlay hint" wrong repo:typescript-language-server/typescript-language-server is:issue`; `"inlay hint" stale repo:typescript-language-server/typescript-language-server is:issue`; `"inlay hint" wrong repo:microsoft/TypeScript is:issue`; `"inlay hint" stale repo:microsoft/TypeScript is:issue`
