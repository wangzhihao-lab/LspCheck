# [ts6 6.0.3] definition loses its answer after edit inside a workspace window

Draft for the author (not filed). Group `ts6-r1-definition-lost-h9-898f29`, signature `ts6|r1_history|definition:lost`, case family `H9`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `mifi/lossless-cut@85cb95f6aeae` (corpus, commit 85cb95f6aeaed9c26dfe64fd5ac6c6ac7760c55f), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open src/renderer/src/TopMenu.tsx`
3. textDocument/didOpen: `open src/renderer/src/hooks/useUserSettings.ts`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/renderer/src/hooks/useUserSettings.ts -> src/renderer/src/hooks/useUserSettings_rt.ts`
5. textDocument/didChange: `change src/renderer/src/TopMenu.tsx (23, 0)-(24, 0) ""`
6. textDocument/didChange: `change src/renderer/src/TopMenu.tsx (23, 10)-(23, 10) "opMenu("`
7. textDocument/didChange: `change src/renderer/src/TopMenu.tsx (23, 17)-(23, 17) "{\n"`
8. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename src/renderer/src/hooks/useUserSettings_rt.ts -> src/renderer/src/hooks/useUserSettings.ts`
9. Timing: wait until the server is idle after every step.
10. textDocument/didOpen `src/main/progress.test.ts` (the query step opens every target file that is not open), then wait until the server is idle.
11. Query `textDocument/definition` on `src/renderer/src/TopMenu.tsx` line 54, column 32 (LSP position {line: 53, character: 31}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/renderer/src/hooks/useUserSettingsRoot.ts",
  329,
  4,
  329,
  19
 ]
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/ts6-r1-definition-lost-h9-898f29/repro.json
```

## Evidence and reduction

- representative d943bb79c7d7-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 12 -> 7 (32 probes, 1782.011 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects mifi/lossless-cut@85cb95f6aeae, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#60](https://github.com/typescript-language-server/typescript-language-server/issues/60) Error: No Project. When starting LS from a bundled electron Theia application (closed, 2018-09-02, 9 comments)
- [typescript-language-server/typescript-language-server#679](https://github.com/typescript-language-server/typescript-language-server/issues/679) Inconsistent completion suggestions on JSX attributes (closed, 2023-02-07, 22 comments)
- [typescript-language-server/typescript-language-server#277](https://github.com/typescript-language-server/typescript-language-server/issues/277) Using typescript plugins through neovim-lsp (closed, 2021-10-31, 10 comments)
- [typescript-language-server/typescript-language-server#264](https://github.com/typescript-language-server/typescript-language-server/issues/264) Inlay Hints return empty result (closed, 2021-10-06, 4 comments)
- [typescript-language-server/typescript-language-server#203](https://github.com/typescript-language-server/typescript-language-server/issues/203) Javascript: Jump to declaration still not at JSDT's level (closed, 2021-04-16, 9 comments)
- [microsoft/TypeScript#60517](https://github.com/microsoft/TypeScript/issues/60517) Missing Boolean.toString definition and loose valueOf definition (open, 2024-11-16, 3 comments)
- [microsoft/TypeScript#28308](https://github.com/microsoft/TypeScript/issues/28308) AudioWorkletProcessor type definition is missing (open, 2018-11-02, 22 comments)
- [microsoft/TypeScript#64118](https://github.com/microsoft/TypeScript/issues/64118) dom.generated.d.ts is missing from this repo while still referenced in the docs (open, 2026-09-01, 1 comments)
- queries: `definition missing repo:typescript-language-server/typescript-language-server is:issue`; `definition stale repo:typescript-language-server/typescript-language-server is:issue`; `definition missing repo:microsoft/TypeScript is:issue`; `definition stale repo:microsoft/TypeScript is:issue`
