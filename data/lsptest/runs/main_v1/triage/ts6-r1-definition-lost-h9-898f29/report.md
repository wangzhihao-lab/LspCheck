# [ts6 6.0.3] definition loses its answer after edit inside a workspace window

Draft for the author (not filed). Group `ts6-r1-definition-lost-h9-898f29`, signature `ts6|r1_history|definition:lost`, case family `H9`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `ChatGPTNextWeb/NextChat@defdcdb55d85` (corpus, commit defdcdb55d850cd12c4c657eb83729fd66e215c0), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open app/command.ts`
3. textDocument/didOpen: `open app/components/mask.tsx`
4. textDocument/didOpen: `open app/utils/store.ts`
5. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename app/utils/store.ts -> app/utils/store_rt.ts`
6. textDocument/didChange: `change app/components/mask.tsx (231, 0)-(232, 0) ""`
7. textDocument/didChange: `change app/components/mask.tsx (231, 0)-(231, 0) "       "`
8. textDocument/didChange: `change app/components/mask.tsx (231, 7)-(231, 7) "           (await showConfirm(L"`
9. textDocument/didChange: `change app/components/mask.tsx (231, 38)-(231, 38) "ocale.Mask.Config.Syn"`
10. textDocument/didChange: `change app/components/mask.tsx (231, 59)-(231, 59) "c.Confirm))\n"`
11. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename app/utils/store_rt.ts -> app/utils/store.ts`
12. Timing: wait until the server is idle after every step.
13. Query `textDocument/definition` on `app/components/mask.tsx` line 608, column 25 (LSP position {line: 607, character: 24}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "app/store/mask.ts",
  18,
  2,
  18,
  9
 ]
]
```

Actual:

```json
[]
```

Project file `app/components/mask.tsx`:

```
 229 |                 const checked = e.currentTarget.checked;
 230 |                 if (
 231 |                   checked &&
 232 |                   (await showConfirm(Locale.Mask.Config.Sync.Confirm))
 233 |                 ) {
 234 |                   props.updateMask((mask) => {
 235 |                     mask.syncGlobalConfig = checked;
     ...
 605 |                       navigate(Path.Chat);
 606 |                     }}
 607 |                   />
 608 |                   {m.builtin ? (
 609 |                     <IconButton
 610 |                       icon={<EyeIcon />}
 611 |                       text={Locale.Mask.Item.View}
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-definition-lost-h9-898f29/repro.json
```

## Evidence and reduction

- representative 5ae299935d29-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 14 -> 10 (19 probes, 1902.65 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, timings settled, seeds 2

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
