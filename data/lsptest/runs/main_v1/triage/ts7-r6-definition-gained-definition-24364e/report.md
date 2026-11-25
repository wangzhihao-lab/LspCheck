# [ts7 7.0.2] definition differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-definition-gained-definition-24364e`, signature `ts7|r6_crossimpl|definition:gained`, case family `definition`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/definition` on `test/commands/store-git.test.ts` line 185, column 20 (LSP position {line: 184, character: 19}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/globals.d.ts",
  2,
  12,
  2,
  19
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/process.d.ts",
  140,
  12,
  140,
  19
 ],
 [
  "~/Library/Caches/typescript/7.0/node_modules/@types/node/process.d.ts",
  141,
  18,
  141,
  25
 ],
 [
  "node_modules/.pnpm/@types+node@20.19.43/node_modules/@types/node/globals.d.ts",
  2,
  12,
  2,
  19
 ],
 [
  "node_modules/.pnpm/@types+node@20.19.43/node_modules/@types/node/process.d.ts",
  121,
  12,
  121,
  19
 ],
 [
  "node_modules/@types/node/globals.d.ts",
  2,
  12,
  2,
  19
 ],
 [
  "node_modules/@types/node/process.d.ts",
  121,
  12,
  121,
  19
 ]
]
```

Project file `test/commands/store-git.test.ts`:

```
 182 |     // A clone of the converted store is immediately a healthy root.
 183 |     const cloneRoot = path.join(tempDir, 'convert-clone');
 184 |     execFileSync('git', ['clone', storeRoot, cloneRoot], {
 185 |       env: { ...process.env, ...gitEnv },
 186 |       stdio: 'ignore',
 187 |     });
 188 |     for (const required of [
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-definition-gained-definition-24364e/repro.json
```

## Evidence and reduction

- representative 15682bd48ce1-v03: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, react-hook-form/react-hook-form@5fd9ef65290b, upstash/context7@6477e43e31d2, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#2964](https://github.com/microsoft/typescript-go/issues/2964) [ServerErrors][JavaScript] linux-x64-7.0.0-dev.20260303.1 vs  (closed, 2026-03-03, 11 comments)
- [microsoft/typescript-go#2780](https://github.com/microsoft/typescript-go/issues/2780) High memory consumption in a large pnpm monorepo (closed, 2026-02-13, 52 comments)
- [microsoft/typescript-go#4380](https://github.com/microsoft/typescript-go/issues/4380) [ServerErrors][TypeScript] main vs  (closed, 2026-06-19, 7 comments)
- [microsoft/typescript-go#2988](https://github.com/microsoft/typescript-go/issues/2988) [ServerErrors][TypeScript] main vs  (closed, 2026-03-05, 82 comments)
- [microsoft/typescript-go#4863](https://github.com/microsoft/typescript-go/issues/4863) TS7 fails to emit types for `@type`-annotated functions when they reference externally-defined symbols (closed, 2026-08-10, 0 comments)
- [microsoft/typescript-go#4740](https://github.com/microsoft/typescript-go/issues/4740) Divergence from tsc: assignment accepted by 5.9/6.0 is rejected by `tsgo` (recursive DeepPartial + contravariant `this` + UnionToIntersection cycle, reduced from chart.js) (closed, 2026-07-25, 2 comments)
- [microsoft/typescript-go#4388](https://github.com/microsoft/typescript-go/issues/4388) Parameters not automatically filled for JSdoc comments (closed, 2026-06-22, 9 comments)
- [microsoft/typescript-go#4437](https://github.com/microsoft/typescript-go/issues/4437) `checkJs` seems to default to true erroneously (closed, 2026-06-24, 6 comments)
- queries: `definition unexpected repo:microsoft/typescript-go is:issue`; `definition "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr24364e-r6-replay-test-baseline-20260925-164412-70464a] stderr: context canceled
[ts7-7.0.2-tr24364e-r6-replay-test-control-20260925-164419-e5c459] stderr: context canceled
```
