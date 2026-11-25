# [ts6 6.0.3] hover shows a different text after query order

Draft for the author (not filed). Group `ts6-r1-hover-text-h8-2ce168`, signature `ts6|r1_history|hover:text`, case family `H8`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `vadimdemedes/ink@02ae1e59e7c2` (corpus, commit 02ae1e59e7c288e971616100c4c11bcca6b5761b), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/dom.ts`
3. request: `request src/dom.ts typeDefinition at (163, 9)`
4. Timing: send the steps 0 ms apart without waiting, then wait until idle.
5. textDocument/didOpen `src/components/FocusContext.ts`, `test/colon-colors.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
6. Query `textDocument/hover` on `src/dom.ts` line 150, column 37 (LSP position {line: 149, character: 36}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "(parameter) newChildNode: DOMElement | TextNode",
 [
  149,
  30,
  149,
  42
 ]
]
```

Actual:

```json
[
 "(parameter) newChildNode: TextNode | DOMElement",
 [
  149,
  30,
  149,
  42
 ]
]
```

Project file `src/dom.ts`:

```
 147 | 	if (index >= 0) {
 148 | 		node.childNodes.splice(index, 0, newChildNode);
 149 | 		if (newChildNode.yogaNode) {
 150 | 			node.yogaNode?.insertChild(newChildNode.yogaNode, index);
 151 | 		}
 152 | 	} else {
 153 | 		node.childNodes.push(newChildNode);
     ...
 161 | 	}
     ...
 163 | 	if (node.nodeName === 'ink-text' || node.nodeName === 'ink-virtual-text') {
 164 | 		markNodeAsDirty(node);
 165 | 	}
 166 | };
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-hover-text-h8-2ce168/repro.json
```

## Evidence and reduction

- representative df02b705037e-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 10 -> 2 (10 probes, 188.504 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects vadimdemedes/ink@02ae1e59e7c2, timings race0, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#865](https://github.com/typescript-language-server/typescript-language-server/issues/865) Fully resolve type aliases  (closed, 2024-02-02, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#445](https://github.com/typescript-language-server/typescript-language-server/issues/445) Issue with tsconfig and first file opened (closed, 2022-05-03, 4 comments)
- [typescript-language-server/typescript-language-server#803](https://github.com/typescript-language-server/typescript-language-server/issues/803) Server error "Could not find source file" on opening second file in a project with large amount of code (closed, 2023-11-14, 4 comments)
- [typescript-language-server/typescript-language-server#191](https://github.com/typescript-language-server/typescript-language-server/issues/191) doRequestDiagnostics of LspServer looks did not handle err? no 'catch'? (closed, 2021-03-11, 61 comments)
- [microsoft/TypeScript#63758](https://github.com/microsoft/TypeScript/issues/63758) Investigate decorator initialization order re: renames of classes (open, 2026-08-18, 0 comments)
- queries: `order in:title repo:typescript-language-server/typescript-language-server is:issue`; `hover wrong repo:typescript-language-server/typescript-language-server is:issue`; `hover order repo:typescript-language-server/typescript-language-server is:issue`; `hover stale repo:typescript-language-server/typescript-language-server is:issue`; `order in:title repo:microsoft/TypeScript is:issue`; `hover wrong repo:microsoft/TypeScript is:issue`; `hover order repo:microsoft/TypeScript is:issue`; `hover stale repo:microsoft/TypeScript is:issue`
