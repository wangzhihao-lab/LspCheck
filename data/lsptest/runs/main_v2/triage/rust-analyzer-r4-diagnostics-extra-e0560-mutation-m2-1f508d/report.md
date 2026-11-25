# [rust-analyzer 2026-09-21] mutation:M2 edit is not valid (diagnostics:extra:E0560)

Draft for the author (not filed). Group `rust-analyzer-r4-diagnostics-extra-e0560-mutation-m2-1f508d`, signature `rust-analyzer|r4_edits|diagnostics:extra:E0560`, case family `mutation:M2`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `cloudflare/pingora@4487f7b2ab50` (corpus, commit 4487f7b2ab50f159e4a2cf4f6a6b813f61bb6e19), language rust

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. textDocument/didOpen: `open pingora-cache/src/eviction/async_lru.rs`
3. textDocument/didChange: `change pingora-cache/src/eviction/async_lru.rs (148, 12)-(148, 24) "weightlimit"`
4. textDocument/didChange: `change pingora-cache/src/eviction/async_lru.rs (155, 8)-(155, 8) "    weight_limit,\n        "`
5. Timing: wait until the server is idle after every step.
6. textDocument/didOpen `pingora-core/src/protocols/digest.rs`, `pingora-http/src/lib.rs` (the query step opens every target file that is not open), then wait until the server is idle.
7. The quick fix above was applied in the same session: the targeted diagnostic must be gone and the error count must not exceed the one before the mutation.
8. Query `textDocument/diagnostic` on `pingora-cache/src/eviction/async_lru.rs` line 148, column 9 (LSP position {line: 147, character: 8}) (M2:quickfix-errors:Fill struct fields); compare with the same query in a fresh session on the same content (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 [
  0,
  0,
  0,
  0,
  1,
  "E0560",
  "rust-analyzer",
  "no such field"
 ]
]
```

Project file `pingora-cache/src/eviction/async_lru.rs`:

```
 145 |     where
 146 |         C: AsyncEvictionCallback<CacheEntryKey>,
 147 |     {
 148 |         ManagerBuilder {
 149 |             weight_limit,
 150 |             eviction_cb,
 151 |             shutdown,
 152 |             runtime,
 153 |             capacity: 0,
 154 |             len_watermark: None,
 155 |             num_eviction_workers: N.max(1),
 156 |         }
 157 |     }
     ...
 159 |     /// Return the total number of shards (`N`).
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r4-diagnostics-extra-e0560-mutation-m2-1f508d/repro.json
```

## Evidence and reduction

- representative 0082cb0ebd81-v01: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 3 -> 3 (2 probes, 119.018 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects cloudflare/pingora@4487f7b2ab50, yewstack/yew@bfa6c19af971, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#23193](https://github.com/rust-lang/rust-analyzer/issues/23193) FP `expected &&&u32, found &&&&&&&&&&&&&&&&&&&&&&&&&i32` (open, 2026-08-19, 5 comments)
- [rust-lang/rust-analyzer#13317](https://github.com/rust-lang/rust-analyzer/issues/13317) Runnables: Extra Args sets Args instead of Extra Args (open, 2022-09-30, 0 comments)
- [rust-lang/rust-analyzer#19491](https://github.com/rust-lang/rust-analyzer/issues/19491) Too many arguments generates two diagnostics (open, 2025-04-01, 13 comments)
- [rust-lang/rust-analyzer#22828](https://github.com/rust-lang/rust-analyzer/issues/22828) panic: `can't project out of` (open, 2026-07-16, 6 comments)
- [rust-lang/rust-analyzer#21662](https://github.com/rust-lang/rust-analyzer/issues/21662) Documentation hint discrepency between autocomplete and inner function (open, 2026-02-17, 2 comments)
- [rust-lang/rust-analyzer#23199](https://github.com/rust-lang/rust-analyzer/issues/23199) Wrong range when request at edited std (open, 2026-08-20, 7 comments)
- [rust-lang/rust-analyzer#17289](https://github.com/rust-lang/rust-analyzer/issues/17289) Invalid offset -32603 when editing an empty .rs file (open, 2024-05-24, 68 comments)
- [rust-lang/rust-analyzer#15873](https://github.com/rust-lang/rust-analyzer/issues/15873) stack overflow in `ra_ap_hir_ty::mir::borrowck::ever_initialized_map::dfs` on the `idna` crate (closed, 2023-11-11, 5 comments)
- queries: `diagnostics extra repo:rust-lang/rust-analyzer is:issue`; `diagnostics "wrong edit" repo:rust-lang/rust-analyzer is:issue`
