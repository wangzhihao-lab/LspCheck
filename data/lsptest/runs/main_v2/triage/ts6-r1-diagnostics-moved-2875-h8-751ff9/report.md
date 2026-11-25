# [ts6 6.0.3] diagnostics moves 2875 after query order

Draft for the author (not filed). Group `ts6-r1-diagnostics-moved-2875-h8-751ff9`, signature `ts6|r1_history|diagnostics:moved:2875`, case family `H8`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open packages/web/test/hydration/spread-innerhtml.spec.tsx`
3. request: `request packages/web/test/hydration/spread-innerhtml.spec.tsx typeDefinition at (28, 13)`
4. request: `request packages/web/test/hydration/spread-innerhtml.spec.tsx completion at (43, 90)`
5. Timing: send the steps 0 ms apart without waiting, then wait until idle.
6. textDocument/didOpen `examples/rendering/shared/src/components/Reveal.tsx`, `packages/web/test/latest-shadow-owned-write-issue-3378.spec.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
7. Query `textDocument/diagnostic` on `packages/web/test/hydration/spread-innerhtml.spec.tsx` for the whole file; compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  5,
  65,
  5,
  75,
  1,
  "2307",
  "typescript",
  "Cannot find module 'solid-js' or its corresponding type declarations."
 ],
 [
  6,
  24,
  6,
  38,
  1,
  "2307",
  "typescript",
  "Cannot find module '@solidjs/web' or its corresponding type declarations."
 ],
 [
  43,
  13,
  43,
  87,
  1,
  "7026",
  "typescript",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ],
 [
  43,
  13,
  43,
  93,
  1,
  "2875",
  "typescript",
  "This JSX tag requires the module path '@solidjs/web/jsx-runtime' to exist, but none could be found. Make sure you have types for the appropriate package installed."
 ],
 [
  43,
  87,
  43,
  93,
  1,
  "7026",
  "typescript",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ]
]
```

Actual:

```json
[
 [
  5,
  65,
  5,
  75,
  1,
  "2307",
  "typescript",
  "Cannot find module 'solid-js' or its corresponding type declarations."
 ],
 [
  6,
  24,
  6,
  38,
  1,
  "2307",
  "typescript",
  "Cannot find module '@solidjs/web' or its corresponding type declarations."
 ],
 [
  43,
  13,
  43,
  87,
  1,
  "2875",
  "typescript",
  "This JSX tag requires the module path '@solidjs/web/jsx-runtime' to exist, but none could be found. Make sure you have types for the appropriate package installed."
 ],
 [
  43,
  13,
  43,
  87,
  1,
  "7026",
  "typescript",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ],
 [
  43,
  87,
  43,
  93,
  1,
  "7026",
  "typescript",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ]
]
```

Project file `packages/web/test/hydration/spread-innerhtml.spec.tsx`:

```
   1 | /**
   2 |  * @jsxImportSource @solidjs/web
   3 |  * @vitest-environment jsdom
   4 |  */
   5 | import { describe, expect, test, beforeEach, afterEach } from "vitest";
   6 | import { createSignal, createMemo, flush, enableHydration } from "solid-js";
   7 | import { hydrate } from "@solidjs/web";
     ...
   9 | enableHydration();
     ...
  11 | function setupHydration() {
  12 |   (globalThis as any)._$HY = { events: [], completed: new WeakSet(), r: {} };
  13 | }
     ...
  15 | describe("#2737: spread + innerHTML across hydration", () => {
  16 |   const container = document.createElement("div");
  17 |   document.body.appendChild(container);
  18 |   let dispose: (() => void) | undefined;
     ...
  20 |   beforeEach(async () => {
  21 |     if (dispose) dispose();
  22 |     await new Promise(r => setTimeout(r, 0));
  23 |     setupHydration();
  24 |     container.innerHTML = "";
  25 |   });
     ...
  27 |   afterEach(() => {
  28 |     if (dispose) {
  29 |       dispose();
  30 |       dispose = undefined;
  31 |     }
  32 |   });
     ...
  34 |   test("reactive spread update after hydration keeps innerHTML content", async () => {
  35 |     // Exact server output for the repro shape (captured from renderToString)
  36 |     container.innerHTML =
  37 |       '<div _hk=1 data-whatever="no" class="flex" style="color: red" >Hello world!</div>';
     ...
  39 |     let setCount!: (v: number) => void;
  40 |     dispose = hydrate(() => {
  41 |       const [count, _setCount] = createSignal(0);
  42 |       setCount = _setCount;
  43 |       const data = createMemo(() => ({ "data-whatever": count() === 1 ? "yes" : "no" }));
  44 |       return <div {...data()} class="flex" style="color: red" innerHTML="Hello world!"></div>;
  45 |     }, container);
     ...
  47 |     await new Promise(r => setTimeout(r, 50));
  48 |     const div = container.querySelector("div")!;
  49 |     expect(div.textContent).toBe("Hello world!");
  50 |     expect(div.getAttribute("data-whatever")).toBe("no");
     ...
  52 |     setCount(1);
  53 |     flush();
  54 |     await new Promise(r => setTimeout(r, 50));
     ...
  56 |     expect(div.getAttribute("data-whatever")).toBe("yes");
  57 |     expect(div.getAttribute("class")).toBe("flex");
  58 |     // The 1.x bug: content cleared on first reactive spread update post-hydration
  59 |     expect(div.textContent).toBe("Hello world!");
  60 |   });
  61 | });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing race0; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-diagnostics-moved-2875-h8-751ff9/repro.json
```

## Evidence and reduction

- representative 170b9b1e53a4-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 10 -> 3 (19 probes, 171.204 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects solidjs/solid@4b62bc29e04b, timings race0, race200, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#803](https://github.com/typescript-language-server/typescript-language-server/issues/803) Server error "Could not find source file" on opening second file in a project with large amount of code (closed, 2023-11-14, 4 comments)
- [typescript-language-server/typescript-language-server#655](https://github.com/typescript-language-server/typescript-language-server/issues/655) Code actions not working (closed, 2023-01-05, 7 comments)
- [typescript-language-server/typescript-language-server#191](https://github.com/typescript-language-server/typescript-language-server/issues/191) doRequestDiagnostics of LspServer looks did not handle err? no 'catch'? (closed, 2021-03-11, 61 comments)
- [typescript-language-server/typescript-language-server#35](https://github.com/typescript-language-server/typescript-language-server/issues/35) Clear diagnostics when closing file (closed, 2018-04-18, 0 comments)
- [microsoft/TypeScript#63758](https://github.com/microsoft/TypeScript/issues/63758) Investigate decorator initialization order re: renames of classes (open, 2026-08-18, 0 comments)
- [microsoft/TypeScript#46633](https://github.com/microsoft/TypeScript/issues/46633) Inconsistent order of properties inferred from a generic type (open, 2021-11-02, 2 comments)
- [microsoft/TypeScript#61711](https://github.com/microsoft/TypeScript/issues/61711) Resolution order dependent circular heritage (open, 2025-05-16, 0 comments)
- [microsoft/TypeScript#37362](https://github.com/microsoft/TypeScript/issues/37362) Order member intellisense by inheritance (open, 2020-03-12, 3 comments)
- queries: `order in:title repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics "wrong range" repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics order repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics stale repo:typescript-language-server/typescript-language-server is:issue`; `order in:title repo:microsoft/TypeScript is:issue`; `diagnostics "wrong range" repo:microsoft/TypeScript is:issue`; `diagnostics order repo:microsoft/TypeScript is:issue`; `diagnostics stale repo:microsoft/TypeScript is:issue`
