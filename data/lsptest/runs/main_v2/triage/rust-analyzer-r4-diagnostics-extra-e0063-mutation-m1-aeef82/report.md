# [rust-analyzer 2026-09-21] mutation:M1 edit is not valid (diagnostics:extra:E0063)

Draft for the author (not filed). Group `rust-analyzer-r4-diagnostics-extra-e0063-mutation-m1-aeef82`, signature `rust-analyzer|r4_edits|diagnostics:extra:E0063`, case family `mutation:M1`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `googleworkspace/cli@a3768d0e82ad` (corpus, commit a3768d0e82ad83cca2da97724e46bea4ff0e6dbd), language rust

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open crates/google-workspace-cli/src/helpers/chat.rs`
3. textDocument/didChange: `change crates/google-workspace-cli/src/helpers/chat.rs (18, 16)-(18, 28) ""`
4. textDocument/didChange: `change crates/google-workspace-cli/src/helpers/chat.rs (183, 13)-(183, 13) ".to_owned()"`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `crates/google-workspace-cli/src/helpers/events/mod.rs`, `crates/google-workspace-cli/src/main.rs` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `crates/google-workspace-cli/src/helpers/chat.rs` line 184, column 9 (LSP position {line: 183, character: 8}) (M1:quickfix-errors:Add .to_owned() here); compare with the same query in a fresh session on the same content (expected).

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
  0,
  1,
  "E0063",
  "rust-analyzer",
  "missing structure fields: - space"
 ]
]
```

Project file `crates/google-workspace-cli/src/helpers/chat.rs`:

```
  16 | use crate::auth;
  17 | use crate::error::GwsError;
  18 | use crate::executor;
  19 | use clap::{Arg, ArgMatches, Command};
  20 | use serde_json::json;
  21 | use std::future::Future;
  22 | use std::pin::Pin;
     ...
 181 |     crate::validate::validate_resource_name(&space)?;
     ...
 183 |     Ok(SendConfig {
 184 |         space,
 185 |         text: matches.get_one::<String>("text").unwrap().clone(),
 186 |     })
 187 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r4-diagnostics-extra-e0063-mutation-m1-aeef82/repro.json
```

## Evidence and reduction

- representative ebf6989f5480-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 24.735 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects googleworkspace/cli@a3768d0e82ad, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#23193](https://github.com/rust-lang/rust-analyzer/issues/23193) FP `expected &&&u32, found &&&&&&&&&&&&&&&&&&&&&&&&&i32` (open, 2026-08-19, 5 comments)
- [rust-lang/rust-analyzer#13317](https://github.com/rust-lang/rust-analyzer/issues/13317) Runnables: Extra Args sets Args instead of Extra Args (open, 2022-09-30, 0 comments)
- [rust-lang/rust-analyzer#19491](https://github.com/rust-lang/rust-analyzer/issues/19491) Too many arguments generates two diagnostics (open, 2025-04-01, 13 comments)
- [rust-lang/rust-analyzer#22828](https://github.com/rust-lang/rust-analyzer/issues/22828) panic: `can't project out of` (open, 2026-07-16, 6 comments)
- [rust-lang/rust-analyzer#21662](https://github.com/rust-lang/rust-analyzer/issues/21662) Documentation hint discrepency between autocomplete and inner function (open, 2026-02-17, 2 comments)
- [rust-lang/rust-analyzer#23199](https://github.com/rust-lang/rust-analyzer/issues/23199) Wrong range when request at edited std (open, 2026-08-20, 7 comments)
- [rust-lang/rust-analyzer#17289](https://github.com/rust-lang/rust-analyzer/issues/17289) Invalid offset -32603 when editing an empty .rs file (open, 2024-05-24, 68 comments)
- [rust-lang/rust-analyzer#15873](https://github.com/rust-lang/rust-analyzer/issues/15873) stack overflow in `ra_ap_hir_ty::mir::borrowck::ever_initialized_map::dfs` on the `idna` crate (closed, 2023-11-11, 5 comments)
- queries: `diagnostics extra repo:rust-lang/rust-analyzer is:issue`; `diagnostics "wrong edit" repo:rust-lang/rust-analyzer is:issue`
