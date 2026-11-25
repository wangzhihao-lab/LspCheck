# [rust-analyzer 2026-09-21] semanticTokensRange: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-semantictokensrange-changed-b-b6e28b`, signature `rust-analyzer|r3_routes|semanticTokensRange:changed`, case family `b`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `alacritty/alacritty@d692748d3f61` (corpus, commit d692748d3f61253ebe9f5094320120d22f6a046f), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/semanticTokens/full` on `alacritty_terminal/src/tty/unix.rs`, then `textDocument/semanticTokens/range` over [245, 28, 253, 13]; the range answer must equal the full answer restricted to that range.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  245,
  32,
  2,
  "operator",
  ""
 ],
 [
  245,
  34,
  3,
  "function",
  "associated,defaultLibrary,library,static"
 ],
 [
  245,
  38,
  4,
  "parameter",
  "reference"
 ],
 [
  245,
  42,
  1,
  "operator",
  ""
 ],
 [
  245,
  43,
  9,
  "method",
  "defaultLibrary,library,reference"
 ],
 [
  245,
  54,
  1,
  "operator",
  ""
 ],
 [
  245,
  55,
  8,
  "method",
  "defaultLibrary,library,reference,trait"
 ],
 [
  245,
  66,
  1,
  "operator",
  ""
 ],
 [
  245,
  67,
  2,
  "method",
  "constant,consuming,defaultLibrary,library"
 ],
 [
  247,
  4,
  6,
  "keyword",
  "unsafe"
 ],
 [
  248,
  8,
  7,
  "variable",
  "mutable"
 ],
 [
  248,
  15,
  1,
  "operator",
  ""
 ],
 [
  248,
  16,
  8,
  "method",
  "defaultLibrary,library,mutable,reference,trait,unsafe"
 ],
 [
  248,
  24,
  1,
  "punctuation",
  "unsafe"
 ],
 [
  248,
  25,
  4,
  "keyword",
  ""
 ],
 [
  249,
  12,
  30,
  "comment",
  ""
 ],
 [
  250,
  12,
  3,
  "keyword",
  ""
 ],
 [
  250,
  16,
  3,
  "variable",
  "declaration"
 ],
 [
  250,
  20,
  1,
  "operator",
  ""
 ],
 [
  250,
  22,
  4,
  "namespace",
  "crateRoot,library"
 ],
 [
  250,
  26,
  2,
  "operator",
  ""
 ],
 [
  250,
  28,
  6,
  "function",
  "library,unsafe"
 ],
 [
  250,
  34,
  1,
  "punctuation",
  "unsafe"
 ],
 [
  250,
  35,
  1,
  "punctuation",
  "unsafe"
 ],
 [
  251,
  12,
  2,
  "keyword",
  "controlFlow"
 ],
 [
  251,
  15,
  3,
  "variable",
  ""
 ],
 [
  251,
  19,
  2,
  "operator",
  ""
 ],
 [
  251,
  22,

... (1883 characters)
```

Actual:

```json
[
 [
  245,
  32,
  2,
  "operator",
  ""
 ],
 [
  245,
  34,
  3,
  "function",
  "associated,defaultLibrary,library,static"
 ],
 [
  245,
  38,
  4,
  "parameter",
  "reference"
 ],
 [
  245,
  42,
  1,
  "operator",
  ""
 ],
 [
  245,
  43,
  9,
  "method",
  "defaultLibrary,library,reference"
 ],
 [
  245,
  54,
  1,
  "operator",
  ""
 ],
 [
  245,
  55,
  8,
  "method",
  "defaultLibrary,library,reference,trait"
 ],
 [
  245,
  66,
  1,
  "operator",
  ""
 ],
 [
  245,
  67,
  2,
  "method",
  "constant,consuming,defaultLibrary,library"
 ],
 [
  247,
  4,
  6,
  "keyword",
  "unsafe"
 ],
 [
  248,
  8,
  7,
  "variable",
  "mutable"
 ],
 [
  248,
  15,
  1,
  "operator",
  ""
 ],
 [
  248,
  16,
  8,
  "method",
  "defaultLibrary,library,mutable,reference,trait"
 ],
 [
  248,
  25,
  4,
  "keyword",
  ""
 ],
 [
  249,
  12,
  30,
  "comment",
  ""
 ],
 [
  250,
  12,
  3,
  "keyword",
  ""
 ],
 [
  250,
  16,
  3,
  "variable",
  "declaration"
 ],
 [
  250,
  20,
  1,
  "operator",
  ""
 ],
 [
  250,
  22,
  4,
  "namespace",
  "crateRoot,library"
 ],
 [
  250,
  26,
  2,
  "operator",
  ""
 ],
 [
  250,
  28,
  6,
  "function",
  "library"
 ],
 [
  251,
  12,
  2,
  "keyword",
  "controlFlow"
 ],
 [
  251,
  15,
  3,
  "variable",
  ""
 ],
 [
  251,
  19,
  2,
  "operator",
  ""
 ],
 [
  251,
  22,
  1,
  "number",
  ""
 ],
 [
  251,
  23,
  1,
  "number",
  ""
 ],
 [
  252,
  16,
  6,
  "keyword",
  "controlFlow"
 ],
 [
  252,
  23,
  3,
  "enumMember",
  "defaultLibr
... (1710 characters)
```

Project file `alacritty_terminal/src/tty/unix.rs`:

```
 243 |     let working_directory = config
 244 |         .working_directory
 245 |         .as_ref()
 246 |         .and_then(|path| CString::new(path.as_os_str().as_bytes()).ok());
     ...
 248 |     unsafe {
 249 |         builder.pre_exec(move || {
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r3-semantictokensrange-changed-b-b6e28b/repro.json
```

## Evidence and reduction

- representative c6d3284a6341-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects alacritty/alacritty@d692748d3f61, timings settled, seeds 1

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

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-trb6e28b-r3-replay-baseline-20260925-171239-9155d0] stderr: 2026-09-25T17:12:41.827602-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alac
[rust-analyzer-2026-09-21-trb6e28b-r3-replay-baseline-20260925-171239-9155d0] stderr: 2026-09-25T17:12:51.464632-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alac
[rust-analyzer-2026-09-21-trb6e28b-r3-replay-control-20260925-171300-5f5d73] stderr: 2026-09-25T17:13:03.042517-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alacr
[rust-analyzer-2026-09-21-trb6e28b-r3-replay-control-20260925-171300-5f5d73] stderr: 2026-09-25T17:13:10.307253-07:00  WARN cyclic deps: alacritty_config_derive(Idx::<CrateBuilder>(23)) -> alacritty_config(Idx::<CrateBuilder>(22)), alternative path: alacritty_config(Idx::<CrateBuilder>(22)) -> alacr
```
