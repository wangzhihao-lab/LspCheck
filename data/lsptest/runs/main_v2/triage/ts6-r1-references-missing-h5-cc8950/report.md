# [ts6 6.0.3] references misses entries after file rename round trip

Draft for the author (not filed). Group `ts6-r1-references-missing-h5-cc8950`, signature `ts6|r1_history|references:missing`, case family `H5`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `mifi/lossless-cut@85cb95f6aeae` (corpus, commit 85cb95f6aeaed9c26dfe64fd5ac6c6ac7760c55f), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/common/util.ts`
3. textDocument/didOpen: `open src/renderer/src/edlFormats.test.ts`
4. textDocument/didOpen: `open src/renderer/src/worker/eval.ts`
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/common/util.ts -> src/common/util_rt.ts`
6. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/common/util_rt.ts -> src/common/util.ts`
7. Timing: wait until the server is idle after every step.
8. Query `textDocument/references` on `src/common/util.ts` line 3, column 24 (LSP position {line: 2, character: 23}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/common/util.ts",
  2,
  13,
  2,
  33
 ],
 [
  "src/main/ffmpeg.ts",
  17,
  72,
  17,
  92
 ],
 [
  "src/main/ffmpeg.ts",
  587,
  9,
  587,
  29
 ],
 [
  "src/renderer/src/App.tsx",
  103,
  9,
  103,
  29
 ],
 [
  "src/renderer/src/App.tsx",
  2299,
  31,
  2299,
  51
 ],
 [
  "src/renderer/src/ffmpeg.ts",
  16,
  9,
  16,
  29
 ],
 [
  "src/renderer/src/ffmpeg.ts",
  581,
  23,
  581,
  43
 ]
]
```

Actual:

```json
[
 [
  "src/common/util.ts",
  2,
  13,
  2,
  33
 ]
]
```

Project file `src/common/util.ts`:

```
   1 | import type { AudioChannelInfo, FfmpegHwAccel } from './types.ts';
     ...
   3 | export const parseFfprobeDuration = (durationStr: string | undefined) => (
   4 |   durationStr != null ? parseFloat(durationStr) : undefined
   5 | );
     ...
   7 | export const getHwaccelArgs = (hwaccel: FfmpegHwAccel) => (hwaccel !== 'none' ? ['-hwaccel', hwaccel] : []);
     ...
   9 | // Used to be 5, but we recently increased to 6 because https://github.com/mifi/lossless-cut/issues/2838
  10 | // I don't remember why 5 was chosen initially, but if we don't truncate, ffmpeg can sometimes give an error when too many decimal places are used in the time argument, see:
  11 | export const formatFfmpegNumber = (time: number) => time.toFixed(6);
     ...
  13 | export function parseRatio(str: string, char = '/') {
  14 |   const split = str.split(char);
  15 |   if (split.length !== 2) return undefined;
  16 |   const num = parseInt(split[0]!, 10);
  17 |   const den = parseInt(split[1]!, 10);
  18 |   if (Number.isNaN(num) || Number.isNaN(den)) return undefined;
  19 |   if (den <= 0) return undefined;
  20 |   return num / den;
  21 | }
     ...
  23 | // ffmpeg's swresample only accepts channel layouts that it considers "sane" (see sane_layout() in
  24 | // libswresample/rematrix.c): a native layout, or a custom one whose channels form a standard speaker
  25 | // set. Anything else is rejected outright when the resampler initializes, so any operation that
  26 | // resamples or downmixes such a stream fails with:
  27 | //   [SWR] Input channel layout '4 channels (UNSD+UNSD+UNSD+UNSD)' is not supported
  28 | // There is no flag to relax this check.
  29 | //
  30 | // ffprobe describes a layout it could not express natively as "N channels (A+B+...)", e.g.
  31 | // "4 channels (UNSD+UNSD+UNSD+UNSD)" for DV/DVCPRO .mov files, whose 'chan' atom labels every channel
  32 | // as unused, or "2 channels (BL+BR)" for a surround stem pair. Layouts that do form a standard set are
  33 | // reported under their native name instead ("stereo", "5.1"), and those always work.
  34 | // A plain "N channels" (no positions at all) is also fine, which is what the fix below produces.
  35 | const customChannelLayoutRegex = /^\d+ channels \(/;
     ...
  37 | export const hasCustomChannelLayout = (channelLayout: string | undefined) => (
  38 |   channelLayout != null && customChannelLayoutRegex.test(channelLayout)
  39 | );
     ...
  41 | // The `channelmap` filter re-labels the channels without touching the samples, which turns the layout
  42 | // into a plain "N channels" (unspecified) layout. swresample handles those by skipping the rematrixing
  43 | // step entirely, so the stream then behaves exactly as if it had carried no channel layout information.
  44 | export function getFixChannelLayoutFilter({ channels, channelLayout }: AudioChannelInfo) {
  45 |   if (channels == null || channels <= 0 || !hasCustomChannelLayout(channelLayout)) return undefined;
  46 |   return `channelmap=${Array.from({ length: channels }, (_, i) => i).join('|')}`;
  47 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-references-missing-h5-cc8950/repro.json
```

## Evidence and reduction

- representative 0d6f841395f8-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 5 -> 5 (14 probes, 735.399 s, reduced ops confirmed 2/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects Gitlawb/openclaude@5cd11336caea, mifi/lossless-cut@85cb95f6aeae, umami-software/umami@12ad773d621f, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#878](https://github.com/typescript-language-server/typescript-language-server/issues/878) Support renaming files when renaming default exports (open, 2024-02-27, 1 comments)
- [typescript-language-server/typescript-language-server#744](https://github.com/typescript-language-server/typescript-language-server/issues/744) EPERM: operation not permitted Cannot Move/Rename Files & Directories when Language Server is Running.  (closed, 2023-07-31, 1 comments)
- [typescript-language-server/typescript-language-server#665](https://github.com/typescript-language-server/typescript-language-server/issues/665) Preview rename file (closed, 2023-01-16, 1 comments)
- [typescript-language-server/typescript-language-server#430](https://github.com/typescript-language-server/typescript-language-server/issues/430) Rename also trigger on files in node_modules (closed, 2022-04-07, 0 comments)
- [typescript-language-server/typescript-language-server#945](https://github.com/typescript-language-server/typescript-language-server/issues/945) Cross-file referencing not working when using multilspy client (closed, 2025-03-06, 2 comments)
- [typescript-language-server/typescript-language-server#948](https://github.com/typescript-language-server/typescript-language-server/issues/948) workspace/symbol Fails to Recognize rootPath and Inconsistent Responses Without Debugging (closed, 2025-03-14, 3 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#277](https://github.com/typescript-language-server/typescript-language-server/issues/277) Using typescript plugins through neovim-lsp (closed, 2021-10-31, 10 comments)
- queries: `"rename file" in:title repo:typescript-language-server/typescript-language-server is:issue`; `references missing repo:typescript-language-server/typescript-language-server is:issue`; `references "rename file" repo:typescript-language-server/typescript-language-server is:issue`; `references stale repo:typescript-language-server/typescript-language-server is:issue`; `"rename file" in:title repo:microsoft/TypeScript is:issue`; `references missing repo:microsoft/TypeScript is:issue`; `references "rename file" repo:microsoft/TypeScript is:issue`; `references stale repo:microsoft/TypeScript is:issue`
