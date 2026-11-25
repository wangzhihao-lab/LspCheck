# [ts6 6.0.3] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `ts6-r3-definitionconsistency-changed-d-bf619d`, signature `ts6|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `packages/web/test/latest-shadow-owned-write-issue-3378.spec.tsx` at line 50, column 19 (LSP position {line: 49, character: 18}) gives the expected set; didOpen `packages/element/test/element.spec.tsx` and `textDocument/definition` at the reference line 159, column 35 (LSP position {line: 158, character: 34}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.dom.d.ts",
  13912,
  8,
  13912,
  19
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.dom.d.ts",
  13913,
  8,
  13913,
  19
 ]
]
```

Actual:

```json
[
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.dom.d.ts",
  13225,
  8,
  13225,
  19
 ],
 [
  "<servers>/ts6-6.0.3/node_modules/typescript/lib/lib.dom.d.ts",
  13226,
  8,
  13226,
  19
 ]
]
```

Project file `packages/element/test/element.spec.tsx`:

```
 156 |     );
 157 |     const child = root.querySelector(childTag)!;
     ...
 159 |     expect(child.shadowRoot!.textContent).toBe("ancestor");
 160 |     dispose();
 161 |     root.remove();
 162 |   });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r3-definitionconsistency-changed-d-bf619d/repro.json
```

## Evidence and reduction

- representative 02943665191c-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects solidjs/solid@4b62bc29e04b, umami-software/umami@12ad773d621f, vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#795](https://github.com/typescript-language-server/typescript-language-server/issues/795) Go to definition is not working on neovim (closed, 2023-11-12, 2 comments)
- [typescript-language-server/typescript-language-server#507](https://github.com/typescript-language-server/typescript-language-server/issues/507) Possibility of including Go to Source Definition? (closed, 2022-07-03, 4 comments)
- [typescript-language-server/typescript-language-server#431](https://github.com/typescript-language-server/typescript-language-server/issues/431) Go to definition function broken in monorepo project (closed, 2022-04-10, 4 comments)
- [typescript-language-server/typescript-language-server#216](https://github.com/typescript-language-server/typescript-language-server/issues/216) Multiple and wrong definition (closed, 2021-06-03, 38 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#632](https://github.com/typescript-language-server/typescript-language-server/issues/632) Wrong or confusing Semantic Token Types reported (closed, 2022-11-23, 1 comments)
- [typescript-language-server/typescript-language-server#495](https://github.com/typescript-language-server/typescript-language-server/issues/495) Wrong tsconfig.json being used in monorepo (closed, 2022-06-16, 4 comments)
- queries: `"go to definition" in:title repo:typescript-language-server/typescript-language-server is:issue`; `definition wrong repo:typescript-language-server/typescript-language-server is:issue`; `definition "go to definition" repo:typescript-language-server/typescript-language-server is:issue`; `definition inconsistent repo:typescript-language-server/typescript-language-server is:issue`; `"go to definition" in:title repo:microsoft/TypeScript is:issue`; `definition wrong repo:microsoft/TypeScript is:issue`; `definition "go to definition" repo:microsoft/TypeScript is:issue`; `definition inconsistent repo:microsoft/TypeScript is:issue`
