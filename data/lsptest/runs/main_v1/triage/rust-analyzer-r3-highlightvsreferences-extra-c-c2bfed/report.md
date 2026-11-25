# [rust-analyzer 2026-09-21] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-highlightvsreferences-extra-c-c2bfed`, signature `rust-analyzer|r3_routes|highlightVsReferences:extra`, case family `c`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `BurntSushi/ripgrep@3fce3b5bb023` (corpus, commit 3fce3b5bb0236da2df6d99672afb8a719642eca7), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `crates/matcher/tests/util.rs` at line 4, column 40 (LSP position {line: 3, character: 39}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  3,
  36,
  3,
  43
 ],
 [
  27,
  5,
  27,
  12
 ],
 [
  68,
  5,
  68,
  12
 ]
]
```

Actual:

```json
[
 [
  3,
  36,
  3,
  43
 ],
 [
  27,
  5,
  27,
  12
 ],
 [
  28,
  9,
  28,
  17
 ],
 [
  29,
  9,
  29,
  14
 ],
 [
  31,
  7,
  31,
  14
 ],
 [
  38,
  7,
  38,
  19
 ],
 [
  42,
  7,
  42,
  18
 ],
 [
  51,
  7,
  51,
  20
 ],
 [
  55,
  7,
  55,
  20
 ],
 [
  68,
  5,
  68,
  12
 ],
 [
  69,
  9,
  69,
  17
 ],
 [
  70,
  9,
  70,
  14
 ],
 [
  72,
  7,
  72,
  14
 ],
 [
  79,
  7,
  79,
  19
 ]
]
```

Project file `crates/matcher/tests/util.rs`:

```
   1 | use std::collections::HashMap;
     ...
   3 | use {
   4 |     grep_matcher::{Captures, Match, Matcher, NoCaptures, NoError},
   5 |     regex::bytes::{CaptureLocations, Regex},
   6 | };
     ...
   8 | #[derive(Debug)]
   9 | pub(crate) struct RegexMatcher {
  10 |     pub re: Regex,
  11 |     pub names: HashMap<String, usize>,
  12 | }
     ...
  14 | impl RegexMatcher {
  15 |     pub(crate) fn new(re: Regex) -> RegexMatcher {
  16 |         let mut names = HashMap::new();
  17 |         for (i, optional_name) in re.capture_names().enumerate() {
  18 |             if let Some(name) = optional_name {
  19 |                 names.insert(name.to_string(), i);
  20 |             }
  21 |         }
  22 |         RegexMatcher { re, names }
  23 |     }
  24 | }
     ...
  26 | type Result<T> = std::result::Result<T, NoError>;
     ...
  28 | impl Matcher for RegexMatcher {
  29 |     type Captures = RegexCaptures;
  30 |     type Error = NoError;
     ...
  32 |     fn find_at(&self, haystack: &[u8], at: usize) -> Result<Option<Match>> {
  33 |         Ok(self
  34 |             .re
  35 |             .find_at(haystack, at)
  36 |             .map(|m| Match::new(m.start(), m.end())))
  37 |     }
     ...
  39 |     fn new_captures(&self) -> Result<RegexCaptures> {
  40 |         Ok(RegexCaptures(self.re.capture_locations()))
  41 |     }
     ...
  43 |     fn captures_at(
  44 |         &self,
  45 |         haystack: &[u8],
  46 |         at: usize,
  47 |         caps: &mut RegexCaptures,
  48 |     ) -> Result<bool> {
  49 |         Ok(self.re.captures_read_at(&mut caps.0, haystack, at).is_some())
  50 |     }
     ...
  52 |     fn capture_count(&self) -> usize {
  53 |         self.re.captures_len()
  54 |     }
     ...
  56 |     fn capture_index(&self, name: &str) -> Option<usize> {
  57 |         self.names.get(name).copied()
  58 |     }
     ...
  60 |     // We purposely don't implement any other methods, so that we test the
  61 |     // default impls. The "real" Regex impl for Matcher provides a few more
  62 |     // impls. e.g., Its `find_iter` impl is faster than what we can do here,
  63 |     // since the regex crate avoids synchronization overhead.
  64 | }
     ...
  66 | #[derive(Debug)]
  67 | pub(crate) struct RegexMatcherNoCaps(pub(crate) Regex);
     ...
  69 | impl Matcher for RegexMatcherNoCaps {
  70 |     type Captures = NoCaptures;
  71 |     type Error = NoError;
     ...
  73 |     fn find_at(&self, haystack: &[u8], at: usize) -> Result<Option<Match>> {
  74 |         Ok(self
  75 |             .0
  76 |             .find_at(haystack, at)
  77 |             .map(|m| Match::new(m.start(), m.end())))
  78 |     }
     ...
  80 |     fn new_captures(&self) -> Result<NoCaptures> {
  81 |         Ok(NoCaptures::new())
  82 |     }
  83 | }
     ...
  85 | #[derive(Clone, Debug)]
  86 | pub(crate) struct RegexCaptures(CaptureLocations);
     ...
  88 | impl Captures for RegexCaptures {
  89 |     fn len(&self) -> usize {
  90 |         self.0.len()
  91 |     }
     ...
  93 |     fn get(&self, i: usize) -> Option<Match> {
  94 |         self.0.pos(i).map(|(s, e)| Match::new(s, e))
  95 |     }
  96 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-highlightvsreferences-extra-c-c2bfed/repro.json
```

## Evidence and reduction

- representative 227b8c64b999-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects BurntSushi/ripgrep@3fce3b5bb023, rust-lang/rustlings@a650509c789d, sharkdp/bat@4987f76709aa, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#18703](https://github.com/rust-lang/rust-analyzer/issues/18703) Rename should affect references in doc comments (open, 2024-12-16, 4 comments)
- [rust-lang/rust-analyzer#13755](https://github.com/rust-lang/rust-analyzer/issues/13755) references displayed inline can be confusing wrt compiler errors due to missing references (open, 2022-12-10, 1 comments)
- [rust-lang/rust-analyzer#17887](https://github.com/rust-lang/rust-analyzer/issues/17887) "Rename" for references in HRTB (open, 2024-08-14, 3 comments)
- [rust-lang/rust-analyzer#15243](https://github.com/rust-lang/rust-analyzer/issues/15243) fails to resolve nested `prelude::*` references (open, 2023-07-09, 0 comments)
- [rust-lang/rust-analyzer#12182](https://github.com/rust-lang/rust-analyzer/issues/12182) "overflow depth reached" on find all references. (open, 2022-05-06, 2 comments)
- [rust-lang/rust-analyzer#7379](https://github.com/rust-lang/rust-analyzer/issues/7379) Lint option: Highlighting copies (open, 2021-01-21, 3 comments)
- [rust-lang/rust-analyzer#10500](https://github.com/rust-lang/rust-analyzer/issues/10500) Add infrastructure to narrow down diagnostic ranges  (open, 2021-10-09, 0 comments)
- [rust-lang/rust-analyzer#4170](https://github.com/rust-lang/rust-analyzer/issues/4170) Treat doctests as rust code (open, 2020-04-27, 25 comments)
- queries: `references in:title repo:rust-lang/rust-analyzer is:issue`; `highlight extra repo:rust-lang/rust-analyzer is:issue`; `highlight references repo:rust-lang/rust-analyzer is:issue`; `highlight inconsistent repo:rust-lang/rust-analyzer is:issue`
