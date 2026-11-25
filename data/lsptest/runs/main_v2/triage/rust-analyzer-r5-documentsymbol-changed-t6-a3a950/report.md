# [rust-analyzer 2026-09-21] documentSymbol changes its answer after transformation T6

Draft for the author (not filed). Group `rust-analyzer-r5-documentsymbol-changed-t6-a3a950`, signature `rust-analyzer|r5_transforms|documentSymbol:changed`, case family `T6`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `yewstack/yew@bfa6c19af971` (corpus, commit bfa6c19af971084f9547495388bde9aceeb81aaa), language rust

## Relation violated

Semantics-preserving transformation (R5): blank lines, a comment, trailing whitespace, CRLF line ends, the final newline or an inline comment do not change the program, so the answers must agree after mapping positions.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. Two fresh sessions: one on the original project, one with transformation T6 applied to `packages/yew/src/functional/hooks/use_prepared_state/feat_hydration.rs` (1 edit(s), first [64, 40, 64, 40]).
3. Query `textDocument/documentSymbol` on `packages/yew/src/functional/hooks/use_prepared_state/feat_hydration.rs` for the whole file; compare with the same query on the untransformed project, positions mapped (expected).

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  "HookProvider",
  23,
  55,
  4,
  62,
  5
 ],
 [
  "Output",
  26,
  69,
  8,
  69,
  54
 ],
 [
  "_marker",
  8,
  60,
  8,
  60,
  31
 ],
 [
  "decode_base64",
  12,
  14,
  0,
  38,
  1
 ],
 [
  "decode_base64",
  12,
  40,
  0,
  47,
  1
 ],
 [
  "deps",
  8,
  61,
  8,
  61,
  15
 ],
 [
  "impl Hook for HookProvider<T, D>",
  19,
  64,
  4,
  128,
  5
 ],
 [
  "run",
  6,
  71,
  8,
  127,
  9
 ],
 [
  "use_prepared_state",
  12,
  49,
  0,
  134,
  1
 ]
]
```

Actual:

```json
[
 [
  "HookProvider",
  23,
  55,
  4,
  62,
  5
 ],
 [
  "Output",
  26,
  69,
  8,
  69,
  54
 ],
 [
  "_marker",
  8,
  60,
  8,
  60,
  31
 ],
 [
  "decode_base64",
  12,
  14,
  0,
  38,
  1
 ],
 [
  "decode_base64",
  12,
  40,
  0,
  47,
  1
 ],
 [
  "deps",
  8,
  61,
  8,
  61,
  15
 ],
 [
  "impl Hook for HookProvider<T, /* 注释🙂 */ D>",
  19,
  64,
  4,
  128,
  5
 ],
 [
  "run",
  6,
  71,
  8,
  127,
  9
 ],
 [
  "use_prepared_state",
  12,
  49,
  0,
  134,
  1
 ]
]
```

Project file `packages/yew/src/functional/hooks/use_prepared_state/feat_hydration.rs`:

```
   1 | //! The client-side rendering variant. This is used for client side rendering.
     ...
   3 | use std::marker::PhantomData;
   4 | use std::rc::Rc;
     ...
   6 | use serde::Serialize;
   7 | use serde::de::DeserializeOwned;
   8 | use wasm_bindgen::JsValue;
     ...
  10 | use super::PreparedStateBase;
  11 | use crate::functional::{Hook, HookContext, use_state};
  12 | use crate::platform::spawn_local;
  13 | use crate::suspense::{Suspension, SuspensionResult};
     ...
  15 | #[cfg(all(
  16 |     target_arch = "wasm32",
  17 |     not(target_os = "wasi"),
  18 |     not(feature = "not_browser_env")
  19 | ))]
  20 | async fn decode_base64(s: &str) -> Result<Vec<u8>, JsValue> {
  21 |     use gloo::utils::window;
  22 |     use js_sys::Uint8Array;
  23 |     use wasm_bindgen::JsCast;
  24 |     use wasm_bindgen_futures::JsFuture;
     ...
  26 |     let fetch_promise = window().fetch_with_str(s);
     ...
  28 |     let content_promise = JsFuture::from(fetch_promise)
  29 |         .await
  30 |         .and_then(|m| m.dyn_into::<web_sys::Response>())
  31 |         .and_then(|m| m.array_buffer())?;
     ...
  33 |     let content_array = JsFuture::from(content_promise)
  34 |         .await
  35 |         .as_ref()
  36 |         .map(Uint8Array::new)?;
     ...
  38 |     Ok(content_array.to_vec())
  39 | }
     ...
  41 | #[cfg(any(
  42 |     not(target_arch = "wasm32"),
  43 |     target_os = "wasi",
  44 |     feature = "not_browser_env"
  45 | ))]
  46 | async fn decode_base64(_s: &str) -> Result<Vec<u8>, JsValue> {
  47 |     unreachable!("this function is not callable under non-wasm targets!");
  48 | }
     ...
  50 | #[doc(hidden)]
  51 | pub fn use_prepared_state<T, D>(deps: D) -> impl Hook<Output = SuspensionResult<Option<Rc<T>>>>
  52 | where
  53 |     D: Serialize + DeserializeOwned + PartialEq + 'static,
  54 |     T: Serialize + DeserializeOwned + 'static,
  55 | {
  56 |     struct HookProvider<T, D>
  57 |     where
  58 |         D: Serialize + DeserializeOwned + PartialEq + 'static,
  59 |         T: Serialize + DeserializeOwned + 'static,
  60 |     {
  61 |         _marker: PhantomData<T>,
  62 |         deps: D,
  63 |     }
     ...
  65 |     impl<T, D> Hook for HookProvider<T, D>
  66 |     where
  67 |         D: Serialize + DeserializeOwned + PartialEq + 'static,
  68 |         T: Serialize + DeserializeOwned + 'static,
  69 |     {
  70 |         type Output = SuspensionResult<Option<Rc<T>>>;
     ...
  72 |         fn run(self, ctx: &mut HookContext) -> Self::Output {
  73 |             let data = use_state(|| {
  74 |                 let (s, handle) = Suspension::new();
  75 |                 (
  76 |                     SuspensionResult::<(Option<Rc<T>>, Option<Rc<D>>)>::Err(s),
  77 |                     Some(handle),
  78 |                 )
  79 |             })
  80 |             .run(ctx);
     ...
  82 |             let state = {
  83 |                 let data = data.clone();
  84 |                 ctx.next_prepared_state(move |_re_render, buf| -> PreparedStateBase<T, D> {
  85 |                     if let Some(buf) = buf {
  86 |                         let buf = format!("data:application/octet-binary;base64,{buf}");
     ...
  88 |                         spawn_local(async move {
  89 |                             let buf = decode_base64(&buf)
  90 |                                 .await
  91 |                                 .expect("failed to deserialize state");
     ...
  93 |                             let ((state, deps), _) =
  94 |                                 bincode::serde::decode_from_slice::<(Option<T>, Option<D>), _>(
  95 |                                     &buf,
  96 |                                     bincode::config::standard(),
  97 |                                 )
  98 |                                 .map(|((state, deps), consumed)| {
  99 |                                     ((state.map(Rc::new), deps.map(Rc::new)), consumed)
 100 |                                 })
 101 |                                 .expect("failed to deserialize state");
     ...
 103 |                             data.set((Ok((state, deps)), None));
 104 |                         });
 105 |                     }
     ...
 107 |                     PreparedStateBase {
 108 |                         #[cfg(feature = "ssr")]
 109 |                         state: None,
 110 |                         #[cfg(feature = "ssr")]
 111 |                         deps: None,
     ...
 113 |                         has_buf: buf.is_some(),
 114 |                         _marker: PhantomData,
 115 |                     }
 116 |                 })
 117 |             };
     ...
 119 |             if state.has_buf {
 120 |                 let (data, deps) = data.0.clone()?;
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r5-documentsymbol-changed-t6-a3a950/repro.json
```

## Evidence and reduction

- representative 42f7b233f3d9-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 2 -> 2 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects yewstack/yew@bfa6c19af971, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#23301](https://github.com/rust-lang/rust-analyzer/issues/23301) Error messages disappear when `rustc-unicode` is enabled (closed, 2026-09-06, 4 comments)
- [rust-lang/rust-analyzer#17420](https://github.com/rust-lang/rust-analyzer/issues/17420) "Request textdocument/selectionrange Failed" when executing editor.action.smartSelect.expand in vscode on some unicode box drawing characters (closed, 2024-06-14, 1 comments)
- [rust-lang/rust-analyzer#9401](https://github.com/rust-lang/rust-analyzer/issues/9401) Add unicode character snippets (closed, 2021-06-25, 2 comments)
- [rust-lang/rust-analyzer#9121](https://github.com/rust-lang/rust-analyzer/issues/9121) Panic on textDocument/didChange containing a multi-byte unicode character (closed, 2021-06-03, 5 comments)
- [rust-lang/rust-analyzer#7635](https://github.com/rust-lang/rust-analyzer/issues/7635) Unicode-related panic when editing comment (closed, 2021-02-10, 2 comments)
- [rust-lang/rust-analyzer#144](https://github.com/rust-lang/rust-analyzer/issues/144) LSP: Validate responses against client capabilities (open, 2018-10-18, 17 comments)
- [rust-lang/rust-analyzer#9601](https://github.com/rust-lang/rust-analyzer/issues/9601) GTK3 on Windows 10: Type hinting but no type checking? (closed, 2021-07-14, 16 comments)
- queries: `unicode in:title repo:rust-lang/rust-analyzer is:issue`; `"document symbol" wrong repo:rust-lang/rust-analyzer is:issue`; `"document symbol" unicode repo:rust-lang/rust-analyzer is:issue`; `"document symbol" whitespace repo:rust-lang/rust-analyzer is:issue`

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tra3a950-r5-replay-baseline-20261118-235130-4ae9f5] stderr: 2026-11-18T23:51:32.147305-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crat
[rust-analyzer-2026-09-21-tra3a950-r5-replay-baseline-20261118-235130-4ae9f5] stderr: 2026-11-18T23:51:32.14732-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-tra3a950-r5-replay-baseline-20261118-235130-4ae9f5] stderr: 2026-11-18T23:51:32.147328-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx
[rust-analyzer-2026-09-21-tra3a950-r5-replay-baseline-20261118-235130-4ae9f5] stderr: 2026-11-18T23:52:18.764333-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crat
[rust-analyzer-2026-09-21-tra3a950-r5-replay-baseline-20261118-235130-4ae9f5] stderr: 2026-11-18T23:52:18.764348-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-tra3a950-r5-replay-baseline-20261118-235130-4ae9f5] stderr: 2026-11-18T23:52:18.764366-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx
[rust-analyzer-2026-09-21-tra3a950-r5-replay-case-20261118-235331-f02534] stderr: 2026-11-18T23:53:33.328507-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<CrateBui
[rust-analyzer-2026-09-21-tra3a950-r5-replay-case-20261118-235331-f02534] stderr: 2026-11-18T23:53:33.328525-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-tra3a950-r5-replay-case-20261118-235331-f02534] stderr: 2026-11-18T23:53:33.328537-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx::<C
[rust-analyzer-2026-09-21-tra3a950-r5-replay-case-20261118-235331-f02534] stderr: 2026-11-18T23:54:08.685736-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<CrateBui
[rust-analyzer-2026-09-21-tra3a950-r5-replay-case-20261118-235331-f02534] stderr: 2026-11-18T23:54:08.685754-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-tra3a950-r5-replay-case-20261118-235331-f02534] stderr: 2026-11-18T23:54:08.68579-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx::<Cr
[rust-analyzer-2026-09-21-tra3a950-r5-replay-control-20261118-235238-13881a] stderr: 2026-11-18T23:52:40.800202-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crate
[rust-analyzer-2026-09-21-tra3a950-r5-replay-control-20261118-235238-13881a] stderr: 2026-11-18T23:52:40.800217-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-tra3a950-r5-replay-control-20261118-235238-13881a] stderr: 2026-11-18T23:52:40.800225-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx:
[rust-analyzer-2026-09-21-tra3a950-r5-replay-control-20261118-235238-13881a] stderr: 2026-11-18T23:53:12.910986-08:00  WARN cyclic deps: yew_agent_macro(Idx::<CrateBuilder>(94)) -> yew_agent(Idx::<CrateBuilder>(93)), alternative path: yew_agent(Idx::<CrateBuilder>(93)) -> yew_agent_macro(Idx::<Crate
[rust-analyzer-2026-09-21-tra3a950-r5-replay-control-20261118-235238-13881a] stderr: 2026-11-18T23:53:12.910999-08:00  WARN cyclic deps: yew_macro(Idx::<CrateBuilder>(97)) -> yew(Idx::<CrateBuilder>(76)), alternative path: yew(Idx::<CrateBuilder>(76)) -> yew_macro(Idx::<CrateBuilder>(97))
[rust-analyzer-2026-09-21-tra3a950-r5-replay-control-20261118-235238-13881a] stderr: 2026-11-18T23:53:12.911014-08:00  WARN cyclic deps: yew_router_macro(Idx::<CrateBuilder>(115)) -> yew_router(Idx::<CrateBuilder>(107)), alternative path: yew_router(Idx::<CrateBuilder>(107)) -> yew_router_macro(Idx:
```
