# [rust-analyzer 2026-09-21] diagnostics: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0`, signature `rust-analyzer|r3_routes|diagnostics:missing:inactive_code`, case family `a`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `alacritty/alacritty@d692748d3f61` (corpus, commit d692748d3f61253ebe9f5094320120d22f6a046f), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions on the same project: the server's default diagnostics route and the push route; the diagnostics of `alacritty/src/cli.rs` must be equal.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  35,
  4,
  39,
  36,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"macos\" is enabled"
 ],
 [
  41,
  4,
  44,
  36,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  202,
  12,
  203,
  30,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"windows\" is disabled"
 ],
 [
  307,
  4,
  310,
  40,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"macos\" is enabled"
 ],
 [
  430,
  4,
  431,
  22,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ],
 [
  432,
  4,
  433,
  22,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ],
 [
  435,
  4,
  436,
  29,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ],
 [
  437,
  4,
  438,
  29,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ],
 [
  536,
  4,
  565,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ]
]
```

Actual:

```json
[]
```

Project file `alacritty/src/cli.rs`:

```
   1 | use std::cmp::max;
   2 | use std::collections::HashMap;
   3 | use std::ops::{Deref, DerefMut};
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0/repro.json
```

## Evidence and reduction

- representative 2c59f4574505-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects alacritty/alacritty@d692748d3f61, sxyazi/yazi@0ea4c5d9ef75, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#18375](https://github.com/rust-lang/rust-analyzer/issues/18375) Implement the LSP diagnostics pull model (closed, 2024-10-23, 0 comments)
- [rust-lang/rust-analyzer#23383](https://github.com/rust-lang/rust-analyzer/issues/23383) False negative: missing match arm when constant in trait (open, 2026-09-17, 0 comments)
- [rust-lang/rust-analyzer#23326](https://github.com/rust-lang/rust-analyzer/issues/23326) Missing "Run Doctest" CodeLens for trait method doctests (open, 2026-09-09, 0 comments)
- [rust-lang/rust-analyzer#22140](https://github.com/rust-lang/rust-analyzer/issues/22140) Address FIXMEs for adding diagnostics (open, 2026-04-22, 38 comments)
- [rust-lang/rust-analyzer#23193](https://github.com/rust-lang/rust-analyzer/issues/23193) FP `expected &&&u32, found &&&&&&&&&&&&&&&&&&&&&&&&&i32` (open, 2026-08-19, 5 comments)
- [rust-lang/rust-analyzer#22402](https://github.com/rust-lang/rust-analyzer/issues/22402) Missing type inference with diesel (open, 2026-05-18, 9 comments)
- [rust-lang/rust-analyzer#18709](https://github.com/rust-lang/rust-analyzer/issues/18709) rust-analyzer didn't return warning/hint diagnostics on `textDocument/diagnostic` (open, 2024-12-18, 11 comments)
- [rust-lang/rust-analyzer#18732](https://github.com/rust-lang/rust-analyzer/issues/18732) stale diagnostic after panic (open, 2024-12-21, 6 comments)
- queries: `"pull diagnostics" in:title repo:rust-lang/rust-analyzer is:issue`; `diagnostics missing repo:rust-lang/rust-analyzer is:issue`; `diagnostics "pull diagnostics" repo:rust-lang/rust-analyzer is:issue`; `diagnostics inconsistent repo:rust-lang/rust-analyzer is:issue`

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tr0b07f0-r3-replay-baseline-20260925-170810-165ef4] stderr: 2026-09-25T17:08:12.137082-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alac
[rust-analyzer-2026-09-21-tr0b07f0-r3-replay-baseline-20260925-170810-165ef4] stderr: 2026-09-25T17:08:21.405363-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alac
[rust-analyzer-2026-09-21-tr0b07f0-r3-replay-control-20260925-170831-ed9939] stderr: 2026-09-25T17:08:33.499795-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alacr
[rust-analyzer-2026-09-21-tr0b07f0-r3-replay-control-20260925-170831-ed9939] stderr: 2026-09-25T17:08:40.345723-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alacr
[rust-analyzer-2026-09-21-tr0b07f0-r3-replay-route-20260925-170849-3d7c9b] stderr: 2026-09-25T17:08:50.448567-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alacrit
[rust-analyzer-2026-09-21-tr0b07f0-r3-replay-route-20260925-170849-3d7c9b] stderr: 2026-09-25T17:09:00.653946-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alacrit
```
