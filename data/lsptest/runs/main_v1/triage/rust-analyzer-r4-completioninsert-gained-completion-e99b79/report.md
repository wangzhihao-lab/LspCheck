# [rust-analyzer 2026-09-21] completion edit is not valid (completionInsert:gained)

Draft for the author (not filed). Group `rust-analyzer-r4-completioninsert-gained-completion-e99b79`, signature `rust-analyzer|r4_edits|completionInsert:gained`, case family `completion`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `dani-garcia/vaultwarden@cc67d644f626` (corpus, commit cc67d644f62605cb46f4d16c4a2eed1a861cc8bb), language rust

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/completion` on `src/api/core/organizations.rs` at line 315, column 12 (LSP position {line: 314, character: 11}); insert the item: the file must not gain a syntax error.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "expected one of `.`, `;`, `?`, `}`, or an operator, found `!`"
]
```

Project file `src/api/core/organizations.rs`:

```
 312 |     conn: DbConn,
 313 | ) -> JsonResult {
 314 |     if org_id != headers.org_id {
 315 |         err!("Organization not found", "Organization id's do not match");
 316 |     }
     ...
 318 |     let data: OrganizationUpdateData = data.into_inner();
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r4-completioninsert-gained-completion-e99b79/repro.json
```

## Evidence and reduction

- representative 1d56fa44ae9e-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects BurntSushi/ripgrep@3fce3b5bb023, alacritty/alacritty@d692748d3f61, dani-garcia/vaultwarden@cc67d644f626, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- none found
- queries: `completionInsert unexpected repo:rust-lang/rust-analyzer is:issue`; `completionInsert "wrong edit" repo:rust-lang/rust-analyzer is:issue`

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: 2026-09-25T17:20:33.822169-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: |
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: | |_____^
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20260925-172005-40ceaf] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: 2026-09-25T17:21:33.341773-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: |
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: | |_____^
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20260925-172105-d13d16] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
```
