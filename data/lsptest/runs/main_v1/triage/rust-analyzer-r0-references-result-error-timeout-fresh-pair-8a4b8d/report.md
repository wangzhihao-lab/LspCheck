# [rust-analyzer 2026-09-21] references times out in a fresh session

Draft for the author (not filed). Group `rust-analyzer-r0-references-result-error-timeout-fresh-pair-8a4b8d`, signature `rust-analyzer|r0_crash|references:result->error:timeout`, case family `fresh-pair`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `dani-garcia/vaultwarden@cc67d644f626` (corpus, commit cc67d644f62605cb46f4d16c4a2eed1a861cc8bb), language rust

## Relation violated

A request on an unmodified project must not fail with an internal error, kill the server or time out; here it does so in two independent fresh sessions (R0 crash check).

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. didOpen every target file, wait until the server is idle, then send the queries; the failing request is below.
3. Query `textDocument/references` on `src/api/core/two_factor/duo.rs` line 8, column 13 (LSP position {line: 7, character: 12}); it fails like this in two independent fresh sessions (expected: an answer).

## Expected vs actual

Expected (fresh session / reference):

```json
"an answer that is not a server error, a crash or a timeout"
```

Actual:

```json
[
 "error",
 "timeout"
]
```

Project file `src/api/core/two_factor/duo.rs`:

```
   5 | use crate::{
   6 |     CONFIG,
   7 |     api::{
   8 |         ApiResult, EmptyResult, JsonResult, PasswordOrOtpData, core::log_user_event,
   9 |         core::two_factor::generate_recover_code,
  10 |     },
  11 |     auth::Headers,
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r0-references-result-error-timeout-fresh-pair-8a4b8d/repro.json
```

## Evidence and reduction

- representative 41afcf8c4817-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 0/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects dani-garcia/vaultwarden@cc67d644f626, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#18428](https://github.com/rust-lang/rust-analyzer/issues/18428) codeAction/resolve throws an exception for a code action without `data` (open, 2024-10-28, 0 comments)
- [rust-lang/rust-analyzer#9154](https://github.com/rust-lang/rust-analyzer/issues/9154) How to stop reporting `missing-unsafe` errors in embedded exceptions (closed, 2021-06-06, 2 comments)
- [rust-lang/rust-analyzer#8057](https://github.com/rust-lang/rust-analyzer/issues/8057) Exception when loading the VSCode plugin (closed, 2021-03-16, 25 comments)
- [rust-lang/rust-analyzer#20443](https://github.com/rust-lang/rust-analyzer/issues/20443) New trait solver migration issues (closed, 2025-08-13, 43 comments)
- [rust-lang/rust-analyzer#10910](https://github.com/rust-lang/rust-analyzer/issues/10910) Stuck at 'rust_analyzer: -32801: waiting for cargo metadata or cargo check' (closed, 2021-12-03, 44 comments)
- [rust-lang/rust-analyzer#11933](https://github.com/rust-lang/rust-analyzer/issues/11933) rust-analyzer in VS Code will stick in the save action for a long time (closed, 2022-04-08, 17 comments)
- [rust-lang/rust-analyzer#6568](https://github.com/rust-lang/rust-analyzer/issues/6568) 'Find all references' hangs forever (closed, 2020-11-17, 5 comments)
- [rust-lang/rust-analyzer#12552](https://github.com/rust-lang/rust-analyzer/issues/12552) Opening VSCode with RA in a Rust mono repo causes entire system to hang for multiple minutes (closed, 2022-06-16, 3 comments)
- queries: `exception in:title repo:rust-lang/rust-analyzer is:issue`; `references hang repo:rust-lang/rust-analyzer is:issue`; `references exception repo:rust-lang/rust-analyzer is:issue`
