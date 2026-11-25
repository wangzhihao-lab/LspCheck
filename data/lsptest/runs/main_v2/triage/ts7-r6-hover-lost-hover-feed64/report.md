# [ts7 7.0.2] hover differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-hover-lost-hover-feed64`, signature `ts7|r6_crossimpl|hover:lost`, case family `hover`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/hover` on `examples/rendering/shared/src/router.tsx` line 4, column 8 (LSP position {line: 3, character: 7}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"import useContext"
```

Actual:

```json
null
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-hover-lost-hover-feed64/repro.json
```

## Evidence and reduction

- representative 4224a39ee10c-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Gitlawb/openclaude@5cd11336caea, solidjs/solid@4b62bc29e04b, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#3605](https://github.com/microsoft/typescript-go/issues/3605) Missing generic param displayed in hover (closed, 2026-04-25, 0 comments)
- [microsoft/typescript-go#3411](https://github.com/microsoft/typescript-go/issues/3411) Missing generic type description in hover (closed, 2026-04-15, 2 comments)
- [microsoft/typescript-go#3607](https://github.com/microsoft/typescript-go/issues/3607) Missing hover for nullable method in type and interface (closed, 2026-04-25, 1 comments)
- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#3422](https://github.com/microsoft/typescript-go/issues/3422) Wrong function signature and missing invoking description in hover (closed, 2026-04-16, 0 comments)
- [microsoft/typescript-go#4677](https://github.com/microsoft/typescript-go/issues/4677) JSDoc (TSDoc ???) is not shown for object literal properties on hover (closed, 2026-07-20, 1 comments)
- [microsoft/typescript-go#4758](https://github.com/microsoft/typescript-go/issues/4758) disableSourceOfProjectReferenceRedirect causes lodash per-method submodule import to resolve to the wrong function (closed, 2026-07-27, 7 comments)
- [microsoft/typescript-go#4683](https://github.com/microsoft/typescript-go/issues/4683) Generic type parameter inferred differently across two call-site positions with opposite variance (narrow type vs union) (closed, 2026-07-20, 2 comments)
- queries: `hover missing repo:microsoft/typescript-go is:issue`; `hover "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trfeed64-r6-replay-test-baseline-20261118-223556-cf8668] stderr: context canceled
[ts7-7.0.2-trfeed64-r6-replay-test-control-20261118-223604-079129] stderr: context canceled
```
