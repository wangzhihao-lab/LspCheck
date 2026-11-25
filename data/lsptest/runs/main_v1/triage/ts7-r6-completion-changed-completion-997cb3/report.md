# [ts7 7.0.2] completion differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-completion-changed-completion-997cb3`, signature `ts7|r6_crossimpl|completion:changed`, case family `completion`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `Fission-AI/OpenSpec@f179ed4e4056` (corpus, commit f179ed4e40567cdb56501ee3f4d09efbcb1557b8), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/completion` on `test/commands/store-git.test.ts` line 209, column 63 (LSP position {line: 208, character: 62}); compare with the reference implementation's answer (expected).

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
... (20031 characters)
```

Actual:

```json
[
 "mode?",
 "recursive"
]
```

Project file `test/commands/store-git.test.ts`:

```
 206 |       XDG_DATA_HOME: path.join(tempDir, 'empty-teammate-data'),
 207 |       XDG_CONFIG_HOME: path.join(tempDir, 'empty-teammate-config'),
 208 |     };
 209 |     fs.mkdirSync(path.join(storeRoot, 'openspec'), { recursive: true });
 210 |     fs.writeFileSync(path.join(storeRoot, 'openspec', 'config.yaml'), 'schema: spec-driven\n');
 211 |     await writeStoreMetadataState(storeRoot, { version: 1, id: 'empty-team-context' });
 212 |     execFileSync('git', ['init'], { cwd: storeRoot, stdio: 'ignore' });
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-completion-changed-completion-997cb3/repro.json
```

## Evidence and reduction

- representative 15682bd48ce1-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Fission-AI/OpenSpec@f179ed4e4056, chenglou/pretext@2e5e2bdaee39, upstash/context7@6477e43e31d2, timings settled, seeds 1

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
[ts7-7.0.2-tr997cb3-r6-replay-test-baseline-20260925-162149-195287] stderr: context canceled
[ts7-7.0.2-tr997cb3-r6-replay-test-control-20260925-162208-f87b44] stderr: context canceled
```
