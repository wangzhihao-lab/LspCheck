# [rust-analyzer 2026-09-21] diagnostics: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0`, signature `rust-analyzer|r3_routes|diagnostics:missing:inactive_code`, case family `a`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `googleworkspace/cli@a3768d0e82ad` (corpus, commit a3768d0e82ad83cca2da97724e46bea4ff0e6dbd), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions on the same project: the server's default diagnostics route and the push route; the diagnostics of `crates/google-workspace-cli/src/auth.rs` must be equal.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  536,
  46,
  536,
  47,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  563,
  27,
  569,
  9,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  600,
  27,
  608,
  9,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  630,
  9,
  630,
  10,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  642,
  72,
  642,
  73,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  664,
  18,
  670,
  9,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  696,
  18,
  701,
  9,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  719,
  18,
  724,
  9,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  735,
  52,
  735,
  53,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  748,
  44,
  748,
  45,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  776,
  18,
  783,
  9,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  814,
  18,
  822,
  9,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives"
 ],
 [
  856,
  9,
  856,
  10,
  4,
  "inacti
... (1823 characters)
```

Actual:

```json
[]
```

Project file `crates/google-workspace-cli/src/auth.rs`:

```
   1 | // Copyright 2026 Google LLC
   2 | //
   3 | // Licensed under the Apache License, Version 2.0 (the "License");
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r3-diagnostics-missing-inactive-code-a-0b07f0/repro.json
```

## Evidence and reduction

- representative 7f3fa823fc51-v02: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects googleworkspace/cli@a3768d0e82ad, sharkdp/hyperfine@0d6ade930afc, timings settled, seeds 1, 2

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
