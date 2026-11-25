# [rust-analyzer 2026-09-21] diagnostics: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-diagnostics-extra-non-snake-case-a-52ba0b`, signature `rust-analyzer|r3_routes|diagnostics:extra:non_snake_case`, case family `a`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `BurntSushi/ripgrep@3fce3b5bb023` (corpus, commit 3fce3b5bb0236da2df6d99672afb8a719642eca7), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions on the same project: the server's default diagnostics route and the push route; the diagnostics of `crates/searcher/examples/search-stdin.rs` must be equal.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  19,
  8,
  19,
  12,
  2,
  "non_snake_case",
  "rust-analyzer",
  "Variable `None` should have snake_case name, e.g. `none`"
 ]
]
```

Project file `crates/searcher/examples/search-stdin.rs`:

```
   1 | use std::env;
   2 | use std::error::Error;
   3 | use std::io;
   4 | use std::process;
     ...
   6 | use grep_regex::RegexMatcher;
   7 | use grep_searcher::Searcher;
   8 | use grep_searcher::sinks::UTF8;
     ...
  10 | fn main() {
  11 |     if let Err(err) = example() {
  12 |         eprintln!("{}", err);
  13 |         process::exit(1);
  14 |     }
  15 | }
     ...
  17 | fn example() -> Result<(), Box<dyn Error>> {
  18 |     let pattern = match env::args().nth(1) {
  19 |         Some(pattern) => pattern,
  20 |         None => {
  21 |             return Err(From::from(format!("Usage: search-stdin <pattern>")));
  22 |         }
  23 |     };
  24 |     let matcher = RegexMatcher::new(&pattern)?;
  25 |     Searcher::new().search_reader(
  26 |         &matcher,
  27 |         io::stdin(),
  28 |         UTF8(|lnum, line| {
  29 |             print!("{}:{}", lnum, line);
  30 |             Ok(true)
  31 |         }),
  32 |     )?;
  33 |     Ok(())
  34 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-diagnostics-extra-non-snake-case-a-52ba0b/repro.json
```

## Evidence and reduction

- representative 29d2893b9177-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 0/3)
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects BurntSushi/ripgrep@3fce3b5bb023, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#18375](https://github.com/rust-lang/rust-analyzer/issues/18375) Implement the LSP diagnostics pull model (closed, 2024-10-23, 0 comments)
- [rust-lang/rust-analyzer#23193](https://github.com/rust-lang/rust-analyzer/issues/23193) FP `expected &&&u32, found &&&&&&&&&&&&&&&&&&&&&&&&&i32` (open, 2026-08-19, 5 comments)
- [rust-lang/rust-analyzer#13317](https://github.com/rust-lang/rust-analyzer/issues/13317) Runnables: Extra Args sets Args instead of Extra Args (open, 2022-09-30, 0 comments)
- [rust-lang/rust-analyzer#19491](https://github.com/rust-lang/rust-analyzer/issues/19491) Too many arguments generates two diagnostics (open, 2025-04-01, 13 comments)
- [rust-lang/rust-analyzer#22828](https://github.com/rust-lang/rust-analyzer/issues/22828) panic: `can't project out of` (open, 2026-07-16, 6 comments)
- [rust-lang/rust-analyzer#21662](https://github.com/rust-lang/rust-analyzer/issues/21662) Documentation hint discrepency between autocomplete and inner function (open, 2026-02-17, 2 comments)
- [rust-lang/rust-analyzer#18709](https://github.com/rust-lang/rust-analyzer/issues/18709) rust-analyzer didn't return warning/hint diagnostics on `textDocument/diagnostic` (open, 2024-12-18, 11 comments)
- [rust-lang/rust-analyzer#18732](https://github.com/rust-lang/rust-analyzer/issues/18732) stale diagnostic after panic (open, 2024-12-21, 6 comments)
- queries: `"pull diagnostics" in:title repo:rust-lang/rust-analyzer is:issue`; `diagnostics extra repo:rust-lang/rust-analyzer is:issue`; `diagnostics "pull diagnostics" repo:rust-lang/rust-analyzer is:issue`; `diagnostics inconsistent repo:rust-lang/rust-analyzer is:issue`
