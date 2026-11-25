# [ts7 7.0.2] hover shows a different text after query order

Draft for the author (not filed). Group `ts7-r1-hover-text-h8-500422`, signature `ts7|r1_history|hover:text`, case family `H8`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `DayuanJiang/next-ai-draw-io@58b73ef761d8` (corpus, commit 58b73ef761d8a5e5b2afa2c360428d3dea996312), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open lib/types/model-config.ts (then 200 ms)`
3. request: `request lib/types/model-config.ts references at (30, 6) (then 200 ms)`
4. Timing: send the steps 200 ms apart without waiting, then wait until idle.
5. textDocument/didOpen `app/api/validate-diagram/route.ts`, `lib/server-model-config.ts` (the query step opens every target file that is not open), then wait until the server is idle.
6. Query `textDocument/hover` on `lib/server-model-config.ts` line 97, column 19 (LSP position {line: 96, character: 18}); compare with the same query in a fresh session opened on the final content (expected).

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
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r1-hover-text-h8-500422/repro.json
```

## Evidence and reduction

- representative 119ebfb649be-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 13 -> 2 (10 probes, 176.891 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects DayuanJiang/next-ai-draw-io@58b73ef761d8, timings race0, race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#3748](https://github.com/microsoft/typescript-go/issues/3748) Behavior difference: type testing, order (closed, 2026-05-07, 2 comments)
- [microsoft/typescript-go#4121](https://github.com/microsoft/typescript-go/issues/4121) Non-deterministic export specifier order for hoisted exports after a top-level `using` (closed, 2026-05-31, 0 comments)
- [microsoft/typescript-go#3795](https://github.com/microsoft/typescript-go/issues/3795) tsc & tsgo difference in project reference build order (closed, 2026-05-10, 3 comments)
- [microsoft/typescript-go#3548](https://github.com/microsoft/typescript-go/issues/3548) Baselines: Decorator metadata reflects stable union type ordering (closed, 2026-04-23, 0 comments)
- [microsoft/typescript-go#3551](https://github.com/microsoft/typescript-go/issues/3551) Baselines: Output file ordering changed + declaration types resolve to any instead of typeof references (closed, 2026-04-23, 2 comments)
- [microsoft/typescript-go#4758](https://github.com/microsoft/typescript-go/issues/4758) disableSourceOfProjectReferenceRedirect causes lodash per-method submodule import to resolve to the wrong function (closed, 2026-07-27, 7 comments)
- [microsoft/typescript-go#3422](https://github.com/microsoft/typescript-go/issues/3422) Wrong function signature and missing invoking description in hover (closed, 2026-04-16, 0 comments)
- [microsoft/typescript-go#3455](https://github.com/microsoft/typescript-go/issues/3455) Wrong highlight in hover for generic func type with `property` and `accessor` prefix (closed, 2026-04-21, 0 comments)
- queries: `order in:title repo:microsoft/typescript-go is:issue`; `hover wrong repo:microsoft/typescript-go is:issue`; `hover order repo:microsoft/typescript-go is:issue`; `hover stale repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr500422-replay-baseline-20261118-214419-a77479] stderr: context canceled
[ts7-7.0.2-tr500422-replay-control-20261118-214419-6e5c85] stderr: context canceled
[ts7-7.0.2-tr500422-replay-history-20261118-214444-a13f83] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr500422-replay-history-20261118-214444-a13f83] stderr: context canceled
```
