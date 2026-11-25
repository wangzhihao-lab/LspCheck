# [ts6 6.0.3] documentHighlight misses entries after edit inside a workspace window

Draft for the author (not filed). Group `ts6-r1-documenthighlight-missing-h9-2e657a`, signature `ts6|r1_history|documentHighlight:missing`, case family `H9`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `Gitlawb/openclaude@5cd11336caea` (corpus, commit 5cd11336caeaf2023ca1e02e5975c761cfc585fe), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/utils/model/modelOptions.ts`
3. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/utils/model/modelOptions.ts -> src/utils/model/modelOptions_rt.ts`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/utils/model/modelOptions_rt.ts -> src/utils/model/modelOptions.ts`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `src/context/repoMap/repoMap.test.ts`, `src/utils/envFile.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/documentHighlight` on `src/utils/model/modelOptions.ts` line 370, column 7 (LSP position {line: 369, character: 6}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  59,
  2,
  59,
  7,
  2
 ],
 [
  123,
  50,
  123,
  55,
  2
 ],
 [
  156,
  6,
  156,
  11,
  2
 ],
 [
  165,
  6,
  165,
  11,
  2
 ],
 [
  174,
  6,
  174,
  11,
  2
 ],
 [
  182,
  4,
  182,
  9,
  2
 ],
 [
  201,
  6,
  201,
  11,
  2
 ],
 [
  217,
  4,
  217,
  9,
  2
 ],
 [
  232,
  6,
  232,
  11,
  2
 ],
 [
  244,
  4,
  244,
  9,
  2
 ],
 [
  254,
  4,
  254,
  9,
  2
 ],
 [
  264,
  4,
  264,
  9,
  2
 ],
 [
  274,
  4,
  274,
  9,
  2
 ],
 [
  284,
  4,
  284,
  9,
  2
 ],
 [
  298,
  4,
  298,
  9,
  2
 ],
 [
  311,
  6,
  311,
  11,
  2
 ],
 [
  323,
  4,
  323,
  9,
  2
 ],
 [
  333,
  4,
  333,
  9,
  2
 ],
 [
  351,
  4,
  351,
  9,
  2
 ],
 [
  360,
  4,
  360,
  9,
  2
 ],
 [
  369,
  4,
  369,
  9,
  2
 ],
 [
  378,
  4,
  378,
  9,
  2
 ],
 [
  387,
  2,
  387,
  7,
  2
 ],
 [
  393,
  2,
  393,
  7,
  2
 ],
 [
  400,
  4,
  400,
  9,
  2
 ],
 [
  408,
  4,
  408,
  9,
  2
 ],
 [
  416,
  4,
  416,
  9,
  2
 ],
 [
  425,
  6,
  425,
  11,
  2
 ],
 [
  430,
  6,
  430,
  11,
  2
 ],
 [
  435,
  6,
  435,
  11,
  2
 ],
 [
  440,
  6,
  440,
  11,
  2
 ],
 [
  445,
  6,
  445,
  11,
  2
 ],
 [
  450,
  6,
  450,
  11,
  2
 ],
 [
  455,
  6,
  455,
  11,
  2
 ],
 [
  460,
  6,
  460,
  11,
  2
 ],
 [
  465,
  6,
  465,
  11,
  2
 ],
 [
  470,
  6,
  470,
  11,
  2
 ],
 [
  475,
  6,
  475,
  11,
  2
 ],
 [
  480,
  6,
  480,
  11,
  2
 ],
 [
  485,
  6,
  485,
  11,
  2
 ],
 [
  558,
  10,
  558,
  15,
  2
 ],
 [
  790,
  26,
  790,
  31,
  2
 ],
 [
  
... (2366 characters)
```

Actual:

```json
[
 [
  59,
  2,
  59,
  7,
  2
 ],
 [
  123,
  50,
  123,
  55,
  2
 ],
 [
  156,
  6,
  156,
  11,
  2
 ],
 [
  165,
  6,
  165,
  11,
  2
 ],
 [
  174,
  6,
  174,
  11,
  2
 ],
 [
  182,
  4,
  182,
  9,
  2
 ],
 [
  201,
  6,
  201,
  11,
  2
 ],
 [
  217,
  4,
  217,
  9,
  2
 ],
 [
  232,
  6,
  232,
  11,
  2
 ],
 [
  244,
  4,
  244,
  9,
  2
 ],
 [
  254,
  4,
  254,
  9,
  2
 ],
 [
  264,
  4,
  264,
  9,
  2
 ],
 [
  274,
  4,
  274,
  9,
  2
 ],
 [
  284,
  4,
  284,
  9,
  2
 ],
 [
  298,
  4,
  298,
  9,
  2
 ],
 [
  311,
  6,
  311,
  11,
  2
 ],
 [
  323,
  4,
  323,
  9,
  2
 ],
 [
  333,
  4,
  333,
  9,
  2
 ],
 [
  351,
  4,
  351,
  9,
  2
 ],
 [
  360,
  4,
  360,
  9,
  2
 ],
 [
  369,
  4,
  369,
  9,
  2
 ],
 [
  378,
  4,
  378,
  9,
  2
 ],
 [
  387,
  2,
  387,
  7,
  2
 ],
 [
  393,
  2,
  393,
  7,
  2
 ],
 [
  400,
  4,
  400,
  9,
  2
 ],
 [
  408,
  4,
  408,
  9,
  2
 ],
 [
  416,
  4,
  416,
  9,
  2
 ],
 [
  425,
  6,
  425,
  11,
  2
 ],
 [
  430,
  6,
  430,
  11,
  2
 ],
 [
  435,
  6,
  435,
  11,
  2
 ],
 [
  440,
  6,
  440,
  11,
  2
 ],
 [
  445,
  6,
  445,
  11,
  2
 ],
 [
  450,
  6,
  450,
  11,
  2
 ],
 [
  455,
  6,
  455,
  11,
  2
 ],
 [
  460,
  6,
  460,
  11,
  2
 ],
 [
  465,
  6,
  465,
  11,
  2
 ],
 [
  470,
  6,
  470,
  11,
  2
 ],
 [
  475,
  6,
  475,
  11,
  2
 ],
 [
  480,
  6,
  480,
  11,
  2
 ],
 [
  485,
  6,
  485,
  11,
  2
 ],
 [
  558,
  10,
  558,
  15,
  2
 ],
 [
  795,
  8,
  795,
  13,
  2
 ],
 [
  8
... (2292 characters)
```

Project file `src/utils/model/modelOptions.ts`:

```
 367 | export function getMaxOpus46_1MOption(fastMode = false): ModelOption {
 368 |   const billingInfo = isClaudeAISubscriber() ? ' · Billed as extra usage' : ''
 369 |   return {
 370 |     value: 'opus[1m]',
 371 |     label: 'Opus (1M context)',
 372 |     description: `Opus 4.8 with 1M context${billingInfo}${getOpus46PricingSuffix(fastMode, getModelStrings().opus48)}`,
 373 |   }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-documenthighlight-missing-h9-2e657a/repro.json
```

## Evidence and reduction

- representative e760eab91233-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 11 -> 3 (22 probes, 1239.916 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Gitlawb/openclaude@5cd11336caea, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/TypeScript#44099](https://github.com/microsoft/TypeScript/issues/44099) Function identifiers no longer receive semantic highlighting tokens (open, 2021-05-14, 2 comments)
- [microsoft/TypeScript#58062](https://github.com/microsoft/TypeScript/issues/58062) Shorten error spans for missing key errors reported on object literals (open, 2024-04-03, 3 comments)
- [microsoft/TypeScript#63456](https://github.com/microsoft/TypeScript/issues/63456) String.split() method's separator argument should allow undefined (open, 2026-05-01, 5 comments)
- [microsoft/TypeScript#29578](https://github.com/microsoft/TypeScript/issues/29578) unclear how to make function argument check produce the same errors as variable assignment (open, 2019-01-25, 0 comments)
- [microsoft/TypeScript#50469](https://github.com/microsoft/TypeScript/issues/50469) "function" semantic token applied instead of "decorator", thus cannot configure correct syntax highlighting (open, 2022-08-15, 4 comments)
- [microsoft/TypeScript#29526](https://github.com/microsoft/TypeScript/issues/29526) Easier destructuring with type annotations on binding patterns (open, 2019-01-22, 156 comments)
- [microsoft/TypeScript#25600](https://github.com/microsoft/TypeScript/issues/25600) tsc --build / Project References Feedback & Discussion (open, 2018-07-12, 141 comments)
- [microsoft/TypeScript#62867](https://github.com/microsoft/TypeScript/issues/62867) Add basic types <Byte> and <Integer> (closed, 2025-12-09, 13 comments)
- queries: `highlight missing repo:typescript-language-server/typescript-language-server is:issue`; `highlight stale repo:typescript-language-server/typescript-language-server is:issue`; `highlight missing repo:microsoft/TypeScript is:issue`; `highlight stale repo:microsoft/TypeScript is:issue`
