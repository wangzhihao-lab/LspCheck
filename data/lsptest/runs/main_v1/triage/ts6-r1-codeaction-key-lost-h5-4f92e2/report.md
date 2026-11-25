# [ts6 6.0.3] codeAction is not answered after file rename round trip

Draft for the author (not filed). Group `ts6-r1-codeaction-key-lost-h5-4f92e2`, signature `ts6|r1_history|codeAction:key-lost`, case family `H5`.

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
7. Query `textDocument/codeAction` on `tests/persistSync.test.tsx` line 226, column 35 (LSP position {line: 225, character: 34}) (diag:225:48); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Move to a new file",
  "refactor.move.newFile"
 ]
]
```

Actual:

```json
[
 "missing-key"
]
```

Project file `tests/persistSync.test.tsx`:

```
 223 |     )
     ...
 225 |     expect(useBoundStore.getState()).toEqual({ count: 0 })
 226 |     expect(onRehydrateStorageSpy).toBeCalledWith(
 227 |       undefined,
 228 |       new Error('migrate error'),
 229 |     )
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-codeaction-key-lost-h5-4f92e2/repro.json
```

## Evidence and reduction

- representative 210902bea61f-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 3 (11 probes, 228.476 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects pmndrs/zustand@b57db4f86ef1, timings race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#1052](https://github.com/typescript-language-server/typescript-language-server/issues/1052) Question: Where are specific import code actions? (closed, 2025-11-19, 9 comments)
- [typescript-language-server/typescript-language-server#844](https://github.com/typescript-language-server/typescript-language-server/issues/844) Server crashed when asking for textDocument/codeAction (closed, 2024-01-06, 11 comments)
- [typescript-language-server/typescript-language-server#655](https://github.com/typescript-language-server/typescript-language-server/issues/655) Code actions not working (closed, 2023-01-05, 7 comments)
- [typescript-language-server/typescript-language-server#623](https://github.com/typescript-language-server/typescript-language-server/issues/623) missing import code action tries to import React unnecessarily (closed, 2022-11-14, 4 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `"code action" missing repo:typescript-language-server/typescript-language-server is:issue`; `"code action" "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `"code action" stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `"code action" missing repo:microsoft/TypeScript is:issue`; `"code action" "rename file" repo:microsoft/TypeScript is:issue`; `"code action" stale repo:microsoft/TypeScript is:issue`
