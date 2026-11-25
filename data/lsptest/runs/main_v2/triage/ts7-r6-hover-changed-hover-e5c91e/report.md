# [ts7 7.0.2] hover differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-hover-changed-hover-e5c91e`, signature `ts7|r6_crossimpl|hover:changed`, case family `hover`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/hover` on `packages/web/test/hydration/spread-innerhtml.spec.tsx` line 15, column 5 (LSP position {line: 14, character: 4}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"(alias) describe<object>(name: string | Function, fn?: SuiteFactory<object> | undefined, options?: number): SuiteCollector<object> (+1 overload)"
```

Actual:

```json
"(alias) const describe: <object>(name: string | Function, fn?: SuiteFactory<object> | undefined, options?: number) => SuiteCollector<object>"
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
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-hover-changed-hover-e5c91e/repro.json
```

## Evidence and reduction

- representative 89ebeb799563-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects solidjs/solid@4b62bc29e04b, umami-software/umami@12ad773d621f, vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 1

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
[ts7-7.0.2-tre5c91e-r6-replay-test-baseline-20261118-223308-c9af78] stderr: context canceled
[ts7-7.0.2-tre5c91e-r6-replay-test-control-20261118-223321-07ee57] stderr: context canceled
```
