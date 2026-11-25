# [ts7 7.0.2] diagnostics differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-diagnostics-changed-2322-2503-2591-diagnostics-dee939`, signature `ts7|r6_crossimpl|diagnostics:changed:2322,2503,2591`, case family `diagnostics`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/diagnostic` on `test/commands/store-git.test.ts` for the whole file; compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  105,
  4,
  105,
  11,
  0,
  "2591",
  "",
  ""
 ],
 [
  106,
  9,
  106,
  16,
  0,
  "2591",
  "",
  ""
 ],
 [
  112,
  11,
  112,
  18,
  0,
  "2591",
  "",
  ""
 ],
 [
  113,
  11,
  113,
  18,
  0,
  "2591",
  "",
  ""
 ],
 [
  114,
  4,
  114,
  11,
  0,
  "2591",
  "",
  ""
 ],
 [
  115,
  22,
  115,
  28,
  0,
  "2503",
  "",
  ""
 ],
 [
  115,
  5,
  115,
  12,
  0,
  "2591",
  "",
  ""
 ],
 [
  143,
  11,
  143,
  18,
  0,
  "2591",
  "",
  ""
 ],
 [
  184,
  16,
  184,
  23,
  0,
  "2591",
  "",
  ""
 ],
 [
  2,
  29,
  2,
  49,
  0,
  "2591",
  "",
  ""
 ],
 [
  202,
  28,
  202,
  35,
  0,
  "2591",
  "",
  ""
 ],
 [
  238,
  28,
  238,
  35,
  0,
  "2591",
  "",
  ""
 ],
 [
  297,
  28,
  297,
  35,
  0,
  "2591",
  "",
  ""
 ],
 [
  3,
  20,
  3,
  29,
  0,
  "2591",
  "",
  ""
 ],
 [
  347,
  28,
  347,
  35,
  0,
  "2591",
  "",
  ""
 ],
 [
  4,
  20,
  4,
  29,
  0,
  "2591",
  "",
  ""
 ],
 [
  48,
  11,
  48,
  17,
  0,
  "2503",
  "",
  ""
 ],
 [
  49,
  19,
  49,
  25,
  0,
  "2503",
  "",
  ""
 ],
 [
  5,
  22,
  5,
  33,
  0,
  "2591",
  "",
  ""
 ],
 [
  70,
  23,
  70,
  30,
  0,
  "2591",
  "",
  ""
 ],
 [
  71,
  18,
  71,
  25,
  0,
  "2591",
  "",
  ""
 ],
 [
  72,
  24,
  72,
  31,
  0,
  "2591",
  "",
  ""
 ],
 [
  72,
  41,
  72,
  47,
  0,
  "2503",
  "",
  ""
 ],
 [
  73,
  23,
  73,
  30,
  0,
  "2591",
  "",
  ""
 ],
 [
  74,
  4,
  74,
  11,
  0,
  "2591",
  "",
  ""
 ],
 [
  78,
  4,
  78,
  11,
  0,
  "2591",
  "",
  ""
 ],
 [
 
... (1721 characters)
```

Actual:

```json
[
 [
  80,
  4,
  80,
  68,
  0,
  "2322",
  "",
  ""
 ]
]
```

Project file `test/commands/store-git.test.ts`:

```
   1 | import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
   2 | import { Command } from 'commander';
   3 | import { execFileSync } from 'node:child_process';
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-diagnostics-changed-2322-2503-2591-diagnostics-dee939/repro.json
```

## Evidence and reduction

- representative 15682bd48ce1-v04: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4827](https://github.com/microsoft/typescript-go/issues/4827) Generic type argument inferred from the wrong inference slot (cyclic union-of-intersections); larger programs show scheduling-dependent diagnostics (closed, 2026-08-04, 1 comments)
- [microsoft/typescript-go#4262](https://github.com/microsoft/typescript-go/issues/4262) Non-deterministic `TS2305 "has no exported member"` errors across project references with `--emitDeclarationOnly` (closed, 2026-06-10, 8 comments)
- [microsoft/typescript-go#4314](https://github.com/microsoft/typescript-go/issues/4314) Behavior difference: tsgo misses TS2345 when a namespace translator union is called with a template-literal key union (closed, 2026-06-15, 2 comments)
- [microsoft/typescript-go#3576](https://github.com/microsoft/typescript-go/issues/3576) [Proposal] strictArrayVariance: opt-in invariance for mutable Array<T> element type (post-7.0 discussion) (closed, 2026-04-24, 5 comments)
- [microsoft/typescript-go#2511](https://github.com/microsoft/typescript-go/issues/2511) Stale diagnostics on file reload (closed, 2026-01-14, 5 comments)
- [microsoft/typescript-go#4745](https://github.com/microsoft/typescript-go/issues/4745) Native API syntactic diagnostics omit start and length (closed, 2026-07-26, 2 comments)
- [microsoft/typescript-go#4719](https://github.com/microsoft/typescript-go/issues/4719) tsgo reports type errors in external-library (node_modules) source files that tsc suppresses (closed, 2026-07-23, 2 comments)
- [microsoft/typescript-go#4129](https://github.com/microsoft/typescript-go/issues/4129) tsgo reports compiler-option diagnostics even when syntactic errors exist (closed, 2026-05-31, 0 comments)
- queries: `diagnostics wrong repo:microsoft/typescript-go is:issue`; `diagnostics "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trdee939-r6-replay-test-baseline-20260925-164658-e087b0] stderr: context canceled
[ts7-7.0.2-trdee939-r6-replay-test-control-20260925-164709-fe0211] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trdee939-r6-replay-test-control-20260925-164709-fe0211] stderr: context canceled
```
