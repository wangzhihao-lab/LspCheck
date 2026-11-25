# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-extra-d-1fb668`, signature `ts6|r3_routes|definitionConsistency:extra`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `vercel/hyper@30ec0a2a91de` (corpus, commit 30ec0a2a91de17eeb32dd71998fe8a8ec59f98eb), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `app/menus/menus/window.ts` at line 44, column 15 (LSP position {line: 43, character: 14}) gives the expected set; didOpen `app/index.ts` and `textDocument/definition` at the reference line 183, column 17 (LSP position {line: 182, character: 16}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "node_modules/electron/electron.d.ts",
  14683,
  4,
  14683,
  9
 ]
]
```

Actual:

```json
[
 [
  "node_modules/electron/electron.d.ts",
  5713,
  4,
  5713,
  9
 ],
 [
  "node_modules/electron/electron.d.ts",
  14683,
  4,
  14683,
  9
 ]
]
```

Project file `app/index.ts`:

```
 180 |         if (process.platform === 'darwin') {
 181 |           const dockMenu = Menu.buildFromTemplate([
 182 |             {
 183 |               label: 'New Window',
 184 |               click() {
 185 |                 createWindow();
 186 |               }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r3-definitionconsistency-extra-d-1fb668/repro.json
```

## Evidence and reduction

- representative 2e5b5cb87f65-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, vercel/hyper@30ec0a2a91de, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#795](https://github.com/typescript-language-server/typescript-language-server/issues/795) Go to definition is not working on neovim (closed, 2023-11-12, 2 comments)
- [typescript-language-server/typescript-language-server#507](https://github.com/typescript-language-server/typescript-language-server/issues/507) Possibility of including Go to Source Definition? (closed, 2022-07-03, 4 comments)
- [typescript-language-server/typescript-language-server#431](https://github.com/typescript-language-server/typescript-language-server/issues/431) Go to definition function broken in monorepo project (closed, 2022-04-10, 4 comments)
- [typescript-language-server/typescript-language-server#926](https://github.com/typescript-language-server/typescript-language-server/issues/926) "Maximum call stack size exceeded" error with Node v23.0.0 in Neovim (closed, 2024-10-19, 5 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#191](https://github.com/typescript-language-server/typescript-language-server/issues/191) doRequestDiagnostics of LspServer looks did not handle err? no 'catch'? (closed, 2021-03-11, 61 comments)
- queries: `"go to definition" in:title repo:typescript-language-server/typescript-language-server is:issue`; `definition extra repo:typescript-language-server/typescript-language-server is:issue`; `definition "go to definition" repo:typescript-language-server/typescript-language-server is:issue`; `definition inconsistent repo:typescript-language-server/typescript-language-server is:issue`; `"go to definition" in:title repo:microsoft/TypeScript is:issue`; `definition extra repo:microsoft/TypeScript is:issue`; `definition "go to definition" repo:microsoft/TypeScript is:issue`; `definition inconsistent repo:microsoft/TypeScript is:issue`
