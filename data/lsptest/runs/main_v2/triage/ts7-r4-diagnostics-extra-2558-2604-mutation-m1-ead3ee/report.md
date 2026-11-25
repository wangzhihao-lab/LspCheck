# [ts7 7.0.2] mutation:M1 edit is not valid (diagnostics:extra:2558,2604)

Draft for the author (not filed). Group `ts7-r4-diagnostics-extra-2558-2604-mutation-m1-ead3ee`, signature `ts7|r4_edits|diagnostics:extra:2558,2604`, case family `mutation:M1`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/rendering/shared/src/router.tsx`
3. textDocument/didChange: `change examples/rendering/shared/src/router.tsx (1, 2)-(2, 2) ""`
4. textDocument/didChange: `change examples/rendering/shared/src/router.tsx (7, 0)-(7, 0) "import { createContext } from \"node:vm\";\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `packages/signals/tests/latest-plain-write-purity.test.ts`, `packages/web/test/server/server-functions-decoder-rejection-ownership.spec.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `examples/rendering/shared/src/router.tsx` line 17, column 23 (LSP position {line: 16, character: 22}) (M1:quickfix-errors:Add import from "node:vm"); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  0,
  0,
  1,
  "2307",
  "ts",
  "Cannot find module '@solidjs/web' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2307",
  "ts",
  "Cannot find module 'solid-js' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "ts",
  "Property 'url' does not exist on type '{}'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2875",
  "ts",
  "This JSX tag requires the module path '@solidjs/web/jsx-runtime' to exist, but none could be found. Make sure you have types for the appropriate package installed."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7026",
  "ts",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7026",
  "ts",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ]
]
```

Actual:

```json
[
 [
  0,
  0,
  0,
  0,
  1,
  "2307",
  "ts",
  "Cannot find module '@solidjs/web' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2307",
  "ts",
  "Cannot find module 'solid-js' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "ts",
  "Property 'url' does not exist on type '{}'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2558",
  "ts",
  "Expected 0 type arguments, but got 1."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2604",
  "ts",
  "JSX element type 'RouterContext' does not have any construct or call signatures."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2875",
  "ts",
  "This JSX tag requires the module path '@solidjs/web/jsx-runtime' to exist, but none could be found. Make sure you have types for the appropriate package installed."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7026",
  "ts",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7026",
  "ts",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ]
]
```

Project file `examples/rendering/shared/src/router.tsx`:

```
   1 | import {
   2 |   createContext,
   3 |   createSignal,
   4 |   useContext,
   5 |   type Component,
   6 |   type ParentProps
   7 | } from "solid-js";
   8 | import { isServer } from "@solidjs/web";
     ...
  10 | type RouterValue = [
  11 |   () => string,
  12 |   {
  13 |     setLocation: (value: string) => void;
  14 |     matches: (match: string) => boolean;
  15 |   }
  16 | ];
     ...
  18 | const RouterContext = createContext<RouterValue>();
     ...
  20 | function RouteHOC(Comp: Component): Component<{ url?: string }> {
  21 |   return (props = {}) => {
  22 |     const initialPath = props.url ?? (isServer ? "/" : window.location.pathname);
  23 |     const [location, setLocation] = createSignal(initialPath.slice(1) || "index");
  24 |     const matches = (match: string) => match === (location() || "index");
     ...
  26 |     if (!isServer) {
  27 |       window.onpopstate = () => setLocation(window.location.pathname.slice(1) || "index");
  28 |     }
     ...
  30 |     return (
  31 |       <RouterContext value={[location, { setLocation, matches }]}>
  32 |         <Comp />
  33 |       </RouterContext>
  34 |     );
  35 |   };
  36 | }
     ...
  38 | function useRouter() {
  39 |   const router = useContext(RouterContext);
  40 |   if (!router) {
  41 |     throw new Error("RouterContext is not available");
  42 |   }
  43 |   return router;
  44 | }
     ...
  46 | function Link(props: ParentProps<{ path: string }>) {
  47 |   const [, { setLocation }] = useRouter();
     ...
  49 |   function navigate(event: MouseEvent) {
  50 |     event.preventDefault();
  51 |     window.history.pushState("", "", `/${props.path}`);
  52 |     setLocation(props.path);
  53 |   }
     ...
  55 |   return (
  56 |     <a class="link" href={`/${props.path}`} onClick={navigate}>
  57 |       {props.children}
  58 |     </a>
  59 |   );
  60 | }
     ...
  62 | export { Link, RouteHOC, RouterContext, useRouter };
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r4-diagnostics-extra-2558-2604-mutation-m1-ead3ee/repro.json
```

## Evidence and reduction

- representative d2aec7890861-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 11.191 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects solidjs/solid@4b62bc29e04b, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4435](https://github.com/microsoft/typescript-go/issues/4435) Different diagnostics and exit code vs tsc for tsconfig using extends + baseUrl + wildcard paths (closed, 2026-06-24, 1 comments)
- [microsoft/typescript-go#3508](https://github.com/microsoft/typescript-go/issues/3508) Corsa no longer emits the TS-1 internal diagnostic about pre-emit/post-emit diagnostic count mismatches (closed, 2026-04-22, 2 comments)
- [microsoft/typescript-go#3615](https://github.com/microsoft/typescript-go/issues/3615) Server stops responding after `Running scheduled diagnostics refresh` (closed, 2026-04-26, 0 comments)
- [microsoft/typescript-go#4314](https://github.com/microsoft/typescript-go/issues/4314) Behavior difference: tsgo misses TS2345 when a namespace translator union is called with a template-literal key union (closed, 2026-06-15, 2 comments)
- [microsoft/typescript-go#1520](https://github.com/microsoft/typescript-go/issues/1520) --incremental builds are a bit slower after the 20250805 release (closed, 2025-08-05, 5 comments)
- queries: `diagnostics extra repo:microsoft/typescript-go is:issue`; `diagnostics "wrong edit" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tread3ee-r4-replay-baseline-20261118-220647-ac19a3] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tread3ee-r4-replay-baseline-20261118-220647-ac19a3] stderr: context canceled
[ts7-7.0.2-tread3ee-r4-replay-case-20261118-220628-fdebb7] stderr: context canceled
[ts7-7.0.2-tread3ee-r4-replay-control-20261118-220706-7e43cf] stderr: context canceled
```
