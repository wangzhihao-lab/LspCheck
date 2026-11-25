# [ts6 6.0.3] signatureHelp changes its answer after file rename round trip

Draft for the author (not filed). Group `ts6-r1-signaturehelp-changed-h5-db5a5e`, signature `ts6|r1_history|signatureHelp:changed`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `pmndrs/zustand@b57db4f86ef1` (corpus, commit b57db4f86ef179285da216eeb291266da82c361c), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/react.ts`
3. textDocument/didOpen: `open src/vanilla/shallow.ts`
4. textDocument/didOpen: `open tests/persistSync.test.tsx`
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/react.ts -> src/react_rt.ts`
6. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/react_rt.ts -> src/react.ts`
7. Timing: send the steps 0 ms apart without waiting, then wait until idle.
8. Query `textDocument/signatureHelp` on `tests/persistSync.test.tsx` line 468, column 21 (LSP position {line: 467, character: 20}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"fromEntries(entries: Iterable<readonly [PropertyKey, number]>): { [k: string]: number; }"
```

Actual:

```json
"fromEntries(entries: Iterable<readonly [PropertyKey, unknown]>): { [k: string]: unknown; }"
```

Project file `tests/persistSync.test.tsx`:

```
 465 |       name: 'test-storage-2',
 466 |       partialize: (state) =>
 467 |         Object.fromEntries(
 468 |           Object.entries(state).filter(([key]) => key !== 'count'),
 469 |         ),
 470 |     })
 471 |     useBoundStore.setState({})
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-signaturehelp-changed-h5-db5a5e/repro.json
```

## Evidence and reduction

- representative 3ed0e189007e-v08: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 5 (11 probes, 121.476 s, reduced ops confirmed 2/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects pmndrs/zustand@b57db4f86ef1, timings race0, race200, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [microsoft/TypeScript#30039](https://github.com/microsoft/TypeScript/issues/30039) Refactor rename file + rename function (open, 2019-01-23, 6 comments)
- [microsoft/TypeScript#29294](https://github.com/microsoft/TypeScript/issues/29294) Rename file when renaming default export (open, 2019-01-05, 0 comments)
- [microsoft/TypeScript#29375](https://github.com/microsoft/TypeScript/issues/29375) Suggest renaming file from .ts to .tsx if needed? (open, 2019-01-11, 0 comments)
- [microsoft/TypeScript#44411](https://github.com/microsoft/TypeScript/issues/44411) Renaming file doesn't update imports in other projects which reference this project (open, 2021-06-03, 1 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" wrong repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `"signature help" wrong repo:microsoft/TypeScript is:issue`; `"signature help" "rename file" repo:microsoft/TypeScript is:issue`; `"signature help" stale repo:microsoft/TypeScript is:issue`
