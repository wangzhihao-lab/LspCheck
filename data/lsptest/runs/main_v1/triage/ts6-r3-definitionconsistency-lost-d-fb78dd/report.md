# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-lost-d-fb78dd`, signature `ts6|r3_routes|definitionConsistency:lost`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `pmndrs/zustand@b57db4f86ef1` (corpus, commit b57db4f86ef179285da216eeb291266da82c361c), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/middleware/devtools.ts` at line 254, column 46 (LSP position {line: 253, character: 45}) gives the expected set; didOpen `src/middleware/devtools.ts` and `textDocument/definition` at the reference line 191, column 56 (LSP position {line: 190, character: 55}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/middleware/devtools.ts",
  190,
  52,
  190,
  59
 ]
]
```

Actual:

```json
[]
```

Project file `src/middleware/devtools.ts`:

```
 188 | const devtoolsImpl: DevtoolsImpl =
 189 |   (fn, devtoolsOptions = {}) =>
 190 |   (set, get, api) => {
 191 |     const { enabled, anonymousActionType, store, ...options } = devtoolsOptions
     ...
 193 |     type S = ReturnType<typeof fn> & {
 194 |       [store: string]: ReturnType<typeof fn>
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r3-definitionconsistency-lost-d-fb78dd/repro.json
```

## Evidence and reduction

- representative 71f6d8ce3149-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects pmndrs/zustand@b57db4f86ef1, timings settled, seeds 2

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
