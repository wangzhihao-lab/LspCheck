# [ts6 6.0.3] inlayHint changes its answer after query order

Draft for the author (not filed). Group `ts6-r1-inlayhint-changed-h8-8f6569`, signature `ts6|r1_history|inlayHint:changed`, case family `H8`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `vadimdemedes/ink@02ae1e59e7c2` (corpus, commit 02ae1e59e7c288e971616100c4c11bcca6b5761b), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/dom.ts (then 200 ms)`
3. request: `request src/dom.ts typeDefinition at (163, 9) (then 200 ms)`
4. Timing: send the steps 200 ms apart without waiting, then wait until idle.
5. textDocument/didOpen `src/components/FocusContext.ts`, `test/colon-colors.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
6. Query `textDocument/inlayHint` on `src/dom.ts` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  92,
  23,
  ": (nodeName: ElementNames) => DOMElement"
 ],
 [
  105,
  32,
  "measureFunc:"
 ],
 [
  105,
  53,
  "thisArg:"
 ],
 [
  111,
  28,
  ": (node: DOMElement, childNode: DOMElement) => void"
 ],
 [
  116,
  18,
  "node:"
 ],
 [
  116,
  40,
  "removeNode:"
 ],
 [
  120,
  22,
  "...items:"
 ],
 [
  124,
  3,
  "child:"
 ],
 [
  125,
  3,
  "index:"
 ],
 [
  130,
  18,
  "node:"
 ],
 [
  134,
  29,
  ": (node: DOMElement, newChildNode: DOMElement | TextNode, beforeChildNode: DOMElement | TextNode) => void"
 ],
 [
  140,
  18,
  "node:"
 ],
 [
  140,
  43,
  "removeNode:"
 ],
 [
  145,
  12,
  ": number"
 ],
 [
  145,
  39,
  "searchElement:"
 ],
 [
  147,
  25,
  "start:"
 ],
 [
  147,
  32,
  "deleteCount:"
 ],
 [
  147,
  35,
  "...items:"
 ],
 [
  149,
  30,
  "child:"
 ],
 [
  149,
  53,
  "index:"
 ],
 [
  152,
  23,
  "...items:"
 ],
 [
  156,
  4,
  "child:"
 ],
 [
  157,
  4,
  "index:"
 ],
 [
  163,
  18,
  "node:"
 ],
 [
  167,
  28,
  ": (node: DOMElement, removeNode: DOMElement | TextNode) => void"
 ],
 [
  172,
  47,
  "child:"
 ],
 [
  177,
  12,
  ": number"
 ],
 [
  177,
  39,
  "searchElement:"
 ],
 [
  179,
  25,
  "start:"
 ],
 [
  179,
  32,
  "deleteCount:"
 ],
 [
  183,
  18,
  "node:"
 ],
 [
  187,
  22,
  ": (node: DOMElement | TextNode) => void"
 ],
 [
  192,
  20,
  "node:"
 ],
 [
  207,
  28,
  ": (removeNode: DOMElement | TextNode) => void"
 ],
 [
  210,
  18,
  "node:"
 ],
 [
  213,
  25,
  ": (node: DOMElement, key: string, value:
... (3262 characters)
```

Actual:

```json
[
 [
  92,
  23,
  ": (nodeName: ElementNames) => DOMElement"
 ],
 [
  105,
  32,
  "measureFunc:"
 ],
 [
  105,
  53,
  "thisArg:"
 ],
 [
  111,
  28,
  ": (node: DOMElement, childNode: DOMElement) => void"
 ],
 [
  116,
  18,
  "node:"
 ],
 [
  116,
  40,
  "removeNode:"
 ],
 [
  120,
  22,
  "...items:"
 ],
 [
  124,
  3,
  "child:"
 ],
 [
  125,
  3,
  "index:"
 ],
 [
  130,
  18,
  "node:"
 ],
 [
  134,
  29,
  ": (node: DOMElement, newChildNode: TextNode | DOMElement, beforeChildNode: TextNode | DOMElement) => void"
 ],
 [
  140,
  18,
  "node:"
 ],
 [
  140,
  43,
  "removeNode:"
 ],
 [
  145,
  12,
  ": number"
 ],
 [
  145,
  39,
  "searchElement:"
 ],
 [
  147,
  25,
  "start:"
 ],
 [
  147,
  32,
  "deleteCount:"
 ],
 [
  147,
  35,
  "...items:"
 ],
 [
  149,
  30,
  "child:"
 ],
 [
  149,
  53,
  "index:"
 ],
 [
  152,
  23,
  "...items:"
 ],
 [
  156,
  4,
  "child:"
 ],
 [
  157,
  4,
  "index:"
 ],
 [
  163,
  18,
  "node:"
 ],
 [
  167,
  28,
  ": (node: DOMElement, removeNode: TextNode | DOMElement) => void"
 ],
 [
  172,
  47,
  "child:"
 ],
 [
  177,
  12,
  ": number"
 ],
 [
  177,
  39,
  "searchElement:"
 ],
 [
  179,
  25,
  "start:"
 ],
 [
  179,
  32,
  "deleteCount:"
 ],
 [
  183,
  18,
  "node:"
 ],
 [
  187,
  22,
  ": (node: TextNode | DOMElement) => void"
 ],
 [
  192,
  20,
  "node:"
 ],
 [
  207,
  28,
  ": (removeNode: TextNode | DOMElement) => void"
 ],
 [
  210,
  18,
  "node:"
 ],
 [
  213,
  25,
  ": (node: DOMElement, key: string, value:
... (3262 characters)
```

Project file `src/dom.ts`:

```
   1 | import Yoga, {type Node as YogaNode, type MeasureMode} from 'yoga-layout';
   2 | import measureText from './measure-text.js';
   3 | import {type Styles} from './styles.js';
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
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race200; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-inlayhint-changed-h8-8f6569/repro.json
```

## Evidence and reduction

- representative b6a8f0579f23-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 10 -> 2 (10 probes, 208.346 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects vadimdemedes/ink@02ae1e59e7c2, timings race0, race200, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#738](https://github.com/typescript-language-server/typescript-language-server/issues/738) Do not send paddingLeft = true for type parameters' hints (closed, 2023-07-07, 7 comments)
- [typescript-language-server/typescript-language-server#258](https://github.com/typescript-language-server/typescript-language-server/issues/258) Support inlay hints (closed, 2021-09-16, 0 comments)
- [typescript-language-server/typescript-language-server#264](https://github.com/typescript-language-server/typescript-language-server/issues/264) Inlay Hints return empty result (closed, 2021-10-06, 4 comments)
- [microsoft/TypeScript#63758](https://github.com/microsoft/TypeScript/issues/63758) Investigate decorator initialization order re: renames of classes (open, 2026-08-18, 0 comments)
- [microsoft/TypeScript#46633](https://github.com/microsoft/TypeScript/issues/46633) Inconsistent order of properties inferred from a generic type (open, 2021-11-02, 2 comments)
- [microsoft/TypeScript#61711](https://github.com/microsoft/TypeScript/issues/61711) Resolution order dependent circular heritage (open, 2025-05-16, 0 comments)
- [microsoft/TypeScript#37362](https://github.com/microsoft/TypeScript/issues/37362) Order member intellisense by inheritance (open, 2020-03-12, 3 comments)
- [microsoft/TypeScript#49103](https://github.com/microsoft/TypeScript/issues/49103) Consistently order and differentiate `navto` results (open, 2022-05-13, 1 comments)
- queries: `order in:title repo:typescript-language-server/typescript-language-server is:issue`; `"inlay hint" wrong repo:typescript-language-server/typescript-language-server is:issue`; `"inlay hint" order repo:typescript-language-server/typescript-language-server is:issue`; `"inlay hint" stale repo:typescript-language-server/typescript-language-server is:issue`; `order in:title repo:microsoft/TypeScript is:issue`; `"inlay hint" wrong repo:microsoft/TypeScript is:issue`; `"inlay hint" order repo:microsoft/TypeScript is:issue`; `"inlay hint" stale repo:microsoft/TypeScript is:issue`
