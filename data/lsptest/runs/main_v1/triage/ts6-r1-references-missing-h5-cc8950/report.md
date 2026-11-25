# [ts6 6.0.3] references misses entries after file rename round trip

Draft for the author (not filed). Group `ts6-r1-references-missing-h5-cc8950`, signature `ts6|r1_history|references:missing`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/core/shared/skill-generation.ts (then 200 ms)`
3. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/core/shared/skill-generation.ts -> src/core/shared/skill-generation_rt.ts (then 200 ms)`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/core/shared/skill-generation_rt.ts -> src/core/shared/skill-generation.ts (then 200 ms)`
5. Timing: send the steps 200 ms apart without waiting, then wait until idle.
6. textDocument/didOpen `src/telemetry/index.ts`, `test/commands/store-git.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/references` on `src/core/shared/skill-generation.ts` line 65, column 6 (LSP position {line: 64, character: 5}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/core/init.ts",
  966,
  33,
  966,
  40
 ],
 [
  "src/core/shared/skill-generation.ts",
  64,
  2,
  64,
  9
 ],
 [
  "src/core/shared/skill-generation.ts",
  83,
  43,
  83,
  50
 ],
 [
  "src/core/shared/skill-generation.ts",
  84,
  45,
  84,
  52
 ],
 [
  "src/core/shared/skill-generation.ts",
  85,
  50,
  85,
  57
 ],
 [
  "src/core/shared/skill-generation.ts",
  86,
  47,
  86,
  54
 ],
 [
  "src/core/shared/skill-generation.ts",
  87,
  48,
  87,
  55
 ],
 [
  "src/core/shared/skill-generation.ts",
  88,
  44,
  88,
  51
 ],
 [
  "src/core/shared/skill-generation.ts",
  89,
  45,
  89,
  52
 ],
 [
  "src/core/shared/skill-generation.ts",
  90,
  49,
  90,
  56
 ],
 [
  "src/core/shared/skill-generation.ts",
  91,
  53,
  91,
  60
 ],
 [
  "src/core/shared/skill-generation.ts",
  92,
  48,
  92,
  55
 ],
 [
  "src/core/shared/skill-generation.ts",
  93,
  43,
  93,
  50
 ],
 [
  "src/core/shared/skill-generation.ts",
  94,
  47,
  94,
  54
 ],
 [
  "src/core/update.ts",
  339,
  33,
  339,
  40
 ],
 [
  "src/core/update.ts",
  629,
  75,
  629,
  82
 ],
 [
  "src/core/update.ts",
  1343,
  33,
  1343,
  40
 ]
]
```

Actual:

```json
[
 [
  "src/core/shared/skill-generation.ts",
  64,
  2,
  64,
  9
 ],
 [
  "src/core/shared/skill-generation.ts",
  83,
  43,
  83,
  50
 ],
 [
  "src/core/shared/skill-generation.ts",
  84,
  45,
  84,
  52
 ],
 [
  "src/core/shared/skill-generation.ts",
  85,
  50,
  85,
  57
 ],
 [
  "src/core/shared/skill-generation.ts",
  86,
  47,
  86,
  54
 ],
 [
  "src/core/shared/skill-generation.ts",
  87,
  48,
  87,
  55
 ],
 [
  "src/core/shared/skill-generation.ts",
  88,
  44,
  88,
  51
 ],
 [
  "src/core/shared/skill-generation.ts",
  89,
  45,
  89,
  52
 ],
 [
  "src/core/shared/skill-generation.ts",
  90,
  49,
  90,
  56
 ],
 [
  "src/core/shared/skill-generation.ts",
  91,
  53,
  91,
  60
 ],
 [
  "src/core/shared/skill-generation.ts",
  92,
  48,
  92,
  55
 ],
 [
  "src/core/shared/skill-generation.ts",
  93,
  43,
  93,
  50
 ],
 [
  "src/core/shared/skill-generation.ts",
  94,
  47,
  94,
  54
 ]
]
```

Project file `src/core/shared/skill-generation.ts`:

```
  62 |  */
  63 | export interface SkillTemplateEntry {
  64 |   template: SkillTemplate;
  65 |   dirName: string;
  66 |   workflowId: string;
  67 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-references-missing-h5-cc8950/repro.json
```

## Evidence and reduction

- representative 9fc84ad1ca04-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 3 (11 probes, 112.099 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, vercel/hyper@30ec0a2a91de, timings race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#945](https://github.com/typescript-language-server/typescript-language-server/issues/945) Cross-file referencing not working when using multilspy client (closed, 2025-03-06, 2 comments)
- [typescript-language-server/typescript-language-server#948](https://github.com/typescript-language-server/typescript-language-server/issues/948) workspace/symbol Fails to Recognize rootPath and Inconsistent Responses Without Debugging (closed, 2025-03-14, 3 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#277](https://github.com/typescript-language-server/typescript-language-server/issues/277) Using typescript plugins through neovim-lsp (closed, 2021-10-31, 10 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `references missing repo:typescript-language-server/typescript-language-server is:issue`; `references "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `references stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `references missing repo:microsoft/TypeScript is:issue`; `references "rename file" repo:microsoft/TypeScript is:issue`; `references stale repo:microsoft/TypeScript is:issue`
