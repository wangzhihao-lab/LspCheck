# [ts7 7.0.2] completion differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-completion-missing-completion-60ede6`, signature `ts7|r6_crossimpl|completion:missing`, case family `completion`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `solidjs/solid@4b62bc29e04b` (corpus, commit 4b62bc29e04bfd29573a20ff3d47ae56a8a80ccb), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/completion` on `examples/rendering/shared/src/components/Reveal.tsx` line 60, column 19 (LSP position {line: 59, character: 18}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "AbortController",
 "AbortSignal",
 "AbstractRange",
 "AggregateError",
 "AnalyserNode",
 "Animation",
 "AnimationEffect",
 "AnimationEvent",
 "AnimationPlaybackEvent",
 "AnimationTimeline",
 "Array",
 "ArrayBuffer",
 "AsyncCard",
 "AsyncDisposableStack",
 "Atomics",
 "Attr",
 "Audio",
 "AudioBuffer",
 "AudioBufferSourceNode",
 "AudioContext",
 "AudioData",
 "AudioDecoder",
 "AudioDestinationNode",
 "AudioEncoder",
 "AudioListener",
 "AudioNode",
 "AudioParam",
 "AudioParamMap",
 "AudioProcessingEvent",
 "AudioScheduledSourceNode",
 "AudioWorklet",
 "AudioWorkletNode",
 "AuthenticatorAssertionResponse",
 "AuthenticatorAttestationResponse",
 "AuthenticatorResponse",
 "BarProp",
 "BaseAudioContext",
 "BeforeUnloadEvent",
 "BigInt",
 "BigInt64Array",
 "BigUint64Array",
 "BiquadFilterNode",
 "Blob",
 "BlobEvent",
 "Boolean",
 "BroadcastChannel",
 "Buffer",
 "ByteLengthQueuingStrategy",
 "CDATASection",
 "CSS",
 "CSSAnimation",
 "CSSConditionRule",
 "CSSContainerRule",
 "CSSCounterStyleRule",
 "CSSFontFaceRule",
 "CSSFontFeatureValuesRule",
 "CSSFontPaletteValuesRule",
 "CSSGroupingRule",
 "CSSImageValue",
 "CSSImportRule",
 "CSSKeyframeRule",
 "CSSKeyframesRule",
 "CSSKeywordValue",
 "CSSLayerBlockRule",
 "CSSLayerStatementRule",
 "CSSMathClamp",
 "CSSMathInvert",
 "CSSMathMax",
 "CSSMathMin",
 "CSSMathNegate",
 "CSSMathProduct",
 "CSSMathSum",
 "CSSMathValue",
 "CSSMatrixComponent",
 "CSSMediaRule",
 "CSSNamespaceRule",
 "CSSNestedDeclarations",
 "CSSNumericArray",
 "CSSNumer
... (19291 characters)
```

Actual:

```json
[
 "AbortController",
 "AbortSignal",
 "AbstractRange",
 "AggregateError",
 "AnalyserNode",
 "Animation",
 "AnimationEffect",
 "AnimationEvent",
 "AnimationPlaybackEvent",
 "AnimationTimeline",
 "Array",
 "ArrayBuffer",
 "AsyncCard",
 "AsyncDisposableStack",
 "Atomics",
 "Attr",
 "Audio",
 "AudioBuffer",
 "AudioBufferSourceNode",
 "AudioContext",
 "AudioData",
 "AudioDecoder",
 "AudioDestinationNode",
 "AudioEncoder",
 "AudioListener",
 "AudioNode",
 "AudioParam",
 "AudioParamMap",
 "AudioProcessingEvent",
 "AudioScheduledSourceNode",
 "AudioWorklet",
 "AudioWorkletNode",
 "AuthenticatorAssertionResponse",
 "AuthenticatorAttestationResponse",
 "AuthenticatorResponse",
 "BarProp",
 "BaseAudioContext",
 "BeforeUnloadEvent",
 "BigInt",
 "BigInt64Array",
 "BigUint64Array",
 "BiquadFilterNode",
 "Blob",
 "BlobEvent",
 "Boolean",
 "BroadcastChannel",
 "Buffer",
 "ByteLengthQueuingStrategy",
 "CDATASection",
 "CSS",
 "CSSAnimation",
 "CSSConditionRule",
 "CSSContainerRule",
 "CSSCounterStyleRule",
 "CSSFontFaceRule",
 "CSSFontFeatureValuesRule",
 "CSSFontPaletteValuesRule",
 "CSSGroupingRule",
 "CSSImageValue",
 "CSSImportRule",
 "CSSKeyframeRule",
 "CSSKeyframesRule",
 "CSSKeywordValue",
 "CSSLayerBlockRule",
 "CSSLayerStatementRule",
 "CSSMathClamp",
 "CSSMathInvert",
 "CSSMathMax",
 "CSSMathMin",
 "CSSMathNegate",
 "CSSMathProduct",
 "CSSMathSum",
 "CSSMathValue",
 "CSSMatrixComponent",
 "CSSMediaRule",
 "CSSNamespaceRule",
 "CSSNestedDeclarations",
 "CSSNumericArray",
 "CSSNumer
... (19265 characters)
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-completion-missing-completion-60ede6/repro.json
```

## Evidence and reduction

- representative 89ebeb799563-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects solidjs/solid@4b62bc29e04b, umami-software/umami@12ad773d621f, vadimdemedes/ink@02ae1e59e7c2, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#2985](https://github.com/microsoft/typescript-go/issues/2985) panic: "project bucket missing" in completions (closed, 2026-03-05, 0 comments)
- [microsoft/typescript-go#4005](https://github.com/microsoft/typescript-go/issues/4005) Native Preview returns no code actions for any TS diagnostic (closed, 2026-05-20, 5 comments)
- [microsoft/typescript-go#2384](https://github.com/microsoft/typescript-go/issues/2384) slow Code Completion with use valibot schema define (closed, 2025-12-15, 4 comments)
- [microsoft/typescript-go#2383](https://github.com/microsoft/typescript-go/issues/2383) LSP: Path suggestion missing (import/export) (closed, 2025-12-15, 5 comments)
- [microsoft/typescript-go#4677](https://github.com/microsoft/typescript-go/issues/4677) JSDoc (TSDoc ???) is not shown for object literal properties on hover (closed, 2026-07-20, 1 comments)
- [microsoft/typescript-go#4347](https://github.com/microsoft/typescript-go/issues/4347) CPU usage spikes to 80% to 100% when using `tsgo --lsp --stdio` (closed, 2026-06-17, 5 comments)
- [microsoft/typescript-go#3946](https://github.com/microsoft/typescript-go/issues/3946) Auto-import lowercases internal capitals in PascalCase default-import bindings (closed, 2026-05-18, 0 comments)
- queries: `completion missing repo:microsoft/typescript-go is:issue`; `completion "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr60ede6-r6-replay-test-baseline-20261118-221635-b6895f] stderr: context canceled
[ts7-7.0.2-tr60ede6-r6-replay-test-control-20261118-221645-e9e1b7] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr60ede6-r6-replay-test-control-20261118-221645-e9e1b7] stderr: context canceled
```
