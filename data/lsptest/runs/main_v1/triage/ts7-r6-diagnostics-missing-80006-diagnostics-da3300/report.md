# [ts7 7.0.2] diagnostics differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-diagnostics-missing-80006-diagnostics-da3300`, signature `ts7|r6_crossimpl|diagnostics:missing:80006`, case family `diagnostics`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `vercel/hyper@30ec0a2a91de` (corpus, commit 30ec0a2a91de17eeb32dd71998fe8a8ec59f98eb), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/diagnostic` on `cli/index.ts` for the whole file; compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  101,
  6,
  101,
  14,
  0,
  "80006",
  "",
  ""
 ],
 [
  120,
  3,
  120,
  7,
  0,
  "6133",
  "",
  ""
 ],
 [
  168,
  3,
  168,
  7,
  0,
  "6133",
  "",
  ""
 ],
 [
  57,
  3,
  57,
  7,
  0,
  "6133",
  "",
  ""
 ],
 [
  72,
  3,
  72,
  7,
  0,
  "6133",
  "",
  ""
 ]
]
```

Actual:

```json
[
 [
  120,
  3,
  120,
  7,
  0,
  "6133",
  "",
  ""
 ],
 [
  168,
  3,
  168,
  7,
  0,
  "6133",
  "",
  ""
 ],
 [
  57,
  3,
  57,
  7,
  0,
  "6133",
  "",
  ""
 ],
 [
  72,
  3,
  72,
  7,
  0,
  "6133",
  "",
  ""
 ]
]
```

Project file `cli/index.ts`:

```
   1 | // This is a CLI tool, using console is OK
   2 | /* eslint no-console: 0 */
   3 | import {spawn, exec} from 'child_process';
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-diagnostics-missing-80006-diagnostics-da3300/repro.json
```

## Evidence and reduction

- representative 8d2a914da68a-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects vercel/hyper@30ec0a2a91de, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4745](https://github.com/microsoft/typescript-go/issues/4745) Native API syntactic diagnostics omit start and length (closed, 2026-07-26, 2 comments)
- [microsoft/typescript-go#4249](https://github.com/microsoft/typescript-go/issues/4249) `.getProgramDiagnostics()` is missing in the API (closed, 2026-06-09, 0 comments)
- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4262](https://github.com/microsoft/typescript-go/issues/4262) Non-deterministic `TS2305 "has no exported member"` errors across project references with `--emitDeclarationOnly` (closed, 2026-06-10, 8 comments)
- [microsoft/typescript-go#4378](https://github.com/microsoft/typescript-go/issues/4378) `tsgo --watch` error: "error starting FSEvents stream" on large `node_modules` since the fswatch rewrite (closed, 2026-06-19, 8 comments)
- [microsoft/typescript-go#4827](https://github.com/microsoft/typescript-go/issues/4827) Generic type argument inferred from the wrong inference slot (cyclic union-of-intersections); larger programs show scheduling-dependent diagnostics (closed, 2026-08-04, 1 comments)
- [microsoft/typescript-go#4719](https://github.com/microsoft/typescript-go/issues/4719) tsgo reports type errors in external-library (node_modules) source files that tsc suppresses (closed, 2026-07-23, 2 comments)
- [microsoft/typescript-go#4129](https://github.com/microsoft/typescript-go/issues/4129) tsgo reports compiler-option diagnostics even when syntactic errors exist (closed, 2026-05-31, 0 comments)
- queries: `diagnostics missing repo:microsoft/typescript-go is:issue`; `diagnostics "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trda3300-r6-replay-test-baseline-20260925-170149-7b8058] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trda3300-r6-replay-test-baseline-20260925-170149-7b8058] stderr: context canceled
[ts7-7.0.2-trda3300-r6-replay-test-control-20260925-170242-35e835] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trda3300-r6-replay-test-control-20260925-170242-35e835] stderr: context canceled
```
