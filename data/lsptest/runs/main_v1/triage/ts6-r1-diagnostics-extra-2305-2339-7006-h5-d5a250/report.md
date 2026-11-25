# [ts6 6.0.3] diagnostics adds 2305,2339,7006 after file rename round trip

Draft for the author (not filed). Group `ts6-r1-diagnostics-extra-2305-2339-7006-h5-d5a250`, signature `ts6|r1_history|diagnostics:extra:2305,2339,7006`, case family `H5`.

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
8. Query `textDocument/diagnostic` on `tests/persistSync.test.tsx` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  70,
  34,
  70,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  94,
  16,
  94,
  30,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  115,
  34,
  115,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  120,
  23,
  120,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  132,
  35,
  132,
  49,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  161,
  23,
  161,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  162,
  23,
  162,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  169,
  34,
  169,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  196,
  34,
  196,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  225,
  34,
  225,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  261,
  34,
  261,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  291,
  34,
  291,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  402,
  23,
  402,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  458,
  23,
  458,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  471,
  23,
  471,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
... (2901 characters)
```

Actual:

```json
[
 [
  3,
  9,
  3,
  15,
  1,
  "2305",
  "typescript",
  "Module '\"zustand\"' has no exported member 'create'."
 ],
 [
  70,
  34,
  70,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  94,
  16,
  94,
  30,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  115,
  34,
  115,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  120,
  23,
  120,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  132,
  35,
  132,
  49,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  161,
  23,
  161,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  162,
  23,
  162,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  169,
  34,
  169,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  196,
  34,
  196,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  225,
  34,
  225,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  261,
  34,
  261,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  291,
  34,
  291,
  48,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  402,
  23,
  402,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is deprecated."
 ],
 [
  458,
  23,
  458,
  37,
  4,
  "6385",
  "typescript",
  "'toBeCalledWith' is de
... (3358 characters)
```

Project file `tests/persistSync.test.tsx`:

```
   1 | /// <reference types="node" />
     ...
   3 | import { afterEach, describe, expect, it, vi } from 'vitest'
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-diagnostics-extra-2305-2339-7006-h5-d5a250/repro.json
```

## Evidence and reduction

- representative 3ed0e189007e-v03: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 5 (11 probes, 274.132 s, reduced ops confirmed 2/3)
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects pmndrs/zustand@b57db4f86ef1, timings race0, race200, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#815](https://github.com/typescript-language-server/typescript-language-server/issues/815) TSServer >=4.1.0 never publishes textDocument/publishDiagnostics event (NeoVim) (closed, 2023-11-16, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics extra repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `diagnostics extra repo:microsoft/TypeScript is:issue`; `diagnostics "rename file" repo:microsoft/TypeScript is:issue`; `diagnostics stale repo:microsoft/TypeScript is:issue`
