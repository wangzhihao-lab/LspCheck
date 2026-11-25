# [rust-analyzer 2026-09-21] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-definitionconsistency-missing-d-586fd8`, signature `rust-analyzer|r3_routes|definitionConsistency:missing`, case family `d`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `casey/just@6119e6aff518` (corpus, commit 6119e6aff518b6550d9030955f905b01051b5772), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/cache_lock.rs` at line 12, column 10 (LSP position {line: 11, character: 9}) gives the expected set; didOpen `src/cache_lock.rs` and `textDocument/definition` at the reference line 11, column 23 (LSP position {line: 10, character: 22}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/cache_lock.rs",
  10,
  19,
  10,
  25
 ],
 [
  "src/error.rs",
  163,
  4,
  163,
  10
 ]
]
```

Actual:

```json
[
 [
  "src/cache_lock.rs",
  10,
  19,
  10,
  25
 ]
]
```

Project file `src/cache_lock.rs`:

```
   1 | use super::*;
     ...
   3 | pub(crate) struct CacheLock {
   4 |   pub(crate) file: File,
   5 |   pub(crate) path: Utf8PathBuf,
   6 |   pub(crate) recipe: Modulepath,
   7 | }
     ...
   9 | impl CacheLock {
  10 |   pub(crate) fn save(mut self) -> RunResult<'static> {
  11 |     let context = |source| Error::FilesystemIo {
  12 |       source,
  13 |       path: self.path.clone(),
  14 |     };
     ...
  16 |     self.file.set_len(0).map_err(context)?;
     ...
  18 |     self.file.rewind().map_err(context)?;
     ...
  20 |     let entry = CacheEntry {
  21 |       recipe: self.recipe,
  22 |     };
     ...
  24 |     serde_json::to_writer(&mut self.file, &entry).map_err(|source| Error::CacheEntryWrite {
  25 |       source,
  26 |       path: self.path,
  27 |     })
  28 |   }
  29 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r3-definitionconsistency-missing-d-586fd8/repro.json
```

## Evidence and reduction

- representative 53dd5e55330e-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects casey/just@6119e6aff518, niri-wm/niri@5f4469b6a992, yewstack/yew@bfa6c19af971, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#8373](https://github.com/rust-lang/rust-analyzer/issues/8373) Monomorphised go to definition (open, 2021-04-06, 1 comments)
- [rust-lang/rust-analyzer#17122](https://github.com/rust-lang/rust-analyzer/issues/17122) Go to Definition on Private Symbols (open, 2024-04-22, 2 comments)
- [rust-lang/rust-analyzer#22482](https://github.com/rust-lang/rust-analyzer/issues/22482) Panics with "invalid offset" errors ( code: -32603) on "Go to definition" calls (open, 2026-05-28, 4 comments)
- [rust-lang/rust-analyzer#14428](https://github.com/rust-lang/rust-analyzer/issues/14428) Go to definition on std types locks rustc (open, 2023-03-28, 2 comments)
- [rust-lang/rust-analyzer#10700](https://github.com/rust-lang/rust-analyzer/issues/10700) [Feature Request] Go to Definition from the comments (open, 2021-11-05, 1 comments)
- [rust-lang/rust-analyzer#23299](https://github.com/rust-lang/rust-analyzer/issues/23299) scip: panics with "Invariant violation: file emitted multiple times" when one file is mounted into two targets via #[path] (open, 2026-09-06, 2 comments)
- [rust-lang/rust-analyzer#14377](https://github.com/rust-lang/rust-analyzer/issues/14377) Missing constant color highlighting inside `stringify!` (open, 2023-03-19, 3 comments)
- [rust-lang/rust-analyzer#12665](https://github.com/rust-lang/rust-analyzer/issues/12665) Rust-analyzer vscode extension : missing codes under macro in Outline (open, 2022-07-01, 3 comments)
- queries: `"go to definition" in:title repo:rust-lang/rust-analyzer is:issue`; `definition missing repo:rust-lang/rust-analyzer is:issue`; `definition "go to definition" repo:rust-lang/rust-analyzer is:issue`; `definition inconsistent repo:rust-lang/rust-analyzer is:issue`
