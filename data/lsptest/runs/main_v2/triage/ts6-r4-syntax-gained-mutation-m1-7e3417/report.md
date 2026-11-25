# [ts6 6.0.3] mutation:M1 edit is not valid (syntax:gained)

Draft for the author (not filed). Group `ts6-r4-syntax-gained-mutation-m1-7e3417`, signature `ts6|r4_edits|syntax:gained`, case family `mutation:M1`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open examples/rendering/shared/src/components/Reveal.tsx`
3. textDocument/didChange: `change examples/rendering/shared/src/components/Reveal.tsx (0, 44)-(0, 52) ""`
4. textDocument/didChange: `change examples/rendering/shared/src/components/Reveal.tsx (97, 9)-(97, 13) "ev"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `packages/web/test/hydration/spread-innerhtml.spec.tsx`, `packages/web/test/latest-shadow-owned-write-issue-3378.spec.tsx` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `syntax` on `examples/rendering/shared/src/components/Reveal.tsx` line 98, column 10 (LSP position {line: 97, character: 9}) (M1:quickfix-syntax:Change spelling to 'eval'); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "TS17002 Expected corresponding JSX closing tag for 'eval'."
]
```

Project file `examples/rendering/shared/src/components/Reveal.tsx`:

```
   1 | import { createMemo, createSignal, Loading, Reveal, Show, type RevealOrder } from "solid-js";
     ...
   3 | function delayedValue<T>(ms: number, value: T): Promise<T> {
   4 |   return new Promise(resolve => setTimeout(() => resolve(value), ms));
   5 | }
     ...
   7 | function AsyncCard(props: { delay: number; title: string }) {
   8 |   const value = createMemo(() =>
   9 |     delayedValue(props.delay, `${props.title} resolved in ${props.delay}ms`)
  10 |   );
     ...
  12 |   return (
  13 |     <Loading fallback={<div class="loader">{props.title} loading...</div>}>
  14 |       <div class="reveal-card">
  15 |         <strong>{props.title}</strong>
  16 |         <div>{value()}</div>
  17 |       </div>
  18 |     </Loading>
  19 |   );
  20 | }
     ...
  22 | const RevealPage = () => {
  23 |   const [order, setOrder] = createSignal<RevealOrder>("sequential");
  24 |   const [collapsed, setCollapsed] = createSignal(true);
  25 |   const [seed, setSeed] = createSignal(1);
     ...
  27 |   return (
  28 |     <>
  29 |       <h1>Reveal</h1>
  30 |       <p>
  31 |         Compare reveal ordering with different <code>order</code> modes and watch the nested group
  32 |         behave as a single composite slot inside its parent. Restart the run to replay SSR and
  33 |         hydration timings.
  34 |       </p>
  35 |       <p>
  36 |         <strong>Run:</strong> {seed()}
  37 |       </p>
  38 |       <div
  39 |         style={{
  40 |           display: "flex",
  41 |           gap: "1rem",
  42 |           "align-items": "center",
  43 |           "margin-bottom": "1rem",
  44 |           "flex-wrap": "wrap"
  45 |         }}
  46 |       >
  47 |         <fieldset style={{ display: "flex", gap: "0.75rem", "align-items": "center" }}>
  48 |           <legend>order</legend>
  49 |           <label>
  50 |             <input
  51 |               type="radio"
  52 |               name="order"
  53 |               value="sequential"
  54 |               checked={order() === "sequential"}
  55 |               onInput={() => setOrder("sequential")}
  56 |             />{" "}
  57 |             sequential
  58 |           </label>
  59 |           <label>
  60 |             <input
  61 |               type="radio"
  62 |               name="order"
  63 |               value="together"
  64 |               checked={order() === "together"}
  65 |               onInput={() => setOrder("together")}
  66 |             />{" "}
  67 |             together
  68 |           </label>
  69 |           <label>
  70 |             <input
  71 |               type="radio"
  72 |               name="order"
  73 |               value="natural"
  74 |               checked={order() === "natural"}
  75 |               onInput={() => setOrder("natural")}
  76 |             />{" "}
  77 |             natural
  78 |           </label>
  79 |         </fieldset>
  80 |         <label title="Only applies when order is sequential">
  81 |           <input
  82 |             type="checkbox"
  83 |             checked={collapsed()}
  84 |             disabled={order() !== "sequential"}
  85 |             onInput={e => setCollapsed(e.currentTarget.checked)}
  86 |           />{" "}
  87 |           collapsed <em>(sequential only)</em>
  88 |         </label>
  89 |         <button onClick={() => setSeed(s => s + 1)}>Restart run</button>
  90 |       </div>
     ...
  92 |       <Show when={seed()} keyed>
  93 |         <h2>Primary Group</h2>
  94 |         <p>
  95 |           Three siblings under a single <code>{`<Reveal order="${order()}">`}</code>. Compare how
  96 |           they swap in as each resolves.
  97 |         </p>
  98 |         <Reveal order={order()} collapsed={collapsed()}>
  99 |           <div class="reveal-grid">
 100 |             <AsyncCard title="A" delay={500} />
 101 |             <AsyncCard title="B" delay={1100} />
 102 |             <AsyncCard title="C" delay={1700} />
 103 |           </div>
 104 |         </Reveal>
     ...
 106 |         <h2>Nested Group</h2>
 107 |         <p>
 108 |           The outer group uses <code>order="{order()}"</code>. The inner group is always{" "}
 109 |           <code>order="natural"</code> — it registers as a single composite slot to the outer group
 110 |           and, once the outer releases it, each inner card reveals on its own.
 111 |         </p>
 112 |         <Reveal order={order()} collapsed={collapsed()}>
 113 |           <div class="reveal-grid">
 114 |             <AsyncCard title="Outer-1" delay={700} />
 115 |             <Reveal order="natural">
 116 |               <div class="reveal-grid">
 117 |                 <AsyncCard title="Inner-1" delay={900} />
 118 |                 <AsyncCard title="Inner-2" delay={1300} />
 119 |               </div>
 120 |             </Reveal>
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r4-syntax-gained-mutation-m1-7e3417/repro.json
```

## Evidence and reduction

- representative fa21096f3d2f-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 6.757 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects solidjs/solid@4b62bc29e04b, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#921](https://github.com/typescript-language-server/typescript-language-server/issues/921) Fails to load with syntax error in Kate on KDE Neon (closed, 2024-10-02, 18 comments)
- [typescript-language-server/typescript-language-server#700](https://github.com/typescript-language-server/typescript-language-server/issues/700) Dont find syntax error (closed, 2023-03-09, 1 comments)
- [typescript-language-server/typescript-language-server#243](https://github.com/typescript-language-server/typescript-language-server/issues/243) language server crashes on a syntax error in globby (closed, 2021-08-05, 1 comments)
- [microsoft/TypeScript#48441](https://github.com/microsoft/TypeScript/issues/48441) Please add default values to all properties in configuration reference (open, 2022-03-26, 2 comments)
- [microsoft/TypeScript#54602](https://github.com/microsoft/TypeScript/issues/54602) Unexpected ASI after `declare` (regression since version 4.4) (open, 2023-06-10, 1 comments)
- [microsoft/TypeScript#61426](https://github.com/microsoft/TypeScript/issues/61426) Intellisense: deprioritise native function methods (open, 2025-03-15, 2 comments)
- [microsoft/TypeScript#40317](https://github.com/microsoft/TypeScript/issues/40317) Tolerate invalid identifier syntax errors in list parsing (open, 2020-08-29, 6 comments)
- [microsoft/TypeScript#63005](https://github.com/microsoft/TypeScript/issues/63005) Crash： when inferring from a tuple with middle rest elements and trailing variadic elements (open, 2026-01-17, 1 comments)
- queries: `syntax unexpected repo:typescript-language-server/typescript-language-server is:issue`; `syntax "wrong edit" repo:typescript-language-server/typescript-language-server is:issue`; `syntax unexpected repo:microsoft/TypeScript is:issue`; `syntax "wrong edit" repo:microsoft/TypeScript is:issue`
