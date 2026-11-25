# [rust-analyzer 2026-09-21] mutation:M1 edit is not valid (syntax:gained)

Draft for the author (not filed). Group `rust-analyzer-r4-syntax-gained-mutation-m1-7af5e4`, signature `rust-analyzer|r4_edits|syntax:gained`, case family `mutation:M1`.

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
8. Query `syntax` on `crates/google-workspace-cli/src/helpers/chat.rs` line 184, column 9 (LSP position {line: 183, character: 8}) (M1:quickfix-syntax:Add .to_owned() here); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "expected one of `,`, `:`, or `}`, found `.`"
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
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r4-syntax-gained-mutation-m1-7af5e4/repro.json
```

## Evidence and reduction

- representative ebf6989f5480-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 31.639 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects googleworkspace/cli@a3768d0e82ad, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#18673](https://github.com/rust-lang/rust-analyzer/issues/18673) Unexpected type for `Struct` constructor: `AssocTypeId` (open, 2024-12-12, 1 comments)
- [rust-lang/rust-analyzer#18211](https://github.com/rust-lang/rust-analyzer/issues/18211) Support macro None groupings (open, 2024-09-30, 4 comments)
- [rust-lang/rust-analyzer#19782](https://github.com/rust-lang/rust-analyzer/issues/19782) rust-analyzer should not emit macro-errors when macro input contains an unclosed delimiter (open, 2025-05-12, 1 comments)
- [rust-lang/rust-analyzer#20024](https://github.com/rust-lang/rust-analyzer/issues/20024) `Semantics::attach_first_edition` hangs, possibly due to blocked communication with the `proc-macro-server` process (open, 2025-06-17, 8 comments)
- [rust-lang/rust-analyzer#3186](https://github.com/rust-lang/rust-analyzer/issues/3186) StructuralSearchReplace: next steps (open, 2020-02-17, 35 comments)
- [rust-lang/rust-analyzer#17289](https://github.com/rust-lang/rust-analyzer/issues/17289) Invalid offset -32603 when editing an empty .rs file (open, 2024-05-24, 68 comments)
- [rust-lang/rust-analyzer#15873](https://github.com/rust-lang/rust-analyzer/issues/15873) stack overflow in `ra_ap_hir_ty::mir::borrowck::ever_initialized_map::dfs` on the `idna` crate (closed, 2023-11-11, 5 comments)
- [rust-lang/rust-analyzer#11260](https://github.com/rust-lang/rust-analyzer/issues/11260) Support format_args_capture (closed, 2022-01-11, 27 comments)
- queries: `syntax unexpected repo:rust-lang/rust-analyzer is:issue`; `syntax "wrong edit" repo:rust-lang/rust-analyzer is:issue`
