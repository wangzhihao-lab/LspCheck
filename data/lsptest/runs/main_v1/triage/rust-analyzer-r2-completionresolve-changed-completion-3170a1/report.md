# [rust-analyzer 2026-09-21] a stale completion handle resolves to a different edit after an intervening edit

Draft for the author (not filed). Group `rust-analyzer-r2-completionresolve-changed-completion-3170a1`, signature `rust-analyzer|r2_handles|completionResolve:changed`, case family `completion`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `sxyazi/yazi@0ea4c5d9ef75` (corpus, commit 0ea4c5d9ef75d7165c2e3b4eb8d713fc11f26c96), language rust

## Relation violated

Handle validity (R2): a code-action or completion handle minted before an edit and resolved after it must fail, return no edit, or return the same edit as a fresh handle for the same item.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. didOpen `yazi-parser/src/tasks/spawn.rs`; request completion items at line 6, column 9 (LSP position {line: 5, character: 8}) and resolve them; didChange: insert `"\n\n"` at line 6 (above); wait until idle; resolve the OLD completion item `anyhow::`; request and resolve a fresh one at the mapped position: the old handle must fail, give no edit, or give the fresh handle's edit.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "textEdit",
  7,
  2,
  7,
  8,
  "anyhow::"
 ]
]
```

Actual:

```json
[
 [
  "textEdit",
  6,
  0,
  5,
  8,
  "anyhow::"
 ]
]
```

Project file `yazi-parser/src/tasks/spawn.rs`:

```
   1 | use anyhow::anyhow;
   2 | use mlua::{ExternalError, FromLua, IntoLua, Lua, Value};
   3 | use yazi_core::tasks::TaskOpt;
   4 | use yazi_shared::event::ActionCow;
     ...
   6 | #[derive(Clone, Debug)]
   7 | pub struct SpawnForm {
   8 | 	pub opt: TaskOpt,
   9 | }
     ...
  11 | impl TryFrom<ActionCow> for SpawnForm {
  12 | 	type Error = anyhow::Error;
     ...
  14 | 	fn try_from(mut a: ActionCow) -> Result<Self, Self::Error> {
  15 | 		Ok(Self { opt: a.take_any("opt").ok_or_else(|| anyhow!("Invalid 'opt' in SpawnForm"))? })
  16 | 	}
  17 | }
     ...
  19 | impl FromLua for SpawnForm {
  20 | 	fn from_lua(_: Value, _: &Lua) -> mlua::Result<Self> { Err("unsupported".into_lua_err()) }
  21 | }
     ...
  23 | impl IntoLua for SpawnForm {
  24 | 	fn into_lua(self, _: &Lua) -> mlua::Result<Value> { Err("unsupported".into_lua_err()) }
  25 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r2-completionresolve-changed-completion-3170a1/repro.json
```

## Evidence and reduction

- representative 308d26953c2a-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects BurntSushi/ripgrep@3fce3b5bb023, rtk-ai/rtk@b748a5f75563, sxyazi/yazi@0ea4c5d9ef75, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#16240](https://github.com/rust-lang/rust-analyzer/issues/16240) No autocompletion for `inherent_associated_types` nightly feature (open, 2024-01-03, 5 comments)
- [rust-lang/rust-analyzer#18363](https://github.com/rust-lang/rust-analyzer/issues/18363) Auto-imports not working in Kate (closed, 2024-10-21, 12 comments)
- [rust-lang/rust-analyzer#18547](https://github.com/rust-lang/rust-analyzer/issues/18547) Autocomplete suggestion changes to something random once selected (closed, 2024-11-23, 18 comments)
- [rust-lang/rust-analyzer#18504](https://github.com/rust-lang/rust-analyzer/issues/18504) No signatures shown in completion popup (closed, 2024-11-11, 6 comments)
- [rust-lang/rust-analyzer#13786](https://github.com/rust-lang/rust-analyzer/issues/13786) Borrow/BorrowMut auto importing completions are confusing for newcomers (closed, 2022-12-16, 4 comments)
- [rust-lang/rust-analyzer#22442](https://github.com/rust-lang/rust-analyzer/issues/22442) auto-import macro fails when exclamation mark is present (open, 2026-05-24, 22 comments)
- queries: `"completion resolve" wrong repo:rust-lang/rust-analyzer is:issue`; `"completion resolve" stale repo:rust-lang/rust-analyzer is:issue`
