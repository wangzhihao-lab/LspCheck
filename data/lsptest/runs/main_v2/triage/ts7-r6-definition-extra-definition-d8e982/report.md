# [ts7 7.0.2] definition differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-definition-extra-definition-d8e982`, signature `ts7|r6_crossimpl|definition:extra`, case family `definition`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/definition` on `packages/signals/tests/latest-plain-write-purity.test.ts` line 27, column 5 (LSP position {line: 26, character: 4}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "packages/signals/src/core/scheduler.ts",
  1557,
  16,
  1557,
  21
 ]
]
```

Actual:

```json
[
 [
  "packages/signals/src/core/scheduler.ts",
  1557,
  16,
  1557,
  21
 ],
 [
  "packages/signals/src/core/scheduler.ts",
  1558,
  16,
  1558,
  21
 ],
 [
  "packages/signals/src/core/scheduler.ts",
  1559,
  16,
  1559,
  21
 ]
]
```

Project file `packages/signals/tests/latest-plain-write-purity.test.ts`:

```
   1 | /**
   2 |  * #3009: `latest()` is not pure when the memo itself uses `latest()`.
   3 |  *
   4 |  * A memo whose compute reads `latest(count)` subscribes to count's shadow
   5 |  * companion, so a plain `setCount()` wakes it through the optimistic channel
   6 |  * (the companion's wake-only lane) and marks it OPTIMISTIC_DIRTY. A subsequent
   7 |  * `latest(m)` pull then recomputed `m` under lane posture, which direct-commits
   8 |  * `_value` — leaking the queued plain write into committed reads before the
   9 |  * flush: `m()` returned the latest value instead of the committed one.
  10 |  *
  11 |  * Writes now become visible at flush for every channel, so `latest(m)` no
  12 |  * longer pulls at all before the flush — the leak has no path. The purity
  13 |  * invariant these tests pin is unchanged: probing `latest(m)` never changes
  14 |  * what plain `m()` returns, and the flush commits and notifies normally.
  15 |  */
  16 | import { createEffect, createMemo, createRoot, createSignal, flush, latest } from "../src/index.js";
  17 | import { isPending } from "../src/index.js";
     ...
  19 | it("latest(m) does not change what plain m() returns before the flush (#3009)", () => {
  20 |   let m!: () => number;
  21 |   let setCount!: (v: number) => void;
  22 |   createRoot(() => {
  23 |     const [count, set] = createSignal(0);
  24 |     setCount = set;
  25 |     m = createMemo(() => latest(count) * 2);
  26 |   });
  27 |   flush();
     ...
  29 |   setCount(4);
  30 |   expect(m()).toBe(0); // A
  31 |   expect(latest(m)).toBe(0); // B — the flushed world (was 8 under the pull)
  32 |   expect(m()).toBe(0); // C
  33 |   expect(latest(m)).toBe(0); // probe repeats stay consistent
  34 |   expect(m()).toBe(0);
  35 |   flush();
  36 |   expect(m()).toBe(8);
  37 |   expect(latest(m)).toBe(8);
  38 | });
     ...
  40 | it("the flush commits and notifies effects after latest() probes (#3009)", () => {
  41 |   let m!: () => number;
  42 |   let setCount!: (v: number) => void;
  43 |   const effectLog: number[] = [];
  44 |   createRoot(() => {
  45 |     const [count, set] = createSignal(0);
  46 |     setCount = set;
  47 |     m = createMemo(() => latest(count) * 2);
  48 |     createEffect(m, v => void effectLog.push(v));
  49 |   });
  50 |   flush();
  51 |   expect(effectLog).toEqual([0]);
     ...
  53 |   setCount(4);
  54 |   expect(latest(m)).toBe(0);
  55 |   flush();
  56 |   expect(m()).toBe(8);
  57 |   expect(latest(m)).toBe(8);
  58 |   expect(effectLog).toEqual([0, 8]);
     ...
  60 |   // Later writes keep flowing normally.
  61 |   setCount(10);
  62 |   flush();
  63 |   expect(m()).toBe(20);
  64 |   expect(effectLog).toEqual([0, 8, 20]);
  65 | });
     ...
  67 | it("chained memos over latest() stay pure (#3009)", () => {
  68 |   let m!: () => number;
  69 |   let m2!: () => number;
  70 |   let setCount!: (v: number) => void;
  71 |   createRoot(() => {
  72 |     const [count, set] = createSignal(1);
  73 |     setCount = set;
  74 |     m = createMemo(() => latest(count) * 2);
  75 |     m2 = createMemo(() => m() + 1);
  76 |   });
  77 |   flush();
  78 |   expect(m2()).toBe(3);
     ...
  80 |   setCount(5);
  81 |   // Probing through the chain must not commit any intermediate node.
  82 |   expect(latest(m2)).toBe(3);
  83 |   expect(m()).toBe(2);
  84 |   expect(m2()).toBe(3);
     ...
  86 |   flush();
  87 |   expect(m()).toBe(10);
  88 |   expect(m2()).toBe(11);
  89 |   expect(latest(m2)).toBe(11);
  90 | });
     ...
  92 | it("an isPending probe on the same shape does not pollute committed reads (#3009)", () => {
  93 |   let m!: () => number;
  94 |   let setCount!: (v: number) => void;
  95 |   createRoot(() => {
  96 |     const [count, set] = createSignal(0);
  97 |     setCount = set;
  98 |     m = createMemo(() => latest(count) * 2);
  99 |   });
 100 |   flush();
     ...
 102 |   setCount(4);
 103 |   isPending(m);
 104 |   expect(m()).toBe(0);
 105 |   flush();
 106 |   expect(m()).toBe(8);
 107 | });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-definition-extra-definition-d8e982/repro.json
```

## Evidence and reduction

- representative 4224a39ee10c-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects hexojs/hexo@751e856691bf, pear-devs/pear-desktop@3ff0a86231fe, solidjs/solid@4b62bc29e04b, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4000](https://github.com/microsoft/typescript-go/issues/4000) Make typedef exporting explicit (closed, 2026-05-20, 7 comments)
- [microsoft/typescript-go#4037](https://github.com/microsoft/typescript-go/issues/4037) TS2304 when a generic (@template) function JSDoc contains @overload (closed, 2026-05-23, 5 comments)
- [microsoft/typescript-go#4532](https://github.com/microsoft/typescript-go/issues/4532) [ServerErrors][TypeScript] main vs  (closed, 2026-07-03, 8 comments)
- [microsoft/typescript-go#3615](https://github.com/microsoft/typescript-go/issues/3615) Server stops responding after `Running scheduled diagnostics refresh` (closed, 2026-04-26, 0 comments)
- [microsoft/typescript-go#4863](https://github.com/microsoft/typescript-go/issues/4863) TS7 fails to emit types for `@type`-annotated functions when they reference externally-defined symbols (closed, 2026-08-10, 0 comments)
- [microsoft/typescript-go#4740](https://github.com/microsoft/typescript-go/issues/4740) Divergence from tsc: assignment accepted by 5.9/6.0 is rejected by `tsgo` (recursive DeepPartial + contravariant `this` + UnionToIntersection cycle, reduced from chart.js) (closed, 2026-07-25, 2 comments)
- [microsoft/typescript-go#4388](https://github.com/microsoft/typescript-go/issues/4388) Parameters not automatically filled for JSdoc comments (closed, 2026-06-22, 9 comments)
- queries: `definition extra repo:microsoft/typescript-go is:issue`; `definition "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trd8e982-r6-replay-test-baseline-20261118-222054-a90408] stderr: context canceled
[ts7-7.0.2-trd8e982-r6-replay-test-control-20261118-222101-5e66ca] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-trd8e982-r6-replay-test-control-20261118-222101-5e66ca] stderr: context canceled
```
