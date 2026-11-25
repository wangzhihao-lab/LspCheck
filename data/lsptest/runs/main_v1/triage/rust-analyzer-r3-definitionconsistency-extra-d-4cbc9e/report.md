# [rust-analyzer 2026-09-21] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-definitionconsistency-extra-d-4cbc9e`, signature `rust-analyzer|r3_routes|definitionConsistency:extra`, case family `d`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `dani-garcia/vaultwarden@cc67d644f626` (corpus, commit cc67d644f62605cb46f4d16c4a2eed1a861cc8bb), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/api/core/two_factor/duo.rs` at line 8, column 13 (LSP position {line: 7, character: 12}) gives the expected set; didOpen `src/api/admin.rs` and `textDocument/definition` at the reference line 289, column 30 (LSP position {line: 288, character: 29}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/api/mod.rs",
  43,
  9,
  43,
  18
 ]
]
```

Actual:

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
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/route/handler.rs",
  6,
  9,
  6,
  16
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/route/handler.rs",
  187,
  11,
  187,
  15
 ],
 [
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket-0.5.1/src/route/mod.rs",
  0,
  0,
  12,
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
  "~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rocket_codegen-0.5.1/src/lib.rs",
  281,
  0,
  281,
  5
 ],
 [
  "src/api/admin.rs",
  287,
  2,
  287,
  20
 ],
 [
  "src/api/admin.rs",
  288,
  25,
  288,
  34
 ],
 [
  "src/api/mod.rs",
  43,
  9,
  43,
  18
 ]
]
```

Project file `src/api/admin.rs`:

```
 286 | }
     ...
 288 | #[get("/", rank = 2)]
 289 | fn admin_page_login() -> ApiResult<Html<String>> {
 290 |     render_admin_login(None, None)
 291 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-definitionconsistency-extra-d-4cbc9e/repro.json
```

## Evidence and reduction

- representative ec5d10b1f270-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects dani-garcia/vaultwarden@cc67d644f626, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#8373](https://github.com/rust-lang/rust-analyzer/issues/8373) Monomorphised go to definition (open, 2021-04-06, 1 comments)
- [rust-lang/rust-analyzer#17122](https://github.com/rust-lang/rust-analyzer/issues/17122) Go to Definition on Private Symbols (open, 2024-04-22, 2 comments)
- [rust-lang/rust-analyzer#22482](https://github.com/rust-lang/rust-analyzer/issues/22482) Panics with "invalid offset" errors ( code: -32603) on "Go to definition" calls (open, 2026-05-28, 4 comments)
- [rust-lang/rust-analyzer#14428](https://github.com/rust-lang/rust-analyzer/issues/14428) Go to definition on std types locks rustc (open, 2023-03-28, 2 comments)
- [rust-lang/rust-analyzer#10700](https://github.com/rust-lang/rust-analyzer/issues/10700) [Feature Request] Go to Definition from the comments (open, 2021-11-05, 1 comments)
- [rust-lang/rust-analyzer#23302](https://github.com/rust-lang/rust-analyzer/issues/23302) When only showing errors/warnings/messages for the current file, sometimes messages are cryptic when split between files (open, 2026-09-07, 1 comments)
- [rust-lang/rust-analyzer#13938](https://github.com/rust-lang/rust-analyzer/issues/13938) Symbol search for symbol in dependency (open, 2023-01-13, 13 comments)
- [rust-lang/rust-analyzer#11019](https://github.com/rust-lang/rust-analyzer/issues/11019) Feature request: “Create file” assist for `include` macro family (open, 2021-12-15, 4 comments)
- queries: `"go to definition" in:title repo:rust-lang/rust-analyzer is:issue`; `definition extra repo:rust-lang/rust-analyzer is:issue`; `definition "go to definition" repo:rust-lang/rust-analyzer is:issue`; `definition inconsistent repo:rust-lang/rust-analyzer is:issue`

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: 2026-09-25T16:39:14.331917-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: |
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: | |_____^
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-baseline-20260925-163846-a69316] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: 2026-09-25T16:40:11.308991-07:00 ERROR FetchBuildDataError: error: You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: --> build.rs:12:5
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: |
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: 12 | /     compile_error!(
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: 13 | |         "You need to enable one DB backend. To build with previous defaults do: cargo build --features sqlite"
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: 14 | |     );
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: | |_____^
[rust-analyzer-2026-09-21-tr4cbc9e-r3-replay-control-20260925-163942-029959] stderr: error: could not compile `vaultwarden` (build script) due to 1 previous error
```
