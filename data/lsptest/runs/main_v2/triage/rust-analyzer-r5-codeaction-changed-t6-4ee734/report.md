# [rust-analyzer 2026-09-21] codeAction changes its answer after transformation T6

Draft for the author (not filed). Group `rust-analyzer-r5-codeaction-changed-t6-4ee734`, signature `rust-analyzer|r5_transforms|codeAction:changed`, case family `T6`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `niri-wm/niri@5f4469b6a992` (corpus, commit 5f4469b6a992492cf7221b269e9379f42e737649), language rust

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T6 applied to `src/ipc/client.rs` (1 edit(s), first [53, 37, 53, 37]).
3. Query `textDocument/codeAction` on `src/ipc/client.rs` line 54, column 40 (LSP position {line: 53, character: 39}) (pos); compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "Inline `std::io::stdin`",
  "refactor.inline"
 ],
 [
  "Replace qualified path with use",
  "refactor.rewrite"
 ]
]
```

Actual:

```json
[
 [
  "Inline `std::io::/* 注释🙂 */ stdin`",
  "refactor.inline"
 ],
 [
  "Replace qualified path with use",
  "refactor.rewrite"
 ]
]
```

Project file `src/ipc/client.rs`:

```
  51 |         Msg::Casts => Request::Casts,
  52 |         Msg::RawRequest => {
  53 |             let mut buf = Vec::new();
  54 |             let mut stdin = std::io::stdin().lock();
  55 |             stdin
  56 |                 .read_until(b'\n', &mut buf)
  57 |                 .context("error reading from stdin")?;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r5-codeaction-changed-t6-4ee734/repro.json
```

## Evidence and reduction

- representative 0c1168881081-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects casey/just@6119e6aff518, niri-wm/niri@5f4469b6a992, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#23301](https://github.com/rust-lang/rust-analyzer/issues/23301) Error messages disappear when `rustc-unicode` is enabled (closed, 2026-09-06, 4 comments)
- [rust-lang/rust-analyzer#17420](https://github.com/rust-lang/rust-analyzer/issues/17420) "Request textdocument/selectionrange Failed" when executing editor.action.smartSelect.expand in vscode on some unicode box drawing characters (closed, 2024-06-14, 1 comments)
- [rust-lang/rust-analyzer#9401](https://github.com/rust-lang/rust-analyzer/issues/9401) Add unicode character snippets (closed, 2021-06-25, 2 comments)
- [rust-lang/rust-analyzer#9121](https://github.com/rust-lang/rust-analyzer/issues/9121) Panic on textDocument/didChange containing a multi-byte unicode character (closed, 2021-06-03, 5 comments)
- [rust-lang/rust-analyzer#7635](https://github.com/rust-lang/rust-analyzer/issues/7635) Unicode-related panic when editing comment (closed, 2021-02-10, 2 comments)
- [rust-lang/rust-analyzer#16504](https://github.com/rust-lang/rust-analyzer/issues/16504) Wrong `try_into` for enum variant if `Result` is shadowed (open, 2024-02-07, 0 comments)
- [rust-lang/rust-analyzer#21601](https://github.com/rust-lang/rust-analyzer/issues/21601) Inline assist on `.into()` produces wrong code (open, 2026-02-07, 3 comments)
- [rust-lang/rust-analyzer#12938](https://github.com/rust-lang/rust-analyzer/issues/12938) fill match arms assist put the code in the wrong place (open, 2022-08-04, 10 comments)
- queries: `unicode in:title repo:rust-lang/rust-analyzer is:issue`; `"code action" wrong repo:rust-lang/rust-analyzer is:issue`; `"code action" unicode repo:rust-lang/rust-analyzer is:issue`; `"code action" whitespace repo:rust-lang/rust-analyzer is:issue`

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: 2026-11-18T23:41:35.842044-08:00 ERROR FetchBuildDataError: error: failed to run custom build command for `gtk4-sys v0.10.3`
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: note: To improve backtraces for build dependencies, set the CARGO_PROFILE_DEV_BUILD_OVERRIDE_DEBUG=true environment variable to enable debug information generation.
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: Caused by:
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: process didn't exit successfully: `temp/lsptest_runs/rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0/ws/target/debug/build/gtk4-sys-231b5ca87aed2a8b/buil
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: --- stdout
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: cargo:rerun-if-changed=~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/gtk4-sys-0.10.3/Cargo.toml
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: cargo:rerun-if-env-changed=GTK4_NO_PKG_CONFIG
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: cargo:rerun-if-env-changed=PKG_CONFIG_aarch64-apple-darwin
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: cargo:rerun-if-env-changed=PKG_CONFIG_aarch64_apple_darwin
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: cargo:rerun-if-env-changed=HOST_PKG_CONFIG
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: cargo:rerun-if-env-changed=PKG_CONFIG
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-baseline-20261118-234118-7dadd0] stderr: cargo:rerun-if-env-changed=PKG_CONFIG_PATH_aarch64-apple-darwin
... 1125 lines omitted ...
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: HINT: if you have installed the library, try setting PKG_CONFIG_PATH to the directory containing `libdisplay-info.pc`.
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: )
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: stack backtrace:
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: 0: __rustc::rust_begin_unwind
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: at /rustc/48a229ceaefd4985c50990b14116b6d856af0985/library/std/src/panicking.rs:679:5
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: 1: core::panicking::panic_fmt
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: at /rustc/48a229ceaefd4985c50990b14116b6d856af0985/library/core/src/panicking.rs:80:14
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: 2: core::result::unwrap_failed
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: at /rustc/48a229ceaefd4985c50990b14116b6d856af0985/library/core/src/result.rs:1870:5
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: 3: build_script_build::main
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: 4: <fn() as core::ops::function::FnOnce<()>>::call_once
[rust-analyzer-2026-09-21-tr4ee734-r5-replay-control-20261118-234152-883123] stderr: note: Some details are omitted, run with `RUST_BACKTRACE=full` for a verbose backtrace.
```
