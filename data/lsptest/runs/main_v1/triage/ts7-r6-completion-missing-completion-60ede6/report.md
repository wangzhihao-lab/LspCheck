# [ts7 7.0.2] completion differs from TypeScript 6

Draft for the author (not filed). Group `ts7-r6-completion-missing-completion-60ede6`, signature `ts7|r6_crossimpl|completion:missing`, case family `completion`.

## Server

- ts7 7.0.2; launch `temp/lsp_servers/ts7-7.0.2/node_modules/@typescript/typescript-darwin-arm64/lib/tsc --lsp --stdio`; entry sha256 a82f731365ad69d5; package version 7.0.2
- project `react-hook-form/react-hook-form@5fd9ef65290b` (corpus, commit 5fd9ef65290bef2ccaa7ac96dc8d5d55478b5410), language typescript

## Relation violated

Cross-implementation agreement (R6): TypeScript 7 (tsc --lsp) and TypeScript 6 (typescript-language-server) answer the same query on the same project; the difference is not among the documented intended differences.

## Minimal steps (LSP)

1. Start ts7 7.0.2 on the project root; answer workspace/configuration with the settings under Environment.
2. Fresh sessions of ts7 7.0.2 and of the reference ts6 6.0.3 on the same project, the same query in both.
3. Query `textDocument/completion` on `src/logic/skipValidation.ts` line 7, column 23 (LSP position {line: 6, character: 22}); compare with the reference implementation's answer (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "ANGLE_instanced_arrays",
 "ARIAMixin",
 "AacBitstreamFormat",
 "AacEncoderConfig",
 "AbortController",
 "AbortSignal",
 "AbortSignalEventMap",
 "AbstractRange",
 "AbstractWorker",
 "AbstractWorkerEventMap",
 "AddEventListenerOptions",
 "AddressErrors",
 "AesCbcParams",
 "AesCtrParams",
 "AesDerivedKeyParams",
 "AesGcmParams",
 "AesKeyAlgorithm",
 "AesKeyGenParams",
 "AggregateError",
 "AggregateErrorConstructor",
 "Algorithm",
 "AlgorithmIdentifier",
 "AlignSetting",
 "AllAcceptedCredentialsOptions",
 "AllowSharedBuffer",
 "AllowSharedBufferSource",
 "AlphaOption",
 "AnalyserNode",
 "AnalyserOptions",
 "Animatable",
 "Animation",
 "AnimationEffect",
 "AnimationEvent",
 "AnimationEventInit",
 "AnimationEventMap",
 "AnimationFrameProvider",
 "AnimationPlayState",
 "AnimationPlaybackEvent",
 "AnimationPlaybackEventInit",
 "AnimationReplaceState",
 "AnimationTimeline",
 "AppendMode",
 "Array",
 "ArrayBuffer",
 "ArrayBufferConstructor",
 "ArrayBufferLike",
 "ArrayBufferTypes",
 "ArrayBufferView",
 "ArrayConstructor",
 "ArrayIterator",
 "ArrayLike",
 "AssignedNodesOptions",
 "AsyncDisposable",
 "AsyncDisposableStack",
 "AsyncDisposableStackConstructor",
 "AsyncGenerator",
 "AsyncGeneratorFunction",
 "AsyncGeneratorFunctionConstructor",
 "AsyncIterable",
 "AsyncIterableIterator",
 "AsyncIterator",
 "AsyncIteratorObject",
 "Atomics",
 "AttestationConveyancePreference",
 "Attr",
 "AudioBuffer",
 "AudioBufferOptions",
 "AudioBufferSourceNode",
 "AudioBufferSourceOptions",
 "AudioCo
... (46097 characters)
```

Actual:

```json
[
 "ANGLE_instanced_arrays",
 "ARIAMixin",
 "AacBitstreamFormat",
 "AacEncoderConfig",
 "AbortController",
 "AbortSignal",
 "AbortSignalEventMap",
 "AbstractRange",
 "AbstractWorker",
 "AbstractWorkerEventMap",
 "AddEventListenerOptions",
 "AddressErrors",
 "AesCbcParams",
 "AesCtrParams",
 "AesDerivedKeyParams",
 "AesGcmParams",
 "AesKeyAlgorithm",
 "AesKeyGenParams",
 "AggregateError",
 "AggregateErrorConstructor",
 "Algorithm",
 "AlgorithmIdentifier",
 "AlignSetting",
 "AllAcceptedCredentialsOptions",
 "AllowSharedBuffer",
 "AllowSharedBufferSource",
 "AlphaOption",
 "AnalyserNode",
 "AnalyserOptions",
 "Animatable",
 "Animation",
 "AnimationEffect",
 "AnimationEvent",
 "AnimationEventInit",
 "AnimationEventMap",
 "AnimationFrameProvider",
 "AnimationPlayState",
 "AnimationPlaybackEvent",
 "AnimationPlaybackEventInit",
 "AnimationReplaceState",
 "AnimationTimeline",
 "AppendMode",
 "Array",
 "ArrayBuffer",
 "ArrayBufferConstructor",
 "ArrayBufferLike",
 "ArrayBufferTypes",
 "ArrayBufferView",
 "ArrayConstructor",
 "ArrayIterator",
 "ArrayLike",
 "AssignedNodesOptions",
 "AsyncDisposable",
 "AsyncDisposableStack",
 "AsyncDisposableStackConstructor",
 "AsyncGenerator",
 "AsyncGeneratorFunction",
 "AsyncGeneratorFunctionConstructor",
 "AsyncIterable",
 "AsyncIterableIterator",
 "AsyncIterator",
 "AsyncIteratorObject",
 "Atomics",
 "AttestationConveyancePreference",
 "Attr",
 "AudioBuffer",
 "AudioBufferOptions",
 "AudioBufferSourceNode",
 "AudioBufferSourceOptions",
 "AudioCo
... (46087 characters)
```

Project file `src/logic/skipValidation.ts`:

```
   1 | import type { ValidationModeFlags } from '../types';
     ...
   3 | export default (
   4 |   isBlurEvent: boolean,
   5 |   isTouched: boolean,
   6 |   isSubmitted: boolean,
   7 |   reValidateMode: Pick<ValidationModeFlags, 'isOnBlur' | 'isOnChange'>,
   8 |   mode: Partial<ValidationModeFlags>,
   9 | ) => {
  10 |   if (mode.isOnAll) {
  11 |     return false;
  12 |   } else if (!isSubmitted && mode.isOnTouch) {
  13 |     return !(isTouched || isBlurEvent);
  14 |   } else if (isSubmitted ? reValidateMode.isOnBlur : mode.isOnBlur) {
  15 |     return !isBlurEvent;
  16 |   } else if (isSubmitted ? reValidateMode.isOnChange : mode.isOnChange) {
  17 |     return isBlurEvent;
  18 |   }
  19 |   return true;
  20 | };
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts7-r6-completion-missing-completion-60ede6/repro.json
```

## Evidence and reduction

- representative 33f1bc8d2cec-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects react-hook-form/react-hook-form@5fd9ef65290b, reduxjs/redux@fb3bad6804d6, upstash/context7@6477e43e31d2, timings settled, seeds 1

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
[ts7-7.0.2-tr60ede6-r6-replay-test-baseline-20260925-163348-5b3d61] stderr: context canceled
[ts7-7.0.2-tr60ede6-r6-replay-test-control-20260925-163356-328430] stderr: context canceled
```
