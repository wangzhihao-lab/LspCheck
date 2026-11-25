# [rust-analyzer 2026-09-21] diagnostics: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-diagnostics-missing-e0004-inactive-code-a-731c4f`, signature `rust-analyzer|r3_routes|diagnostics:missing:E0004,inactive_code`, case family `a`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `dani-garcia/vaultwarden@cc67d644f626` (corpus, commit cc67d644f62605cb46f4d16c4a2eed1a861cc8bb), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions on the same project: the server's default diagnostics route and the push route; the diagnostics of `src/db/models/attachment.rs` must be equal.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  83,
  18,
  83,
  22,
  1,
  "E0004",
  "rust-analyzer",
  "missing match arm: type `&mut DbConnInner` is non-empty"
 ],
 [
  83,
  18,
  92,
  13,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: mysql is disabled"
 ],
 [
  83,
  18,
  101,
  13,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: postgresql is disabled"
 ],
 [
  83,
  18,
  101,
  13,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: sqlite is disabled"
 ]
]
```

Actual:

```json
[]
```

Project file `src/db/models/attachment.rs`:

```
   1 | use std::time::Duration;
     ...
   3 | use bigdecimal::{BigDecimal, ToPrimitive};
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-diagnostics-missing-e0004-inactive-code-a-731c4f/repro.json
```

## Evidence and reduction

- representative ec5d10b1f270-v03: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects dani-garcia/vaultwarden@cc67d644f626, timings settled, seeds 1

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
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: 2026-09-25T17:02:34.573341-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: |
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: | |_____^
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-baseline-20260925-170202-29aad7] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: 2026-09-25T17:03:31.000526-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: |
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: | |_____^
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-control-20260925-170301-a92cd2] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: 2026-09-25T17:04:32.170835-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: |
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: | |_____^
[rust-analyzer-2026-09-21-tr731c4f-r3-replay-route-20260925-170401-6420f4] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
```
