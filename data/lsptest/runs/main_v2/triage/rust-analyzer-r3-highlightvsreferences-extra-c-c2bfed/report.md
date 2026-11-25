# [rust-analyzer 2026-09-21] highlightVsReferences: two routes to the same fact disagree

Draft for the author (not filed). Group `rust-analyzer-r3-highlightvsreferences-extra-c-c2bfed`, signature `rust-analyzer|r3_routes|highlightVsReferences:extra`, case family `c`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `cloudflare/pingora@4487f7b2ab50` (corpus, commit 4487f7b2ab50f159e4a2cf4f6a6b813f61bb6e19), language rust

## Relation violated

Route equivalence (R3): two protocol routes to the same fact (pull and push diagnostics, semanticTokens range and full, documentHighlight and references, definition at a symbol and at its references) must agree.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/documentHighlight` and `textDocument/references` (includeDeclaration) on `pingora-proxy/examples/connection_filter.rs` at line 16, column 14 (LSP position {line: 15, character: 13}); every highlight range must be a reference range in that file.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  15,
  10,
  15,
  16
 ]
]
```

Actual:

```json
[
 [
  15,
  10,
  15,
  16
 ],
 [
  66,
  19,
  66,
  24
 ]
]
```

Project file `pingora-proxy/examples/connection_filter.rs`:

```
   1 | // Copyright 2026 Cloudflare, Inc.
   2 | //
   3 | // Licensed under the Apache License, Version 2.0 (the "License");
   4 | // you may not use this file except in compliance with the License.
   5 | // You may obtain a copy of the License at
   6 | //
   7 | // http://www.apache.org/licenses/LICENSE-2.0
   8 | //
   9 | // Unless required by applicable law or agreed to in writing, software
  10 | // distributed under the License is distributed on an "AS IS" BASIS,
  11 | // WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  12 | // See the License for the specific language governing permissions and
  13 | // limitations under the License.
     ...
  15 | use async_trait::async_trait;
  16 | use clap::Parser;
  17 | use log::info;
  18 | use pingora_core::listeners::ConnectionFilter;
  19 | use pingora_core::prelude::Opt;
  20 | use pingora_core::server::Server;
  21 | use pingora_core::upstreams::peer::HttpPeer;
  22 | use pingora_core::Result;
  23 | use pingora_proxy::{ProxyHttp, Session};
  24 | use std::sync::Arc;
     ...
  26 | /// This example demonstrates how to implement a connection filter
  27 | pub struct MyProxy;
     ...
  29 | #[async_trait]
  30 | impl ProxyHttp for MyProxy {
  31 |     type CTX = ();
     ...
  33 |     fn new_ctx(&self) -> Self::CTX {}
     ...
  35 |     async fn upstream_peer(
  36 |         &self,
  37 |         _session: &mut Session,
  38 |         _ctx: &mut Self::CTX,
  39 |     ) -> Result<Box<HttpPeer>> {
  40 |         // Forward to httpbin.org for testing
  41 |         let peer = HttpPeer::new(("httpbin.org", 80), false, "httpbin.org".into());
  42 |         Ok(Box::new(peer))
  43 |     }
  44 | }
     ...
  46 | /// Connection filter that blocks ALL connections (for testing)
  47 | #[derive(Debug, Clone)]
  48 | struct BlockAllFilter;
     ...
  50 | #[async_trait]
  51 | impl ConnectionFilter for BlockAllFilter {
  52 |     async fn should_accept(&self, addr: Option<&std::net::SocketAddr>) -> bool {
  53 |         info!(
  54 |             "BLOCKING connection from {:?} (BlockAllFilter active)",
  55 |             addr
  56 |         );
  57 |         false
  58 |     }
  59 | }
     ...
  61 | // RUST_LOG=INFO cargo run --example connection_filter
     ...
  63 | fn main() {
  64 |     env_logger::init();
     ...
  66 |     // read command line arguments
  67 |     let opt = Opt::parse();
  68 |     let mut my_server = Server::new(Some(opt)).unwrap();
  69 |     my_server.bootstrap();
     ...
  71 |     let mut my_proxy = pingora_proxy::http_proxy_service(&my_server.configuration, MyProxy);
     ...
  73 |     // Create a filter that blocks ALL connections
  74 |     let filter = Arc::new(BlockAllFilter);
     ...
  76 |     info!("Setting BlockAllFilter on proxy service");
  77 |     my_proxy.set_connection_filter(filter.clone());
     ...
  79 |     info!("Adding TCP endpoints AFTER setting filter");
  80 |     my_proxy.add_tcp("0.0.0.0:6195");
  81 |     my_proxy.add_tcp("0.0.0.0:6196");
     ...
  83 |     info!("====================================");
  84 |     info!("Server starting with BlockAllFilter");
  85 |     info!("This filter blocks ALL connections!");
  86 |     info!("====================================");
  87 |     info!("");
  88 |     info!("Test with:");
  89 |     info!("  curl http://localhost:6195/get");
  90 |     info!("  curl http://localhost:6196/get");
  91 |     info!("");
  92 |     info!("ALL requests should be blocked!");
  93 |     info!("You should see 'BLOCKING connection' in the logs");
  94 |     info!("and curl should fail with 'Connection refused' or hang");
  95 |     info!("");
     ...
  97 |     my_server.add_service(my_proxy);
  98 |     my_server.run_forever();
  99 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r3-highlightvsreferences-extra-c-c2bfed/repro.json
```

## Evidence and reduction

- representative 142f3ee23060-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects cloudflare/pingora@4487f7b2ab50, iced-rs/iced@0ef42477fb6f, yewstack/yew@bfa6c19af971, timings settled, seeds 1, 2

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
