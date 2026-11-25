# [ts6 6.0.3] mutation:M1 edit is not valid (diagnostics:extra:2558,2604)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2558-2604-mutation-m1-e220b8`, signature `ts6|r4_edits|diagnostics:extra:2558,2604`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/rendering/shared/src/router.tsx`
3. textDocument/didChange: `change examples/rendering/shared/src/router.tsx (1, 2)-(2, 2) ""`
4. textDocument/didChange: `change examples/rendering/shared/src/router.tsx (7, 0)-(7, 0) "import { createContext } from \"vm\";\n"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `packages/signals/tests/latest-plain-write-purity.test.ts`, `packages/web/test/server/server-functions-decoder-rejection-ownership.spec.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `examples/rendering/shared/src/router.tsx` line 17, column 23 (LSP position {line: 16, character: 22}) (M1:quickfix-errors:Add import from "vm"); compare with the same query in a fresh session on the same content (expected).

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
  "typescript",
  "Cannot find module '@solidjs/web' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2307",
  "typescript",
  "Cannot find module 'solid-js' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "typescript",
  "Property 'url' does not exist on type '{}'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2875",
  "typescript",
  "This JSX tag requires the module path '@solidjs/web/jsx-runtime' to exist, but none could be found. Make sure you have types for the appropriate package installed."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7026",
  "typescript",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ],
 [
  0,
  0,
  0,
  0,
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
  0,
  0,
  0,
  0,
  1,
  "2307",
  "typescript",
  "Cannot find module '@solidjs/web' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2307",
  "typescript",
  "Cannot find module 'solid-js' or its corresponding type declarations."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2339",
  "typescript",
  "Property 'url' does not exist on type '{}'."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2558",
  "typescript",
  "Expected 0 type arguments, but got 1."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2604",
  "typescript",
  "JSX element type 'RouterContext' does not have any construct or call signatures."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "2875",
  "typescript",
  "This JSX tag requires the module path '@solidjs/web/jsx-runtime' to exist, but none could be found. Make sure you have types for the appropriate package installed."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7026",
  "typescript",
  "JSX element implicitly has type 'any' because no interface 'JSX.IntrinsicElements' exists."
 ],
 [
  0,
  0,
  0,
  0,
  1,
  "7026",
  "typescript",
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r4-diagnostics-extra-2558-2604-mutation-m1-e220b8/repro.json
```

## Evidence and reduction

- representative 09497d6d86a9-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 6.649 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects solidjs/solid@4b62bc29e04b, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#1014](https://github.com/typescript-language-server/typescript-language-server/issues/1014) TypeScript Language Server Hangs on Completion Resolution On Enter Key Pressed (closed, 2025-09-24, 21 comments)
- [typescript-language-server/typescript-language-server#917](https://github.com/typescript-language-server/typescript-language-server/issues/917) Shows incorrect type completion item between VSCode and Neovim (closed, 2024-09-27, 9 comments)
- [typescript-language-server/typescript-language-server#815](https://github.com/typescript-language-server/typescript-language-server/issues/815) TSServer >=4.1.0 never publishes textDocument/publishDiagnostics event (NeoVim) (closed, 2023-11-16, 1 comments)
- [typescript-language-server/typescript-language-server#841](https://github.com/typescript-language-server/typescript-language-server/issues/841) Invalid completions (closed, 2024-01-02, 10 comments)
- [typescript-language-server/typescript-language-server#724](https://github.com/typescript-language-server/typescript-language-server/issues/724) "typescript.inlayHints.includeInlayParameterNameHints": "all" breaks inference with dangling commas (closed, 2023-05-15, 7 comments)
- [microsoft/TypeScript#58262](https://github.com/microsoft/TypeScript/issues/58262) Enable `allowJs` with `isolatedDeclarations` (open, 2024-04-19, 6 comments)
- [microsoft/TypeScript#31849](https://github.com/microsoft/TypeScript/issues/31849) Document --incremental and composite project APIs (open, 2019-06-10, 50 comments)
- [microsoft/TypeScript#41860](https://github.com/microsoft/TypeScript/issues/41860) Richer Diagnostic Display Meta-Issue (open, 2020-12-07, 10 comments)
- queries: `diagnostics extra repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics "wrong edit" repo:typescript-language-server/typescript-language-server is:issue`; `diagnostics extra repo:microsoft/TypeScript is:issue`; `diagnostics "wrong edit" repo:microsoft/TypeScript is:issue`
