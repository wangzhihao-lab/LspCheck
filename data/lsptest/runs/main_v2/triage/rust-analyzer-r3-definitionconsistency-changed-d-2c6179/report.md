# [rust-analyzer 2026-09-21] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-definitionconsistency-changed-d-2c6179`, signature `rust-analyzer|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `niri-wm/niri@5f4469b6a992` (corpus, commit 5f4469b6a992492cf7221b269e9379f42e737649), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `niri-visual-tests/src/cases/layout.rs` at line 28, column 9 (LSP position {line: 27, character: 8}) gives the expected set; didOpen `niri-visual-tests/src/cases/layout.rs` and `textDocument/definition` at the reference line 79, column 11 (LSP position {line: 78, character: 10}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "niri-visual-tests/src/cases/layout.rs",
  18,
  11,
  18,
  17
 ]
]
```

Actual:

```json
[
 [
  "niri-visual-tests/src/cases/layout.rs",
  27,
  5,
  27,
  11
 ]
]
```

Project file `niri-visual-tests/src/cases/layout.rs`:

```
  77 |         let start_time = clock.now_unadjusted();
     ...
  79 |         Self {
  80 |             output,
  81 |             windows: Vec::new(),
  82 |             clock,
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r3-definitionconsistency-changed-d-2c6179/repro.json
```

## Evidence and reduction

- representative 596487af6dac-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects googleworkspace/cli@a3768d0e82ad, niri-wm/niri@5f4469b6a992, yewstack/yew@bfa6c19af971, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#8373](https://github.com/rust-lang/rust-analyzer/issues/8373) Monomorphised go to definition (open, 2021-04-06, 1 comments)
- [rust-lang/rust-analyzer#17122](https://github.com/rust-lang/rust-analyzer/issues/17122) Go to Definition on Private Symbols (open, 2024-04-22, 2 comments)
- [rust-lang/rust-analyzer#22482](https://github.com/rust-lang/rust-analyzer/issues/22482) Panics with "invalid offset" errors ( code: -32603) on "Go to definition" calls (open, 2026-05-28, 4 comments)
- [rust-lang/rust-analyzer#14428](https://github.com/rust-lang/rust-analyzer/issues/14428) Go to definition on std types locks rustc (open, 2023-03-28, 2 comments)
- [rust-lang/rust-analyzer#10700](https://github.com/rust-lang/rust-analyzer/issues/10700) [Feature Request] Go to Definition from the comments (open, 2021-11-05, 1 comments)
- [rust-lang/rust-analyzer#15757](https://github.com/rust-lang/rust-analyzer/issues/15757) rust-analyzer finds wrong macro definition (open, 2023-10-14, 1 comments)
- [rust-lang/rust-analyzer#18248](https://github.com/rust-lang/rust-analyzer/issues/18248) no definition found for method, but definition location can be identified when params is wrong (open, 2024-10-06, 6 comments)
- [rust-lang/rust-analyzer#11834](https://github.com/rust-lang/rust-analyzer/issues/11834) Failed to "Run Test": run Cargo from wrong folder (open, 2022-03-28, 0 comments)
- queries: `"go to definition" in:title repo:rust-lang/rust-analyzer is:issue`; `definition wrong repo:rust-lang/rust-analyzer is:issue`; `definition "go to definition" repo:rust-lang/rust-analyzer is:issue`; `definition inconsistent repo:rust-lang/rust-analyzer is:issue`

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: 2026-11-19T00:42:37.54775-08:00 ERROR FetchBuildDataError: error: failed to run custom build command for `gtk4-sys v0.10.3`
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: note: To improve backtraces for build dependencies, set the CARGO_PROFILE_DEV_BUILD_OVERRIDE_DEBUG=true environment variable to enable debug information generation.
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: Caused by:
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: process didn't exit successfully: `temp/lsptest_runs/rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36/ws/target/debug/build/gtk4-sys-231b5ca87aed2a8b/buil
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: --- stdout
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: cargo:rerun-if-changed=~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/gtk4-sys-0.10.3/Cargo.toml
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: cargo:rerun-if-env-changed=GTK4_NO_PKG_CONFIG
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: cargo:rerun-if-env-changed=PKG_CONFIG_aarch64-apple-darwin
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: cargo:rerun-if-env-changed=PKG_CONFIG_aarch64_apple_darwin
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: cargo:rerun-if-env-changed=HOST_PKG_CONFIG
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: cargo:rerun-if-env-changed=PKG_CONFIG
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-baseline-20261119-004144-afda36] stderr: cargo:rerun-if-env-changed=PKG_CONFIG_PATH_aarch64-apple-darwin
... 742 lines omitted ...
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: HINT: if you have installed the library, try setting PKG_CONFIG_PATH to the directory containing `libdisplay-info.pc`.
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: )
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: stack backtrace:
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: 0: __rustc::rust_begin_unwind
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: at /rustc/48a229ceaefd4985c50990b14116b6d856af0985/library/std/src/panicking.rs:679:5
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: 1: core::panicking::panic_fmt
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: at /rustc/48a229ceaefd4985c50990b14116b6d856af0985/library/core/src/panicking.rs:80:14
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: 2: core::result::unwrap_failed
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: at /rustc/48a229ceaefd4985c50990b14116b6d856af0985/library/core/src/result.rs:1870:5
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: 3: build_script_build::main
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: 4: <fn() as core::ops::function::FnOnce<()>>::call_once
[rust-analyzer-2026-09-21-tr2c6179-r3-replay-control-20261119-004317-097b7c] stderr: note: Some details are omitted, run with `RUST_BACKTRACE=full` for a verbose backtrace.
```
