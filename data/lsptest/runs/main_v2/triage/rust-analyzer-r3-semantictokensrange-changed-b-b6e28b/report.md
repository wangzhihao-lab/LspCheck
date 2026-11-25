# [rust-analyzer 2026-09-21] semanticTokensRange: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-semantictokensrange-changed-b-b6e28b`, signature `rust-analyzer|r3_routes|semanticTokensRange:changed`, case family `b`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `googleworkspace/cli@a3768d0e82ad` (corpus, commit a3768d0e82ad83cca2da97724e46bea4ff0e6dbd), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/semanticTokens/full` on `crates/google-workspace-cli/src/auth.rs`, then `textDocument/semanticTokens/range` over [563, 15, 567, 13]; the range answer must equal the full answer restricted to that range.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  563,
  17,
  1,
  "operator",
  "macro,procMacro"
 ],
 [
  563,
  18,
  6,
  "method",
  "consuming,defaultLibrary,library,macro,procMacro"
 ],
 [
  564,
  12,
  10,
  "enum",
  "macro,procMacro"
 ],
 [
  564,
  22,
  2,
  "operator",
  "macro,procMacro"
 ],
 [
  564,
  24,
  14,
  "enumMember",
  "macro,procMacro"
 ],
 [
  564,
  39,
  6,
  "variable",
  "declaration,macro,procMacro"
 ],
 [
  564,
  47,
  2,
  "operator",
  "macro,procMacro"
 ],
 [
  565,
  16,
  9,
  "macro",
  "defaultLibrary,library,macro,procMacro"
 ],
 [
  565,
  25,
  1,
  "macro",
  "macro,procMacro"
 ],
 [
  565,
  27,
  6,
  "variable",
  "macro"
 ],
 [
  565,
  33,
  1,
  "operator",
  "macro,procMacro"
 ],
 [
  565,
  34,
  9,
  "property",
  "library,macro"
 ],
 [
  565,
  45,
  8,
  "string",
  "macro"
 ],
 [
  566,
  16,
  9,
  "macro",
  "defaultLibrary,library,macro,procMacro"
 ],
 [
  566,
  25,
  1,
  "macro",
  "macro,procMacro"
 ],
 [
  566,
  27,
  6,
  "variable",
  "macro"
 ],
 [
  566,
  33,
  1,
  "operator",
  "macro,procMacro"
 ],
 [
  566,
  34,
  13,
  "property",
  "library,macro"
 ],
 [
  566,
  49,
  13,
  "string",
  "macro"
 ]
]
```

Actual:

```json
[
 [
  563,
  17,
  1,
  "operator",
  ""
 ],
 [
  563,
  18,
  6,
  "unresolvedReference",
  ""
 ],
 [
  564,
  12,
  10,
  "enum",
  ""
 ],
 [
  564,
  22,
  2,
  "operator",
  ""
 ],
 [
  564,
  24,
  14,
  "enumMember",
  ""
 ],
 [
  564,
  39,
  6,
  "variable",
  "declaration"
 ],
 [
  564,
  47,
  2,
  "operator",
  ""
 ],
 [
  565,
  16,
  9,
  "macro",
  "defaultLibrary,library"
 ],
 [
  565,
  25,
  1,
  "macro",
  ""
 ],
 [
  565,
  27,
  6,
  "variable",
  "macro"
 ],
 [
  565,
  33,
  1,
  "operator",
  "macro,procMacro"
 ],
 [
  565,
  34,
  9,
  "property",
  "library,macro"
 ],
 [
  565,
  45,
  8,
  "string",
  "macro"
 ],
 [
  566,
  16,
  9,
  "macro",
  "defaultLibrary,library"
 ],
 [
  566,
  25,
  1,
  "macro",
  ""
 ],
 [
  566,
  27,
  6,
  "variable",
  "macro"
 ],
 [
  566,
  33,
  1,
  "operator",
  "macro,procMacro"
 ],
 [
  566,
  34,
  13,
  "property",
  "library,macro"
 ],
 [
  566,
  49,
  13,
  "string",
  "macro"
 ]
]
```

Project file `crates/google-workspace-cli/src/auth.rs`:

```
 561 |         )
 562 |         .await;
     ...
 564 |         match res.unwrap() {
 565 |             Credential::AuthorizedUser(secret) => {
 566 |                 assert_eq!(secret.client_id, "adc_id");
 567 |                 assert_eq!(secret.refresh_token, "adc_refresh");
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r3-semantictokensrange-changed-b-b6e28b/repro.json
```

## Evidence and reduction

- representative 7f3fa823fc51-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects googleworkspace/cli@a3768d0e82ad, h4ckf0r0day/obscura@0e17221dbb55, tokio-rs/tokio@3930bd182cb1, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#23199](https://github.com/rust-lang/rust-analyzer/issues/23199) Wrong range when request at edited std (open, 2026-08-20, 7 comments)
- [rust-lang/rust-analyzer#23124](https://github.com/rust-lang/rust-analyzer/issues/23124) panic: highlight: `type parameter `#1` (#1/1) out of range when instantiating, args=[#0]` (open, 2026-08-11, 0 comments)
- [rust-lang/rust-analyzer#12640](https://github.com/rust-lang/rust-analyzer/issues/12640) Feature request: lifetime range visualizations (open, 2022-06-26, 1 comments)
- [rust-lang/rust-analyzer#16535](https://github.com/rust-lang/rust-analyzer/issues/16535) Hover range breaks within attribute macros (open, 2024-02-12, 0 comments)
- [rust-lang/rust-analyzer#13931](https://github.com/rust-lang/rust-analyzer/issues/13931) Range hover inside macro is wrong (open, 2023-01-11, 0 comments)
- [rust-lang/rust-analyzer#15737](https://github.com/rust-lang/rust-analyzer/issues/15737) work node crashes (closed, 2023-10-09, 1 comments)
- [rust-lang/rust-analyzer#9601](https://github.com/rust-lang/rust-analyzer/issues/9601) GTK3 on Windows 10: Type hinting but no type checking? (closed, 2021-07-14, 16 comments)
- [rust-lang/rust-analyzer#7416](https://github.com/rust-lang/rust-analyzer/issues/7416) Support in band lifetimes (closed, 2021-01-24, 5 comments)
- queries: `range in:title repo:rust-lang/rust-analyzer is:issue`; `"semantic tokens range" wrong repo:rust-lang/rust-analyzer is:issue`; `"semantic tokens range" range repo:rust-lang/rust-analyzer is:issue`; `"semantic tokens range" inconsistent repo:rust-lang/rust-analyzer is:issue`
