# [ts6 6.0.3] mutation:M3 edit is not valid (diagnostics:extra:2554)

Draft for the author (not filed). Group `ts6-r4-diagnostics-extra-2554-mutation-m3-d2ab31`, signature `ts6|r4_edits|diagnostics:extra:2554`, case family `mutation:M3`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `DayuanJiang/next-ai-draw-io@58b73ef761d8` (corpus, commit 58b73ef761d8a5e5b2afa2c360428d3dea996312), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open components/code-block.tsx`
3. textDocument/didChange: `change components/code-block.tsx (33, 36)-(46, 25) ""`
4. textDocument/didChange: `change components/code-block.tsx (17, 23)-(18, 23) ""`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `components/ui/command.tsx`, `packages/mcp-server/src/pages.ts` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `components/code-block.tsx` line 18, column 21 (LSP position {line: 17, character: 20}) (M3:quickfix-errors:Remove unused declaration for: 'getLineProps'); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
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
  "2554",
  "typescript",
  "Expected 1-2 arguments, but got 0."
 ]
]
```

Project file `components/code-block.tsx`:

```
   1 | "use client"
     ...
   3 | import { Highlight, themes } from "prism-react-renderer"
     ...
   5 | interface CodeBlockProps {
   6 |     code: string
   7 |     language?: "xml" | "json"
   8 | }
     ...
  10 | export function CodeBlock({ code, language = "xml" }: CodeBlockProps) {
  11 |     return (
  12 |         <div className="overflow-hidden w-full">
  13 |             <Highlight theme={themes.github} code={code} language={language}>
  14 |                 {({
  15 |                     className: _className,
  16 |                     style,
  17 |                     tokens,
  18 |                     getLineProps,
  19 |                     getTokenProps,
  20 |                 }) => (
  21 |                     <pre
  22 |                         className="text-[11px] leading-relaxed overflow-x-auto overflow-y-auto max-h-48 scrollbar-thin break-all"
  23 |                         style={{
  24 |                             ...style,
  25 |                             fontFamily:
  26 |                                 "var(--font-mono), ui-monospace, monospace",
  27 |                             backgroundColor: "transparent",
  28 |                             margin: 0,
  29 |                             padding: 0,
  30 |                             wordBreak: "break-all",
  31 |                             whiteSpace: "pre-wrap",
  32 |                         }}
  33 |                     >
  34 |                         {tokens.map((line, i) => (
  35 |                             <div
  36 |                                 key={i}
  37 |                                 {...getLineProps({ line })}
  38 |                                 style={{ wordBreak: "break-all" }}
  39 |                             >
  40 |                                 {line.map((token, key) => (
  41 |                                     <span
  42 |                                         key={key}
  43 |                                         {...getTokenProps({ token })}
  44 |                                     />
  45 |                                 ))}
  46 |                             </div>
  47 |                         ))}
  48 |                     </pre>
  49 |                 )}
  50 |             </Highlight>
  51 |         </div>
  52 |     )
  53 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r4-diagnostics-extra-2554-mutation-m3-d2ab31/repro.json
```

## Evidence and reduction

- representative 3db536a7b58d-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 14.027 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects DayuanJiang/next-ai-draw-io@58b73ef761d8, timings settled, seeds 2

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
