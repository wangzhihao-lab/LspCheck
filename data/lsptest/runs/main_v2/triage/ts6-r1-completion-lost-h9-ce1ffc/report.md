# [ts6 6.0.3] completion loses its answer after edit inside a workspace window

Draft for the author (not filed). Group `ts6-r1-completion-lost-h9-ce1ffc`, signature `ts6|r1_history|completion:lost`, case family `H9`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `mifi/lossless-cut@85cb95f6aeae` (corpus, commit 85cb95f6aeaed9c26dfe64fd5ac6c6ac7760c55f), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/main/progress.test.ts`
3. textDocument/didOpen: `open src/renderer/src/TopMenu.tsx`
4. textDocument/didOpen: `open src/renderer/src/hooks/useUserSettings.ts`
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/renderer/src/hooks/useUserSettings.ts -> src/renderer/src/hooks/useUserSettings_rt.ts`
6. textDocument/didChange: `change src/renderer/src/TopMenu.tsx (23, 0)-(24, 0) ""`
7. textDocument/didChange: `change src/renderer/src/TopMenu.tsx (23, 10)-(23, 10) "opMenu("`
8. textDocument/didChange: `change src/renderer/src/TopMenu.tsx (23, 17)-(23, 17) "{\n"`
9. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/renderer/src/hooks/useUserSettings_rt.ts -> src/renderer/src/hooks/useUserSettings.ts`
10. Timing: wait until the server is idle after every step.
11. Query `textDocument/completion` on `src/renderer/src/TopMenu.tsx` line 54, column 40 (LSP position {line: 53, character: 39}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 "allowMultipleInstances",
 "askBeforeClose",
 "autoDeleteMergedSegments",
 "autoExportExtraStreams",
 "autoLoadTimecode",
 "autoMerge",
 "autoSaveProjectFile",
 "avoidNegativeTs",
 "captureFormat",
 "captureFrameFileNameFormat",
 "captureFrameMethod",
 "captureFrameQuality",
 "changeOutDir",
 "cleanupChoices",
 "customFfPath",
 "cutFileTemplate",
 "cutFromAdjustmentFrames",
 "cutMergedFileTemplate",
 "cutToAdjustmentFrames",
 "effectiveExportMode",
 "enableAskForFileOpenAction",
 "enableAutoHtml5ify",
 "enableCustomOutDir",
 "enableImportChapters",
 "enableNativeHevc",
 "enableOverwriteOutput",
 "enableSmartCut",
 "enableUpdateCheck",
 "ensureWritableOutDirWithFilePath",
 "exportConfirmEnabled",
 "ffmpegExperimental",
 "ffmpegHwaccel",
 "hideNotifications",
 "hideOsNotifications",
 "invertCutSegments",
 "invertTimelineScroll",
 "keyBindings",
 "keyboardNormalSeekSpeed",
 "keyboardSeekAccFactor",
 "keyboardSeekSpeed2",
 "keyboardSeekSpeed3",
 "keyframeCut",
 "keyframesEnabled",
 "language",
 "lastAppVersion",
 "mergedFileTemplate",
 "mouseWheelFrameSeekModifierKey",
 "mouseWheelKeyframeSeekModifierKey",
 "mouseWheelZoomModifierKey",
 "movFastStart"
]
```

Actual:

```json
[]
```

Project file `src/renderer/src/TopMenu.tsx`:

```
   1 | import type { CSSProperties, ReactNode } from 'react';
   2 | import { memo, useCallback, useEffect, useRef } from 'react';
   3 | import { IoIosSettings } from 'react-icons/io';
   4 | import { FaFilter, FaList, FaLock, FaMoon, FaSun, FaUnlock } from 'react-icons/fa';
   5 | import { useTranslation } from 'react-i18next';
   6 | import Button from './components/Button';
     ...
   8 | import ExportModeButton from './components/ExportModeButton';
     ...
  10 | import { withBlur } from './util';
  11 | import { primaryTextColor, controlsBackground, darkModeTransition } from './colors';
  12 | import useUserSettings from './hooks/useUserSettings';
  13 | import useActionTitle from './hooks/useActionTitle';
  14 | import styles from './TopMenu.module.css';
  15 | import OutDirSelector from './components/OutDirSelector';
     ...
  18 | const { stat } = window.require('node:fs/promises');
  19 | const { webUtils } = window.require('electron');
     ...
  21 | const outFmtStyle = { maxWidth: 100 };
  22 | const exportModeStyle = { flexGrow: 0, flexBasis: 140 };
     ...
  24 | function TopMenu({
  25 |   filePath,
  26 |   fileFormat,
  27 |   changeEnabledStreamsFilter,
  28 |   applyEnabledStreamsFilter,
  29 |   enabledStreamsFilter,
  30 |   renderOutFmt,
  31 |   numStreamsToCopy,
  32 |   numStreamsTotal,
  33 |   setStreamsSelectorShown,
  34 |   toggleSettings,
  35 |   selectedSegments,
  36 |   isCustomFormatSelected,
  37 |   toggleDarkMode,
  38 | }: {
  39 |   filePath: string | undefined,
  40 |   fileFormat: string | undefined,
  41 |   changeEnabledStreamsFilter: () => void,
  42 |   applyEnabledStreamsFilter: () => void,
  43 |   enabledStreamsFilter: string | undefined,
  44 |   renderOutFmt: (style: CSSProperties) => ReactNode,
  45 |   numStreamsToCopy: number,
  46 |   numStreamsTotal: number,
  47 |   setStreamsSelectorShown: (v: boolean) => void,
  48 |   toggleSettings: () => void,
  49 |   selectedSegments: unknown[],
  50 |   isCustomFormatSelected: boolean,
  51 |   toggleDarkMode: () => void,
  52 | }) {
  53 |   const { t } = useTranslation();
  54 |   const { customOutDir, setCustomOutDir, simpleMode, outFormatLocked, setOutFormatLocked, darkMode } = useUserSettings();
  55 |   const actionTitle = useActionTitle();
  56 |   const workingDirButtonRef = useRef<HTMLButtonElement>(null);
     ...
  58 |   const DarkMode = darkMode ? FaSun : FaMoon;
     ...
  60 |   const onOutFormatLockedClick = useCallback(() => setOutFormatLocked((v) => (v ? undefined : fileFormat)), [fileFormat, setOutFormatLocked]);
     ...
  62 |   const showClearWorkingDirButton = !!customOutDir;
     ...
  64 |   function renderFormatLock() {
  65 |     const Icon = outFormatLocked ? FaLock : FaUnlock;
  66 |     return (
  67 |       <Button style={{ marginRight: '.7em' }}>
  68 |         <Icon onClick={onOutFormatLockedClick} title={t('Lock/unlock output format')} style={{ fontSize: '.8em', color: outFormatLocked ? primaryTextColor : undefined }} />
  69 |       </Button>
  70 |     );
  71 |   }
     ...
  73 |   // Convenience for drag and drop: https://github.com/mifi/lossless-cut/issues/2147
  74 |   useEffect(() => {
  75 |     async function onDrop(ev: DragEvent) {
  76 |       ev.preventDefault();
  77 |       if (!ev.dataTransfer) return;
  78 |       const paths = [...ev.dataTransfer.files].map((f) => webUtils.getPathForFile(f));
  79 |       const [firstPath] = paths;
  80 |       if (paths.length === 1 && firstPath && (await stat(firstPath)).isDirectory()) {
  81 |         setCustomOutDir(firstPath);
  82 |       }
  83 |     }
  84 |     const element = workingDirButtonRef.current;
  85 |     element?.addEventListener('drop', onDrop);
  86 |     return () => element?.removeEventListener('drop', onDrop);
  87 |   }, [setCustomOutDir]);
     ...
  89 |   return (
  90 |     <div
  91 |       className={`no-user-select ${styles['wrapper']}`}
  92 |       style={{ background: controlsBackground, transition: darkModeTransition, display: 'flex', alignItems: 'center', padding: '.3em .3em', gap: '.3em', justifyContent: 'space-between', flexWrap: 'wrap' }}
  93 |     >
  94 |       {filePath && (
  95 |         <>
  96 |           <Button onClick={withBlur(() => setStreamsSelectorShown(true))}>
  97 |             <FaList style={{ fontSize: '.7em', marginRight: '.5em' }} />
  98 |             {t('Tracks')} ({numStreamsToCopy}/{numStreamsTotal})
  99 |           </Button>
     ...
 101 |           {enabledStreamsFilter != null && (
 102 |             <Button
 103 |               onClick={withBlur(() => applyEnabledStreamsFilter())}
 104 |               title={actionTitle(t('Toggle tracks using current filter'), 'toggleStripCurrentFilter')}
 105 |             >
 106 |               <FaFilter
 107 |                 style={{ fontSize: '.8em', verticalAlign: 'middle' }}
 108 |               />
 109 |             </Button>
 110 |           )}
     ...
 112 |           <Button
 113 |             onClick={changeEnabledStreamsFilter}
 114 |           >
 115 |             {enabledStreamsFilter == null && <FaFilter style={{ fontSize: '.7em', marginRight: '.4em' }} />}
 116 |             {t('Filter tracks')}
 117 |           </Button>
 118 |         </>
 119 |       )}
     ...
 121 |       <div style={{ flexGrow: 1 }} />
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-completion-lost-h9-ce1ffc/repro.json
```

## Evidence and reduction

- representative d943bb79c7d7-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 12 -> 8 (27 probes, 1843.001 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects mifi/lossless-cut@85cb95f6aeae, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#962](https://github.com/typescript-language-server/typescript-language-server/issues/962) Angular auto-imports disappear depending on the trigger character (closed, 2025-07-21, 2 comments)
- [typescript-language-server/typescript-language-server#904](https://github.com/typescript-language-server/typescript-language-server/issues/904) Ignore typescript type errors in `.js` / `.jsx` files (closed, 2024-06-28, 3 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#631](https://github.com/typescript-language-server/typescript-language-server/issues/631) missed ?.  and filterText (closed, 2022-11-22, 34 comments)
- [typescript-language-server/typescript-language-server#650](https://github.com/typescript-language-server/typescript-language-server/issues/650) [Request for info] open performance work (closed, 2022-12-29, 2 comments)
- [microsoft/TypeScript#37281](https://github.com/microsoft/TypeScript/issues/37281) No completions in `@param` tag missing parameter name (open, 2020-03-08, 1 comments)
- [microsoft/TypeScript#38738](https://github.com/microsoft/TypeScript/issues/38738) TSServer Completions - Context Needed (open, 2020-05-22, 3 comments)
- [microsoft/TypeScript#62778](https://github.com/microsoft/TypeScript/issues/62778) Inconsistent object literal key completion for enum keys (open, 2025-11-18, 4 comments)
- queries: `completion missing repo:typescript-language-server/typescript-language-server is:issue`; `completion stale repo:typescript-language-server/typescript-language-server is:issue`; `completion missing repo:microsoft/TypeScript is:issue`; `completion stale repo:microsoft/TypeScript is:issue`
