# [ts7 7.0.2] completion differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-completion-changed-completion-997cb3`, signature `ts7|r6_crossimpl|completion:changed`, case family `completion`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Gitlawb/openclaude@5cd11336caea` (corpus, commit 5cd11336caeaf2023ca1e02e5975c761cfc585fe), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/completion` on `src/components/PromptInput/Notifications.tsx` line 102, column 23 (LSP position {line: 101, character: 22}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "$",
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
 "AutoUpdaterWrapper",
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
 "Box",
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
 "CSSNu
... (21035 characters)
```

Actual:

```json
[
 "$",
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
 "AutoUpdaterWrapper",
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
 "Box",
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
 "CSSNu
... (21056 characters)
```

Project file `src/components/PromptInput/Notifications.tsx`:

```
  99 |   const {
 100 |     addNotification,
 101 |     removeNotification
 102 |   } = useNotifications();
 103 |   const claudeAiLimits = useClaudeAiLimits();
 104 |   let t5;
 105 |   let t6;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts7-r6-completion-changed-completion-997cb3/repro.json
```

## Evidence and reduction

- representative 8bf86710b7ff-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Gitlawb/openclaude@5cd11336caea, hexojs/hexo@751e856691bf, umami-software/umami@12ad773d621f, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/typescript-go#2598](https://github.com/microsoft/typescript-go/issues/2598) Auto-imports broken in JS files when user preferences are used (closed, 2026-01-28, 16 comments)
- [microsoft/typescript-go#3026](https://github.com/microsoft/typescript-go/issues/3026) TypeScript Native Preview VS Code extension status bar color is confusing (closed, 2026-03-09, 3 comments)
- [microsoft/typescript-go#1873](https://github.com/microsoft/typescript-go/issues/1873) Crash in auto-import completions (closed, 2025-10-11, 6 comments)
- [microsoft/typescript-go#1425](https://github.com/microsoft/typescript-go/issues/1425) Invalid `textEdit` range in `completionItem/resolve` response (closed, 2025-07-21, 1 comments)
- [microsoft/typescript-go#4677](https://github.com/microsoft/typescript-go/issues/4677) JSDoc (TSDoc ???) is not shown for object literal properties on hover (closed, 2026-07-20, 1 comments)
- [microsoft/typescript-go#4347](https://github.com/microsoft/typescript-go/issues/4347) CPU usage spikes to 80% to 100% when using `tsgo --lsp --stdio` (closed, 2026-06-17, 5 comments)
- [microsoft/typescript-go#3946](https://github.com/microsoft/typescript-go/issues/3946) Auto-import lowercases internal capitals in PascalCase default-import bindings (closed, 2026-05-18, 0 comments)
- [microsoft/typescript-go#2555](https://github.com/microsoft/typescript-go/issues/2555) Installing Native Preview broke TS Imports (closed, 2026-01-21, 8 comments)
- queries: `completion wrong repo:microsoft/typescript-go is:issue`; `completion "TypeScript 6" repo:microsoft/typescript-go is:issue`

## Server log excerpt (last confirming replay)

```
[ts7-7.0.2-tr997cb3-r6-replay-test-baseline-20261118-221256-92dafe] stderr: context canceled
[ts7-7.0.2-tr997cb3-r6-replay-test-control-20261118-221310-81ba69] window/logMessage type 1: error handling method 'exit': EOF
[ts7-7.0.2-tr997cb3-r6-replay-test-control-20261118-221310-81ba69] stderr: context canceled
```
