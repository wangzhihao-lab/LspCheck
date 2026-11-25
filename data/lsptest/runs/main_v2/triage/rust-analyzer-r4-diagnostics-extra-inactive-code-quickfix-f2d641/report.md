# [rust-analyzer 2026-09-21] quickfix edit is not valid (diagnostics:extra:inactive_code)

Draft for the author (not filed). Group `rust-analyzer-r4-diagnostics-extra-inactive-code-quickfix-f2d641`, signature `rust-analyzer|r4_edits|diagnostics:extra:inactive_code`, case family `quickfix`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `cloudflare/pingora@4487f7b2ab50` (corpus, commit 4487f7b2ab50f159e4a2cf4f6a6b813f61bb6e19), language rust

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. request code actions for the diagnostic {'code': 'inactive_code', 'message': 'code is inactive due to #[cfg] directives: target_os = "linux" is disabled', 'range': {'end': {'character': 1, 'line': 285}, 'start': {'character': 0, 'line': 257}}, 'severity': 4} in `pingora-core/src/protocols/digest.rs`; apply the quick fix 'Remove all unused imports'; wait until idle: the diagnostic must be gone and no error added.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  82,
  4,
  83,
  45,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  103,
  4,
  111,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  129,
  4,
  134,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  143,
  4,
  148,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  163,
  4,
  170,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  181,
  4,
  188,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  199,
  4,
  206,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  220,
  4,
  230,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ]
]
```

Actual:

```json
[
 [
  82,
  4,
  83,
  45,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  103,
  4,
  111,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  129,
  4,
  134,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  143,
  4,
  148,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  163,
  4,
  170,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  181,
  4,
  188,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  199,
  4,
  206,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  220,
  4,
  230,
  5,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: windows is disabled"
 ],
 [
  257,
  0,
  284,
  1,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ]
]
```

Project file `pingora-core/src/protocols/digest.rs`:

```
 255 |     fn set_socket_digest(&mut self, _socket_digest: SocketDigest) {}
 256 | }
     ...
 258 | #[cfg(all(test, target_os = "linux"))]
 259 | mod tests {
 260 |     use super::SocketDigest;
 261 |     use std::os::unix::io::AsRawFd;
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r4-diagnostics-extra-inactive-code-quickfix-f2d641/repro.json
```

## Evidence and reduction

- representative 0082cb0ebd81-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects cloudflare/pingora@4487f7b2ab50, h4ckf0r0day/obscura@0e17221dbb55, tokio-rs/tokio@3930bd182cb1, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#16642](https://github.com/rust-lang/rust-analyzer/issues/16642) When using code actions for quick fix, multiple possible options were not split (open, 2024-02-23, 6 comments)
- [rust-lang/rust-analyzer#15733](https://github.com/rust-lang/rust-analyzer/issues/15733) Import quick fix offers duplicate options (open, 2023-10-09, 0 comments)
- [rust-lang/rust-analyzer#11039](https://github.com/rust-lang/rust-analyzer/issues/11039) Quick fix to declare an unresolved lifetime (open, 2021-12-17, 1 comments)
- [rust-lang/rust-analyzer#14373](https://github.com/rust-lang/rust-analyzer/issues/14373) Consider present type aliases when using quick fixes (open, 2023-03-18, 2 comments)
- [rust-lang/rust-analyzer#14189](https://github.com/rust-lang/rust-analyzer/issues/14189) Quick Fix options for implementing individual default members (open, 2023-02-22, 0 comments)
- [rust-lang/rust-analyzer#23193](https://github.com/rust-lang/rust-analyzer/issues/23193) FP `expected &&&u32, found &&&&&&&&&&&&&&&&&&&&&&&&&i32` (open, 2026-08-19, 5 comments)
- [rust-lang/rust-analyzer#13317](https://github.com/rust-lang/rust-analyzer/issues/13317) Runnables: Extra Args sets Args instead of Extra Args (open, 2022-09-30, 0 comments)
- [rust-lang/rust-analyzer#19491](https://github.com/rust-lang/rust-analyzer/issues/19491) Too many arguments generates two diagnostics (open, 2025-04-01, 13 comments)
- queries: `"quick fix" in:title repo:rust-lang/rust-analyzer is:issue`; `diagnostics extra repo:rust-lang/rust-analyzer is:issue`; `diagnostics "quick fix" repo:rust-lang/rust-analyzer is:issue`; `diagnostics "wrong edit" repo:rust-lang/rust-analyzer is:issue`
