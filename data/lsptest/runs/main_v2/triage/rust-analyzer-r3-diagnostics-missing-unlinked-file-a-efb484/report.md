# [rust-analyzer 2026-09-21] diagnostics: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-diagnostics-missing-unlinked-file-a-efb484`, signature `rust-analyzer|r3_routes|diagnostics:missing:unlinked-file`, case family `a`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `yewstack/yew@bfa6c19af971` (corpus, commit bfa6c19af971084f9547495388bde9aceeb81aaa), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions on the same project: the server's default diagnostics route and the push route; the diagnostics of `packages/yew-macro/tests/classes_macro/classes-fail.rs` must be equal.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  0,
  0,
  0,
  2,
  4,
  "unlinked-file",
  "rust-analyzer",
  "This file is not included in any crates, so rust-analyzer can't offer IDE services. If you're intentionally working on unowned files, you can silence this warning by adding \"unlinked-file\" to rust-analyzer.diagnostics.disabled in your settings."
 ]
]
```

Actual:

```json
[]
```

Project file `packages/yew-macro/tests/classes_macro/classes-fail.rs`:

```
   1 | use yew::prelude::*;
     ...
   3 | fn compile_pass() {
   4 |     classes!(42);
   5 |     classes!(42.0);
     ...
   7 |     classes!("one" "two");
     ...
   9 |     classes!(vec![42]);
     ...
  11 |     let some = Some(42);
  12 |     let none: Option<u32> = None;
  13 |     classes!(some);
  14 |     classes!(none);
     ...
  16 |     classes!("one", 42);
     ...
  18 |     classes!("one", "two three", "four");
  19 | }
     ...
  21 | fn main() {}
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r3-diagnostics-missing-unlinked-file-a-efb484/repro.json
```

## Evidence and reduction

- representative 123013a0b0a6-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects yewstack/yew@bfa6c19af971, timings settled, seeds 2

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

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-trefb484-r3-replay-baseline-20261119-010736-f3d7c9] stderr: 2026-11-19T01:07:38.434863-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crat
[rust-analyzer-2026-09-21-trefb484-r3-replay-baseline-20261119-010736-f3d7c9] stderr: 2026-11-19T01:07:38.434878-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-trefb484-r3-replay-baseline-20261119-010736-f3d7c9] stderr: 2026-11-19T01:07:38.434886-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx
[rust-analyzer-2026-09-21-trefb484-r3-replay-baseline-20261119-010736-f3d7c9] stderr: 2026-11-19T01:08:10.475893-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crat
[rust-analyzer-2026-09-21-trefb484-r3-replay-baseline-20261119-010736-f3d7c9] stderr: 2026-11-19T01:08:10.475908-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-trefb484-r3-replay-baseline-20261119-010736-f3d7c9] stderr: 2026-11-19T01:08:10.47593-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx:
[rust-analyzer-2026-09-21-trefb484-r3-replay-control-20261119-010828-a8d5c8] stderr: 2026-11-19T01:08:30.566592-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crate
[rust-analyzer-2026-09-21-trefb484-r3-replay-control-20261119-010828-a8d5c8] stderr: 2026-11-19T01:08:30.566607-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-trefb484-r3-replay-control-20261119-010828-a8d5c8] stderr: 2026-11-19T01:08:30.566616-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx:
[rust-analyzer-2026-09-21-trefb484-r3-replay-control-20261119-010828-a8d5c8] stderr: 2026-11-19T01:09:00.763191-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crate
[rust-analyzer-2026-09-21-trefb484-r3-replay-control-20261119-010828-a8d5c8] stderr: 2026-11-19T01:09:00.763206-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-trefb484-r3-replay-control-20261119-010828-a8d5c8] stderr: 2026-11-19T01:09:00.763228-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx:
[rust-analyzer-2026-09-21-trefb484-r3-replay-route-20261119-010920-f6e924] stderr: 2026-11-19T01:09:23.503102-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<CrateBu
[rust-analyzer-2026-09-21-trefb484-r3-replay-route-20261119-010920-f6e924] stderr: 2026-11-19T01:09:23.503128-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-trefb484-r3-replay-route-20261119-010920-f6e924] stderr: 2026-11-19T01:09:23.503415-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx::<
[rust-analyzer-2026-09-21-trefb484-r3-replay-route-20261119-010920-f6e924] stderr: 2026-11-19T01:10:01.647433-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<CrateBu
[rust-analyzer-2026-09-21-trefb484-r3-replay-route-20261119-010920-f6e924] stderr: 2026-11-19T01:10:01.647448-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-trefb484-r3-replay-route-20261119-010920-f6e924] stderr: 2026-11-19T01:10:01.647463-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx::<
```
