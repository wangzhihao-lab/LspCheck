# [ts7 7.0.2] definition differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-definition-changed-definition-1c2318`, signature `ts7|r6_crossimpl|definition:changed`, case family `definition`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/definition` on `test/commands/store-git.test.ts` line 151, column 24 (LSP position {line: 150, character: 23}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "test/commands/store-git.test.ts",
  5,
  12,
  5,
  16
 ]
]
```

Actual:

```json
[
 [
  "node_modules/.pnpm/@types+node@20.19.43/node_modules/@types/node/path.d.ts",
  18,
  14,
  18,
  18
 ],
 [
  "node_modules/.pnpm/@types+node@20.19.43/node_modules/@types/node/path.d.ts",
  185,
  10,
  185,
  14
 ]
]
```

Project file `test/commands/store-git.test.ts`:

```
 148 |     const storeRoot = mkdir('convert-context');
 149 |     const gitEnv = { ...env, ...isolatedGitEnv(tempDir) };
 150 |     createHealthyOpenSpecRoot(storeRoot);
 151 |     fs.writeFileSync(path.join(storeRoot, 'openspec', 'specs', 'keep-me.md'), 'user spec\n');
 152 |     // Old beta files outside the store shape stay out of the commit.
 153 |     fs.writeFileSync(path.join(storeRoot, 'workspace.yaml'), 'old: beta\n');
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-definition-changed-definition-1c2318/repro.json
```

## Evidence and reduction

- representative 15682bd48ce1-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, vercel/hyper@30ec0a2a91de, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#1673](https://github.com/microsoft/typescript-go/issues/1673) Panic on textDocument/definition (closed, 2025-09-03, 8 comments)
- [microsoft/typescript-go#2183](https://github.com/microsoft/typescript-go/issues/2183) cannot resolve type definition with type:module (closed, 2025-12-03, 8 comments)
- [microsoft/typescript-go#3026](https://github.com/microsoft/typescript-go/issues/3026) TypeScript Native Preview VS Code extension status bar color is confusing (closed, 2026-03-09, 3 comments)
- [microsoft/typescript-go#2598](https://github.com/microsoft/typescript-go/issues/2598) Auto-imports broken in JS files when user preferences are used (closed, 2026-01-28, 16 comments)
- [microsoft/typescript-go#829](https://github.com/microsoft/typescript-go/issues/829) const enum is not work (closed, 2025-04-27, 8 comments)
- [microsoft/typescript-go#4863](https://github.com/microsoft/typescript-go/issues/4863) TS7 fails to emit types for `@type`-annotated functions when they reference externally-defined symbols (closed, 2026-08-10, 0 comments)
- [microsoft/typescript-go#4740](https://github.com/microsoft/typescript-go/issues/4740) Divergence from tsc: assignment accepted by 5.9/6.0 is rejected by `tsgo` (recursive DeepPartial + contravariant `this` + UnionToIntersection cycle, reduced from chart.js) (closed, 2026-07-25, 2 comments)
- [microsoft/typescript-go#4388](https://github.com/microsoft/typescript-go/issues/4388) Parameters not automatically filled for JSdoc comments (closed, 2026-06-22, 9 comments)
- queries: `definition wrong repo:microsoft/typescript-go is:issue`; `definition "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr1c2318-r6-replay-test-baseline-20260925-163628-5be6a5] stderr: context canceled
[ts7-7.0.2-tr1c2318-r6-replay-test-control-20260925-163637-727b5a] stderr: context canceled
```
