# [rust-analyzer 2026-09-21] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-definitionconsistency-missing-d-586fd8`, signature `rust-analyzer|r3_routes|definitionConsistency:missing`, case family `d`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `dani-garcia/vaultwarden@cc67d644f626` (corpus, commit cc67d644f62605cb46f4d16c4a2eed1a861cc8bb), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/api/core/two_factor/duo.rs` at line 197, column 81 (LSP position {line: 196, character: 80}) gives the expected set; didOpen `src/api/admin.rs` and `textDocument/definition` at the reference line 309, column 53 (LSP position {line: 308, character: 52}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/lib.rs",
  0,
  0,
  364,
  0
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/log.rs",
  0,
  0,
  245,
  0
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/log.rs",
  34,
  24,
  34,
  29
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/outcome.rs",
  0,
  0,
  867,
  0
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/outcome.rs",
  104,
  9,
  104,
  16
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/outcome.rs",
  106,
  4,
  106,
  11
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/outcome.rs",
  108,
  4,
  108,
  9
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/outcome.rs",
  110,
  4,
  110,
  11
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/request/from_request.rs",
  372,
  10,
  372,
  21
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/request/mod.rs",
  0,
  0,
  113,
  0
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/sentinel.rs",
  0,
  0,
  487,
  0
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/sentinel.rs",
  394,
  13,
  394,
  20
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket_codegen-0.
... (2183 characters)
```

Actual:

```json
[
 [
  "src/db/mod.rs",
  122,
  11,
  122,
  17
 ]
]
```

Project file `src/api/admin.rs`:

```
 307 | #[post("/invite", format = "application/json", data = "<data>")]
 308 | async fn invite_user(data: Json<InviteData>, _token: AdminToken, conn: DbConn) -> JsonResult {
 309 |     async fn generate_invite(user: &User, conn: &DbConn) -> EmptyResult {
 310 |         if CONFIG.mail_enabled() {
 311 |             let org_id: OrganizationId = if CONFIG.sso_enabled() {
 312 |                 FAKE_SSO_IDENTIFIER.into()
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-definitionconsistency-missing-d-586fd8/repro.json
```

## Evidence and reduction

- representative ec5d10b1f270-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects dani-garcia/vaultwarden@cc67d644f626, timings settled, seeds 1

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

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: 2026-09-25T16:46:45.057139-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: |
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: | |_____^
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-baseline-20260925-164615-8d3725] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: 2026-09-25T16:47:47.055241-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: |
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: | |_____^
[rust-analyzer-2026-09-21-tr586fd8-r3-replay-control-20260925-164718-02fffd] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
```
