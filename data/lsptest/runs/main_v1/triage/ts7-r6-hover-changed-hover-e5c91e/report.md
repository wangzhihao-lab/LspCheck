# [ts7 7.0.2] hover differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-hover-changed-hover-e5c91e`, signature `ts7|r6_crossimpl|hover:changed`, case family `hover`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/hover` on `test/commands/store-git.test.ts` line 69, column 41 (LSP position {line: 68, character: 40}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"(property) GlobalDataDirOptions.env?: any"
```

Actual:

```json
"(property) GlobalDataDirOptions.env?: NodeJS.ProcessEnv | undefined"
```

Project file `test/commands/store-git.test.ts`:

```
  66 |       OPEN_SPEC_INTERACTIVE: '0',
  67 |       OPENSPEC_TELEMETRY: '0',
  68 |     };
  69 |     globalDataDir = getGlobalDataDir({ env });
     ...
  71 |     originalEnv = { ...process.env };
  72 |     originalCwd = process.cwd();
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-hover-changed-hover-e5c91e/repro.json
```

## Evidence and reduction

- representative 15682bd48ce1-v05: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, react-hook-form/react-hook-form@5fd9ef65290b, upstash/context7@6477e43e31d2, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4758](https://github.com/microsoft/typescript-go/issues/4758) disableSourceOfProjectReferenceRedirect causes lodash per-method submodule import to resolve to the wrong function (closed, 2026-07-27, 7 comments)
- [microsoft/typescript-go#3422](https://github.com/microsoft/typescript-go/issues/3422) Wrong function signature and missing invoking description in hover (closed, 2026-04-16, 0 comments)
- [microsoft/typescript-go#3455](https://github.com/microsoft/typescript-go/issues/3455) Wrong highlight in hover for generic func type with `property` and `accessor` prefix (closed, 2026-04-21, 0 comments)
- [microsoft/typescript-go#3506](https://github.com/microsoft/typescript-go/issues/3506) Verbose quick info crash when base type constructs an intersection (closed, 2026-04-22, 5 comments)
- [microsoft/typescript-go#3302](https://github.com/microsoft/typescript-go/issues/3302) panic crash (closed, 2026-03-31, 3 comments)
- [microsoft/typescript-go#4677](https://github.com/microsoft/typescript-go/issues/4677) JSDoc (TSDoc ???) is not shown for object literal properties on hover (closed, 2026-07-20, 1 comments)
- [microsoft/typescript-go#4683](https://github.com/microsoft/typescript-go/issues/4683) Generic type parameter inferred differently across two call-site positions with opposite variance (narrow type vs union) (closed, 2026-07-20, 2 comments)
- [microsoft/typescript-go#3659](https://github.com/microsoft/typescript-go/issues/3659) Behavior difference: JSDoc comments are stripped for mapped types (closed, 2026-04-29, 2 comments)
- queries: `hover wrong repo:microsoft/typescript-go is:issue`; `hover "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tre5c91e-r6-replay-test-baseline-20260925-171122-20c5a5] stderr: context canceled
[ts7-7.0.2-tre5c91e-r6-replay-test-control-20260925-171131-6d7902] stderr: context canceled
```
