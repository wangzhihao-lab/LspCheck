# [ts6 6.0.3] signatureHelp changes its answer after file rename round trip

Draft for the author (not filed). Group `ts6-r1-signaturehelp-changed-h5-db5a5e`, signature `ts6|r1_history|signatureHelp:changed`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `DayuanJiang/next-ai-draw-io@58b73ef761d8` (corpus, commit 58b73ef761d8a5e5b2afa2c360428d3dea996312), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open lib/server-model-config.ts (then 200 ms)`
3. Timing: send the steps 200 ms apart without waiting, then wait until idle.
4. textDocument/didOpen `app/api/validate-diagram/route.ts`, `lib/types/model-config.ts` (the query step opens every target file that is not open), then wait until the server is idle.
5. Query `textDocument/signatureHelp` on `lib/server-model-config.ts` line 22, column 14 (LSP position {line: 21, character: 13}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"object(shape?: { name: z.ZodString; provider: z.ZodType<ProviderName, unknown, z.core.$ZodTypeInternals<ProviderName, unknown>>; models: z.ZodArray<z.ZodString>; apiKeyEnv: z.ZodOptional<...>; baseUrlEnv: z.ZodOptional<...>; default: z.ZodOptional<...>; } | undefined, params?: string | { error?: string | z.core.$ZodErrorMap<NonNullable<z.core.$ZodIssueInvalidType<unknown> | z.core.$ZodIssueUnrecognizedKeys>> | undefined; message?: string | undefined | undefined; } | undefined): z.ZodObject<{ name: z.ZodString; provider: z.ZodType<ProviderName, unknown, z.core.$ZodTypeInternals<ProviderName, unknown>>; models: z.ZodArray<z.ZodString>; apiKeyEnv: z.ZodOptional<...>; baseUrlEnv: z.ZodOptional<...>; default: z.ZodOptional<...>; }, z.core.$strip>"
```

Actual:

```json
"object(shape?: { name: z.ZodString; provider: z.ZodType<ProviderName, unknown, z.core.$ZodTypeInternals<ProviderName, unknown>>; models: z.ZodArray<z.ZodString>; apiKeyEnv: z.ZodOptional<...>; baseUrlEnv: z.ZodOptional<...>; default: z.ZodOptional<...>; } | undefined, params?: string | { error?: string | z.core.$ZodErrorMap<NonNullable<z.core.$ZodIssueUnrecognizedKeys | z.core.$ZodIssueInvalidType<unknown>>> | undefined; message?: string | undefined | undefined; } | undefined): z.ZodObject<{ name: z.ZodString; provider: z.ZodType<ProviderName, unknown, z.core.$ZodTypeInternals<ProviderName, unknown>>; models: z.ZodArray<z.ZodString>; apiKeyEnv: z.ZodOptional<...>; baseUrlEnv: z.ZodOptional<...>; default: z.ZodOptional<...>; }, z.core.$strip>"
```

Project file `lib/server-model-config.ts`:

```
  19 |     // e.g., "OPENAI_API_KEY_TEAM_A" or ["OPENAI_KEY_1", "OPENAI_KEY_2"]
  20 |     apiKeyEnv: z
  21 |         .union([z.string().min(1), z.array(z.string().min(1)).min(1)])
  22 |         .optional(),
  23 |     // Optional: custom environment variable name for base URL
  24 |     baseUrlEnv: z.string().min(1).optional(),
  25 |     // Optional: mark the first model in this provider as the default
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-signaturehelp-changed-h5-db5a5e/repro.json
```

## Evidence and reduction

- representative 83d8f26e74ae-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 1 (6 probes, 169.663 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects DayuanJiang/next-ai-draw-io@58b73ef761d8, timings race0, race200, settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [microsoft/TypeScript#30039](https://github.com/microsoft/TypeScript/issues/30039) Refactor rename file + rename function (open, 2019-01-23, 6 comments)
- [microsoft/TypeScript#29294](https://github.com/microsoft/TypeScript/issues/29294) Rename file when renaming default export (open, 2019-01-05, 0 comments)
- [microsoft/TypeScript#29375](https://github.com/microsoft/TypeScript/issues/29375) Suggest renaming file from .ts to .tsx if needed? (open, 2019-01-11, 0 comments)
- [microsoft/TypeScript#44411](https://github.com/microsoft/TypeScript/issues/44411) Renaming file doesn't update imports in other projects which reference this project (open, 2021-06-03, 1 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" wrong repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `"signature help" wrong repo:microsoft/TypeScript is:issue`; `"signature help" "rename file" repo:microsoft/TypeScript is:issue`; `"signature help" stale repo:microsoft/TypeScript is:issue`
