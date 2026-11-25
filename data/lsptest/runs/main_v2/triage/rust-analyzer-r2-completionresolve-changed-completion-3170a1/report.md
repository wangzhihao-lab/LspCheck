# [rust-analyzer 2026-09-21] a stale completion handle resolves to a different edit after an intervening edit

Draft for the author (not filed). Group `rust-analyzer-r2-completionresolve-changed-completion-3170a1`, signature `rust-analyzer|r2_handles|completionResolve:changed`, case family `completion`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `googleworkspace/cli@a3768d0e82ad` (corpus, commit a3768d0e82ad83cca2da97724e46bea4ff0e6dbd), language rust

## Relation violated

Handle validity (R2): a code-action or completion handle minted before an edit and resolved after it must fail, return no edit, or return the same edit as a fresh handle for the same item.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. didOpen `crates/google-workspace-cli/src/auth.rs`; request completion items at line 407, column 62 (LSP position {line: 406, character: 61}) and resolve them; didChange: insert `"\n\n"` at line 1 (top); wait until idle; resolve the OLD completion item `None`; request and resolve a fresh one at the mapped position: the old handle must fail, give no edit, or give the fresh handle's edit.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "textEdit",
  408,
  53,
  408,
  61,
  "None$0"
 ]
]
```

Actual:

```json
[
 [
  "textEdit",
  407,
  0,
  406,
  61,
  "None$0"
 ]
]
```

Project file `crates/google-workspace-cli/src/auth.rs`:

```
   1 | // Copyright 2026 Google LLC
   2 | //
   3 | // Licensed under the Apache License, Version 2.0 (the "License");
   4 | // you may not use this file except in compliance with the License.
     ...
 404 |     if let Ok(adc_env) = std::env::var("GOOGLE_APPLICATION_CREDENTIALS") {
 405 |         let adc_path = PathBuf::from(&adc_env);
 406 |         if adc_path.exists() {
 407 |             let content = tokio::fs::read_to_string(&adc_path)
 408 |                 .await
 409 |                 .with_context(|| format!("Failed to read ADC from {adc_env}"))?;
 410 |             return parse_credential_file(&adc_path, &content).await;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r2-completionresolve-changed-completion-3170a1/repro.json
```

## Evidence and reduction

- representative 06365021d85d-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects casey/just@6119e6aff518, googleworkspace/cli@a3768d0e82ad, iced-rs/iced@0ef42477fb6f, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#16240](https://github.com/rust-lang/rust-analyzer/issues/16240) No autocompletion for `inherent_associated_types` nightly feature (open, 2024-01-03, 5 comments)
- [rust-lang/rust-analyzer#18363](https://github.com/rust-lang/rust-analyzer/issues/18363) Auto-imports not working in Kate (closed, 2024-10-21, 12 comments)
- [rust-lang/rust-analyzer#18547](https://github.com/rust-lang/rust-analyzer/issues/18547) Autocomplete suggestion changes to something random once selected (closed, 2024-11-23, 18 comments)
- [rust-lang/rust-analyzer#18504](https://github.com/rust-lang/rust-analyzer/issues/18504) No signatures shown in completion popup (closed, 2024-11-11, 6 comments)
- [rust-lang/rust-analyzer#13786](https://github.com/rust-lang/rust-analyzer/issues/13786) Borrow/BorrowMut auto importing completions are confusing for newcomers (closed, 2022-12-16, 4 comments)
- [rust-lang/rust-analyzer#22442](https://github.com/rust-lang/rust-analyzer/issues/22442) auto-import macro fails when exclamation mark is present (open, 2026-05-24, 22 comments)
- queries: `"completion resolve" wrong repo:rust-lang/rust-analyzer is:issue`; `"completion resolve" stale repo:rust-lang/rust-analyzer is:issue`
