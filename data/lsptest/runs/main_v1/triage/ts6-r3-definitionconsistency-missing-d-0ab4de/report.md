# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-missing-d-0ab4de`, signature `ts6|r3_routes|definitionConsistency:missing`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `test/commands/store-git.test.ts` at line 69, column 41 (LSP position {line: 68, character: 40}) gives the expected set; didOpen `src/core/global-config.ts` and `textDocument/definition` at the reference line 100, column 24 (LSP position {line: 99, character: 23}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/core/global-config.ts",
  87,
  2,
  87,
  5
 ],
 [
  "test/commands/store-git.test.ts",
  48,
  6,
  48,
  9
 ]
]
```

Actual:

```json
[
 [
  "src/core/global-config.ts",
  87,
  2,
  87,
  5
 ]
]
```

Project file `src/core/global-config.ts`:

```
  97 | }
     ...
  99 | export function getGlobalDataDir(options: GlobalDataDirOptions = {}): string {
 100 |   const env = options.env ?? process.env;
 101 |   const platform = options.platform ?? os.platform();
     ...
 103 |   // XDG_DATA_HOME takes precedence on all platforms when explicitly set
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r3-definitionconsistency-missing-d-0ab4de/repro.json
```

## Evidence and reduction

- representative 4ef417928764-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, upstash/context7@6477e43e31d2, vercel/hyper@30ec0a2a91de, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#795](https://github.com/typescript-language-server/typescript-language-server/issues/795) Go to definition is not working on neovim (closed, 2023-11-12, 2 comments)
- [typescript-language-server/typescript-language-server#507](https://github.com/typescript-language-server/typescript-language-server/issues/507) Possibility of including Go to Source Definition? (closed, 2022-07-03, 4 comments)
- [typescript-language-server/typescript-language-server#431](https://github.com/typescript-language-server/typescript-language-server/issues/431) Go to definition function broken in monorepo project (closed, 2022-04-10, 4 comments)
- [typescript-language-server/typescript-language-server#60](https://github.com/typescript-language-server/typescript-language-server/issues/60) Error: No Project. When starting LS from a bundled electron Theia application (closed, 2018-09-02, 9 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#277](https://github.com/typescript-language-server/typescript-language-server/issues/277) Using typescript plugins through neovim-lsp (closed, 2021-10-31, 10 comments)
- [typescript-language-server/typescript-language-server#264](https://github.com/typescript-language-server/typescript-language-server/issues/264) Inlay Hints return empty result (closed, 2021-10-06, 4 comments)
- [typescript-language-server/typescript-language-server#203](https://github.com/typescript-language-server/typescript-language-server/issues/203) Javascript: Jump to declaration still not at JSDT's level (closed, 2021-04-16, 9 comments)
- queries: `"go to definition" in:title repo:typescript-language-server/typescript-language-server is:issue`; `definition missing repo:typescript-language-server/typescript-language-server is:issue`; `definition "go to definition" repo:typescript-language-server/typescript-language-server is:issue`; `definition inconsistent repo:typescript-language-server/typescript-language-server is:issue`; `"go to definition" in:title repo:microsoft/TypeScript is:issue`; `definition missing repo:microsoft/TypeScript is:issue`; `definition "go to definition" repo:microsoft/TypeScript is:issue`; `definition inconsistent repo:microsoft/TypeScript is:issue`
