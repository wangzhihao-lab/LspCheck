# [rust-analyzer 2026-09-21] diagnostics: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-diagnostics-extra-unlinked-file-a-751ce1`, signature `rust-analyzer|r3_routes|diagnostics:extra:unlinked-file`, case family `a`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `BurntSushi/ripgrep@3fce3b5bb023` (corpus, commit 3fce3b5bb0236da2df6d99672afb8a719642eca7), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions on the same project: the server's default diagnostics route and the push route; the diagnostics of `crates/ignore/src/types.rs` must be equal.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  0,
  0,
  0,
  2,
  4,
  "unlinked-file",
  "rust-analyzer",
  "This file is not included in any crates, so rust-analyzer can't offer IDE services. If you're intentionally working on unowned files, you can silence this warning by adding \"unlinked-file\" to rust-analyzer.diagnostics.disabled in your settings."
 ]
]
```

Project file `crates/ignore/src/types.rs`:

```
   1 | /*!
   2 | The types module provides a way of associating globs on file names to file
   3 | types.
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-diagnostics-extra-unlinked-file-a-751ce1/repro.json
```

## Evidence and reduction

- representative 29d2893b9177-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 1/3)
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects BurntSushi/ripgrep@3fce3b5bb023, lapce/lapce@b604d57de4a8, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#18375](https://github.com/rust-lang/rust-analyzer/issues/18375) Implement the LSP diagnostics pull model (closed, 2024-10-23, 0 comments)
- [rust-lang/rust-analyzer#23193](https://github.com/rust-lang/rust-analyzer/issues/23193) FP `expected &&&u32, found &&&&&&&&&&&&&&&&&&&&&&&&&i32` (open, 2026-08-19, 5 comments)
- [rust-lang/rust-analyzer#13317](https://github.com/rust-lang/rust-analyzer/issues/13317) Runnables: Extra Args sets Args instead of Extra Args (open, 2022-09-30, 0 comments)
- [rust-lang/rust-analyzer#19491](https://github.com/rust-lang/rust-analyzer/issues/19491) Too many arguments generates two diagnostics (open, 2025-04-01, 13 comments)
- [rust-lang/rust-analyzer#22828](https://github.com/rust-lang/rust-analyzer/issues/22828) panic: `can't project out of` (open, 2026-07-16, 6 comments)
- [rust-lang/rust-analyzer#21662](https://github.com/rust-lang/rust-analyzer/issues/21662) Documentation hint discrepency between autocomplete and inner function (open, 2026-02-17, 2 comments)
- [rust-lang/rust-analyzer#18709](https://github.com/rust-lang/rust-analyzer/issues/18709) rust-analyzer didn't return warning/hint diagnostics on `textDocument/diagnostic` (open, 2024-12-18, 11 comments)
- [rust-lang/rust-analyzer#18732](https://github.com/rust-lang/rust-analyzer/issues/18732) stale diagnostic after panic (open, 2024-12-21, 6 comments)
- queries: `"pull diagnostics" in:title repo:rust-lang/rust-analyzer is:issue`; `diagnostics extra repo:rust-lang/rust-analyzer is:issue`; `diagnostics "pull diagnostics" repo:rust-lang/rust-analyzer is:issue`; `diagnostics inconsistent repo:rust-lang/rust-analyzer is:issue`
