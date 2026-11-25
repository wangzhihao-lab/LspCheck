# [ts6 6.0.3] signatureHelp loses its answer after edit inside a workspace window

Draft for the author (not filed). Group `ts6-r1-signaturehelp-lost-h9-7bd793`, signature `ts6|r1_history|signatureHelp:lost`, case family `H9`.

## Server

- ts6 6.0.3; launch `~/.local/state/fnm_multishells/22713_1790129010272/bin/node temp/lsp_servers/ts6-6.0.3/node_modules/typescript-language-server/lib/cli.mjs --stdio`; entry sha256 146b113929fd41f1; package version 6.0.0; node v24.3.0
- project `ChatGPTNextWeb/NextChat@defdcdb55d85` (corpus, commit defdcdb55d850cd12c4c657eb83729fd66e215c0), language typescript

## Relation violated

History independence (R1): after a sequence of edits that returns the documents to content C, every query must answer as in a fresh session opened on C. Fresh sessions on C agree with each other on this query; the session that went through the history does not.

## Minimal steps (LSP)

1. Start ts6 6.0.3 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open app/components/mask.tsx`
3. textDocument/didOpen: `open app/utils/store.ts`
4. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename app/utils/store.ts -> app/utils/store_rt.ts`
5. textDocument/didChange: `change app/components/mask.tsx (231, 0)-(232, 0) ""`
6. textDocument/didChange: `change app/components/mask.tsx (231, 7)-(231, 7) "           (await showConfirm(L"`
7. textDocument/didChange: `change app/components/mask.tsx (231, 38)-(231, 38) "ocale.Mask.Config.Syn"`
8. textDocument/didChange: `change app/components/mask.tsx (231, 59)-(231, 59) "c.Confirm))\n"`
9. workspace/willRenameFiles, didClose, rename on disk, workspace/didRenameFiles, didChangeWatchedFiles, didOpen of the new path: `fs_rename app/utils/store_rt.ts -> app/utils/store.ts`
10. Timing: wait until the server is idle after every step.
11. textDocument/didOpen `app/command.ts` (the query step opens every target file that is not open), then wait until the server is idle.
12. Query `textDocument/signatureHelp` on `app/components/mask.tsx` line 608, column 25 (LSP position {line: 607, character: 24}); compare with the same query in a fresh session opened on the final content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
"map(callbackfn: (value: Mask, index: number, array: Mask[]) => JSX.Element, thisArg?: any): JSX.Element[]"
```

Actual:

```json
null
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/ts6-r1-signaturehelp-lost-h9-7bd793/repro.json
```

## Evidence and reduction

- representative 5ae299935d29-v04: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 14 -> 8 (32 probes, 1794.615 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects ChatGPTNextWeb/NextChat@defdcdb55d85, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [typescript-language-server/typescript-language-server#948](https://github.com/typescript-language-server/typescript-language-server/issues/948) workspace/symbol Fails to Recognize rootPath and Inconsistent Responses Without Debugging (closed, 2025-03-14, 3 comments)
- [microsoft/TypeScript#29041](https://github.com/microsoft/TypeScript/issues/29041) Improve signature help when completing object argument (open, 2018-12-15, 2 comments)
- [microsoft/TypeScript#59926](https://github.com/microsoft/TypeScript/issues/59926) Improve Iterator Helper Type Signatures (open, 2024-09-10, 10 comments)
- [microsoft/TypeScript#63839](https://github.com/microsoft/TypeScript/issues/63839) Behavior difference: Block comments on `@typedef` structural types are not preserved, if they are imported and reconstructed as inline types in another file (open, 2026-06-17, 5 comments)
- [microsoft/TypeScript#30269](https://github.com/microsoft/TypeScript/issues/30269) TypeError: Cannot read property 'kind' of undefined (closed, 2019-03-08, 1 comments)
- [microsoft/TypeScript#28357](https://github.com/microsoft/TypeScript/issues/28357) TypeScript doesn't allow event : CustomEvent in addEventListener (open, 2018-11-04, 45 comments)
- [microsoft/TypeScript#24929](https://github.com/microsoft/TypeScript/issues/24929) Use conditional type to narrow return type of function with a union-typed argument (closed, 2018-06-13, 29 comments)
- queries: `"signature help" missing repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" stale repo:typescript-language-server/typescript-language-server is:issue`; `"signature help" missing repo:microsoft/TypeScript is:issue`; `"signature help" stale repo:microsoft/TypeScript is:issue`
