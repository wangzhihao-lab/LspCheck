# [ts7 7.0.2] completion differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-completion-extra-completion-afe533`, signature `ts7|r6_crossimpl|completion:extra`, case family `completion`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/completion` on `test/commands/store-git.test.ts` line 97, column 18 (LSP position {line: 96, character: 17}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "AbortController",
 "AbortSignal",
 "AbstractRange",
 "ActiveXObject",
 "AggregateError",
 "AnalyserNode",
 "Animation",
 "AnimationEffect",
 "AnimationEvent",
 "AnimationPlaybackEvent",
 "AnimationTimeline",
 "Array",
 "ArrayBuffer",
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
 "CSSNumericValue",
 "CSSPageDescriptors",
... (19971 characters)
```

Actual:

```json
[
 "AbortController",
 "AbortSignal",
 "AbstractRange",
 "ActiveXObject",
 "AggregateError",
 "AnalyserNode",
 "Animation",
 "AnimationEffect",
 "AnimationEvent",
 "AnimationPlaybackEvent",
 "AnimationTimeline",
 "Array",
 "ArrayBuffer",
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
 "CSSN
... (20248 characters)
```

Project file `test/commands/store-git.test.ts`:

```
  95 |   function parseJson(result: RunCLIResult): any {
  96 |     try {
  97 |       return JSON.parse(result.stdout);
  98 |     } catch (error) {
  99 |       throw new Error(
 100 |         `Could not parse JSON.\nCommand: ${result.command}\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}\n${String(error)}`
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-completion-extra-completion-afe533/repro.json
```

## Evidence and reduction

- representative 15682bd48ce1-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, react-hook-form/react-hook-form@5fd9ef65290b, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#4587](https://github.com/microsoft/typescript-go/issues/4587) TSX files do not report TypeScript diagnostics, while TS files work correctly (autocomplete still works) (closed, 2026-07-10, 3 comments)
- [microsoft/typescript-go#4532](https://github.com/microsoft/typescript-go/issues/4532) [ServerErrors][TypeScript] main vs  (closed, 2026-07-03, 8 comments)
- [microsoft/typescript-go#3615](https://github.com/microsoft/typescript-go/issues/3615) Server stops responding after `Running scheduled diagnostics refresh` (closed, 2026-04-26, 0 comments)
- [microsoft/typescript-go#2127](https://github.com/microsoft/typescript-go/issues/2127) Panics when extra closing JSX tag (closed, 2025-11-19, 7 comments)
- [microsoft/typescript-go#2778](https://github.com/microsoft/typescript-go/issues/2778) [ServerErrors][TypeScript] linux-x64-7.0.0-dev.20260212.1 vs  (closed, 2026-02-13, 34 comments)
- [microsoft/typescript-go#4677](https://github.com/microsoft/typescript-go/issues/4677) JSDoc (TSDoc ???) is not shown for object literal properties on hover (closed, 2026-07-20, 1 comments)
- [microsoft/typescript-go#4347](https://github.com/microsoft/typescript-go/issues/4347) CPU usage spikes to 80% to 100% when using `tsgo --lsp --stdio` (closed, 2026-06-17, 5 comments)
- [microsoft/typescript-go#3946](https://github.com/microsoft/typescript-go/issues/3946) Auto-import lowercases internal capitals in PascalCase default-import bindings (closed, 2026-05-18, 0 comments)
- queries: `completion extra repo:microsoft/typescript-go is:issue`; `completion "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-trafe533-r6-replay-test-baseline-20260925-162526-813c44] stderr: context canceled
[ts7-7.0.2-trafe533-r6-replay-test-control-20260925-162534-075e90] stderr: context canceled
```
