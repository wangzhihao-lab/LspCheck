# [ts6 6.0.3] typeDefinition loses its answer after file rename round trip

Draft for the author (not filed). Group `ts6-r1-typedefinition-lost-h5-712a35`, signature `ts6|r1_history|typeDefinition:lost`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `pmndrs/zustand@b57db4f86ef1` (corpus, commit b57db4f86ef179285da216eeb291266da82c361c), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/react.ts (then 200 ms)`
3. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/react.ts -> src/react_rt.ts (then 200 ms)`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/react_rt.ts -> src/react.ts (then 200 ms)`
5. Timing: send the steps 200 ms apart without waiting, then wait until idle.
6. textDocument/didOpen `src/vanilla/shallow.ts`, `tests/persistSync.test.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/typeDefinition` on `tests/persistSync.test.tsx` line 566, column 65 (LSP position {line: 565, character: 64}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/middleware/persist.ts",
  141,
  27,
  141,
  65
 ]
]
```

Actual:

```json
[]
```

Project file `tests/persistSync.test.tsx`:

```
 563 |     const hydrateUnsub1 = useBoundStore.persist.onHydrate(onHydrateSpy1)
 564 |     useBoundStore.persist.onHydrate(onHydrateSpy2)
     ...
 566 |     const finishHydrationUnsub1 = useBoundStore.persist.onFinishHydration(
 567 |       onFinishHydrationSpy1,
 568 |     )
 569 |     useBoundStore.persist.onFinishHydration(onFinishHydrationSpy2)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-typedefinition-lost-h5-712a35/repro.json
```

## Evidence and reduction

- representative 9defd9c201d7-v08: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 3 (11 probes, 170.623 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects pmndrs/zustand@b57db4f86ef1, timings race200, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#277](https://github.com/typescript-language-server/typescript-language-server/issues/277) Using typescript plugins through neovim-lsp (closed, 2021-10-31, 10 comments)
- [typescript-language-server/typescript-language-server#236](https://github.com/typescript-language-server/typescript-language-server/issues/236) JSDoc support (closed, 2021-07-13, 6 comments)
- [microsoft/TypeScript#30039](https://github.com/microsoft/TypeScript/issues/30039) Refactor rename file + rename function (open, 2019-01-23, 6 comments)
- [microsoft/TypeScript#29294](https://github.com/microsoft/TypeScript/issues/29294) Rename file when renaming default export (open, 2019-01-05, 0 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `"type definition" missing repo:typescript-language-server/typescript-language-server is:issue`; `"type definition" "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `"type definition" stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `"type definition" missing repo:microsoft/TypeScript is:issue`; `"type definition" "rename file" repo:microsoft/TypeScript is:issue`; `"type definition" stale repo:microsoft/TypeScript is:issue`
