# [ts6 6.0.3] hover shows a different text after file rename round trip

Draft for the author (not filed). Group `ts6-r1-hover-text-h5-b3855d`, signature `ts6|r1_history|hover:text`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `DayuanJiang/next-ai-draw-io@58b73ef761d8` (corpus, commit 58b73ef761d8a5e5b2afa2c360428d3dea996312), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open lib/server-model-config.ts`
3. Timing: send the steps 0 ms apart without waiting, then wait until idle.
4. textDocument/didOpen `app/api/validate-diagram/route.ts`, `lib/types/model-config.ts` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/hover` on `lib/server-model-config.ts` line 97, column 19 (LSP position {line: 96, character: 18}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "(property) Array<T>.length: number Gets or sets the length of the array. This is a number one higher than the highest index in the array.",
 [
  96,
  15,
  96,
  21
 ]
]
```

Actual:

```json
[
 "(property) Array<string>.length: number Gets or sets the length of the array. This is a number one higher than the highest index in the array.",
 [
  96,
  15,
  96,
  21
 ]
]
```

Project file `lib/server-model-config.ts`:

```
  94 |                 .filter((s) => s.length > 0),
  95 |         ),
  96 |     )
  97 |     if (models.length === 0) return null
     ...
  99 |     const providerName = aiProvider as ProviderName
 100 |     return {
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-hover-text-h5-b3855d/repro.json
```

## Evidence and reduction

- representative b5ca03424592-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 1 (6 probes, 281.489 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects DayuanJiang/next-ai-draw-io@58b73ef761d8, timings race0, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#865](https://github.com/typescript-language-server/typescript-language-server/issues/865) Fully resolve type aliases  (closed, 2024-02-02, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `hover wrong repo:typescript-language-server/typescript-language-server is:issue`; `hover "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `hover stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `hover wrong repo:microsoft/TypeScript is:issue`; `hover "rename file" repo:microsoft/TypeScript is:issue`; `hover stale repo:microsoft/TypeScript is:issue`
