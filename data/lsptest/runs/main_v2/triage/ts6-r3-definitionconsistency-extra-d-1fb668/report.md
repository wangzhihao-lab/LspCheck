# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-extra-d-1fb668`, signature `ts6|r3_routes|definitionConsistency:extra`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `packages/signals/tests/latest-plain-write-purity.test.ts` at line 27, column 5 (LSP position {line: 26, character: 4}) gives the expected set; didOpen `packages/signals/src/core/scheduler.ts` and `textDocument/definition` at the reference line 442, column 22 (LSP position {line: 441, character: 21}) must give the same set.

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

Project file `packages/signals/src/core/scheduler.ts`:

```
 439 | export function scheduleWithheld(): void {
 440 |   if (withheld) {
 441 |     withheld = false;
 442 |     queueMicrotask(flush);
 443 |   }
 444 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r3-definitionconsistency-extra-d-1fb668/repro.json
```

## Evidence and reduction

- representative 08c8c634e424-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects hexojs/hexo@751e856691bf, solidjs/solid@4b62bc29e04b, vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 1, 2

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
