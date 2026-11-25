# [rust-analyzer 2026-09-21] definitionConsistency: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-definitionconsistency-changed-d-2c6179`, signature `rust-analyzer|r3_routes|definitionConsistency:changed`, case family `d`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `rust-lang/rustlings@a650509c789d` (corpus, commit a650509c789da1656f813392b16aa1fa043b7f3e), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/definition` on `src/exercise.rs` at line 122, column 42 (LSP position {line: 121, character: 41}) gives the expected set; didOpen `src/exercise.rs` and `textDocument/definition` at the reference line 244, column 18 (LSP position {line: 243, character: 17}) must give the same set.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "src/exercise.rs",
  103,
  7,
  103,
  27
 ]
]
```

Actual:

```json
[
 [
  "src/exercise.rs",
  243,
  7,
  243,
  27
 ]
]
```

Project file `src/exercise.rs`:

```
 241 |         self.test
 242 |     }
     ...
 244 |     fn embedded_input_files(&self) -> &[InputFile] {
 245 |         self.embedded_input_files
 246 |     }
 247 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-definitionconsistency-changed-d-2c6179/repro.json
```

## Evidence and reduction

- representative 27d79bab3edd-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects dani-garcia/vaultwarden@cc67d644f626, rust-lang/rustlings@a650509c789d, sxyazi/yazi@0ea4c5d9ef75, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#8373](https://github.com/rust-lang/rust-analyzer/issues/8373) Monomorphised go to definition (open, 2021-04-06, 1 comments)
- [rust-lang/rust-analyzer#17122](https://github.com/rust-lang/rust-analyzer/issues/17122) Go to Definition on Private Symbols (open, 2024-04-22, 2 comments)
- [rust-lang/rust-analyzer#22482](https://github.com/rust-lang/rust-analyzer/issues/22482) Panics with "invalid offset" errors ( code: -32603) on "Go to definition" calls (open, 2026-05-28, 4 comments)
- [rust-lang/rust-analyzer#14428](https://github.com/rust-lang/rust-analyzer/issues/14428) Go to definition on std types locks rustc (open, 2023-03-28, 2 comments)
- [rust-lang/rust-analyzer#10700](https://github.com/rust-lang/rust-analyzer/issues/10700) [Feature Request] Go to Definition from the comments (open, 2021-11-05, 1 comments)
- [rust-lang/rust-analyzer#15757](https://github.com/rust-lang/rust-analyzer/issues/15757) rust-analyzer finds wrong macro definition (open, 2023-10-14, 1 comments)
- [rust-lang/rust-analyzer#18248](https://github.com/rust-lang/rust-analyzer/issues/18248) no definition found for method, but definition location can be identified when params is wrong (open, 2024-10-06, 6 comments)
- [rust-lang/rust-analyzer#11834](https://github.com/rust-lang/rust-analyzer/issues/11834) Failed to "Run Test": run Cargo from wrong folder (open, 2022-03-28, 0 comments)
- queries: `"go to definition" in:title repo:rust-lang/rust-analyzer is:issue`; `definition wrong repo:rust-lang/rust-analyzer is:issue`; `definition "go to definition" repo:rust-lang/rust-analyzer is:issue`; `definition inconsistent repo:rust-lang/rust-analyzer is:issue`
