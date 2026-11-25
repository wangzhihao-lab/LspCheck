# LSP test corpus preparation

Generated: 2026-11-18 00:31:57

40 projects x their language's server(s) = 50 records.

Settle rule: push servers (pyright, ts6, gopls) wait for publishDiagnostics on every opened file plus 3s with no server traffic at all; pull servers (ts7, rust-analyzer) poll textDocument/diagnostic until two consecutive polls agree; rust-analyzer additionally waits for a quiescent experimental/serverStatus notification. Hard cap: 600s per project x server.

"Import noise" is a heuristic over the final diagnostics: pyright reportMissingImports/reportMissingModuleSource, TS codes 2307/2306/2792/7016, rust-analyzer unresolved-import, plus a generic message regex (cannot find module/package, could not be resolved, missing go.sum entry, ...). "Overwhelming noise" below means >= 100 noise diagnostics, or noise making up >= 70% of >= 20 diagnostics.

## Results

| Language | Repo | Server | Deps | Settled | Seconds | Diag E/W/I/H | Noise | Peak RSS MB | Notes |
|---|---|---|---|---|---:|---|---:|---:|---|
| go | SagerNet/sing-box | gopls-v0.23.0 | ok | True | 9.7 | 0/0/0/0 | 0 | 1238 |  |
| go | abiosoft/colima | gopls-v0.23.0 | ok | True | 6.3 | 0/0/0/1 | 0 | 220 |  |
| go | beego/beego | gopls-v0.23.0 | ok | True | 20.3 | 0/0/0/0 | 0 | 671 |  |
| go | docker/compose | gopls-v0.23.0 | ok | True | 6.9 | 0/0/0/1 | 0 | 1204 |  |
| go | evanw/esbuild | gopls-v0.23.0 | ok | True | 6.1 | 0/0/3/0 | 0 | 957 |  |
| go | go-gorm/gorm | gopls-v0.23.0 | ok | True | 20.7 | 0/1/0/24 | 0 | 311 |  |
| go | iawia002/lux | gopls-v0.23.0 | ok | True | 5.8 | 0/1/0/0 | 0 | 1269 |  |
| go | labstack/echo | gopls-v0.23.0 | ok | True | 6.5 | 0/0/0/0 | 0 | 1006 |  |
| go | schollz/croc | gopls-v0.23.0 | ok | True | 8.8 | 0/0/1/0 | 0 | 691 |  |
| go | zeromicro/go-zero | gopls-v0.23.0 | ok | True | 7.2 | 0/0/0/1 | 0 | 1401 |  |
| python | Alishahryar1/free-claude-code | pyright-1.1.414 | n/a | True | 4.0 | 3/0/0/24 | 3 | 276 |  |
| python | FoundationAgents/OpenManus | pyright-1.1.414 | n/a | True | 3.7 | 1/0/0/1 | 1 | 206 |  |
| python | MemPalace/mempalace | pyright-1.1.414 | n/a | True | 4.0 | 3/0/0/1 | 1 | 374 |  |
| python | NanmiCoder/MediaCrawler | pyright-1.1.414 | n/a | True | 3.6 | 5/0/0/1 | 5 | 212 |  |
| python | karpathy/nanochat | pyright-1.1.414 | n/a | True | 3.6 | 10/0/0/1 | 6 | 194 |  |
| python | scrapy/scrapy | pyright-1.1.414 | n/a | True | 3.7 | 6/4/0/22 | 9 | 239 |  |
| python | soimort/you-get | pyright-1.1.414 | n/a | True | 3.6 | 3/0/0/3 | 2 | 206 |  |
| python | ultralytics/yolov5 | pyright-1.1.414 | n/a | True | 4.9 | 53/0/0/9 | 8 | 546 |  |
| python | usestrix/strix | pyright-1.1.414 | n/a | True | 3.4 | 4/0/0/0 | 1 | 171 |  |
| python | virattt/ai-hedge-fund | pyright-1.1.414 | n/a | True | 3.6 | 1/0/0/1 | 0 | 190 |  |
| rust | casey/just | rust-analyzer-2026-09-21 | ok | True | 11.9 | 0/0/0/0 | 0 | 1023 |  |
| rust | cloudflare/pingora | rust-analyzer-2026-09-21 | ok | True | 104.6 | 0/0/0/1 | 0 | 2307 |  |
| rust | dandavison/delta | rust-analyzer-2026-09-21 | ok | True | 20.2 | 0/0/0/0 | 0 | 1231 |  |
| rust | googleworkspace/cli | rust-analyzer-2026-09-21 | ok | True | 20.2 | 0/0/0/20 | 0 | 1825 |  |
| rust | h4ckf0r0day/obscura | rust-analyzer-2026-09-21 | ok | True | 46.5 | 0/0/0/3 | 0 | 2026 |  |
| rust | iced-rs/iced | rust-analyzer-2026-09-21 | ok | True | 27.8 | 0/0/0/0 | 0 | 4341 |  |
| rust | niri-wm/niri | rust-analyzer-2026-09-21 | ok | True | 35.4 | 0/0/0/0 | 0 | 2914 |  |
| rust | sharkdp/hyperfine | rust-analyzer-2026-09-21 | ok | True | 10.2 | 0/0/0/3 | 0 | 1102 |  |
| rust | tokio-rs/tokio | rust-analyzer-2026-09-21 | ok | True | 14.9 | 0/0/0/0 | 0 | 1355 |  |
| rust | yewstack/yew | rust-analyzer-2026-09-21 | ok | True | 91.5 | 0/0/0/1 | 0 | 2742 |  |
| typescript | DayuanJiang/next-ai-draw-io | ts6-6.0.3 | ok | True | 7.3 | 0/0/0/0 | 0 | 64 |  |
| typescript | DayuanJiang/next-ai-draw-io | ts7-7.0.2 | ok | True | 1.9 | 0/0/0/0 | 0 | 414 |  |
| typescript | Gitlawb/openclaude | ts6-6.0.3 | ok | True | 10.9 | 6/0/0/0 | 0 | 64 |  |
| typescript | Gitlawb/openclaude | ts7-7.0.2 | ok | True | 2.3 | 6/0/0/0 | 0 | 1028 |  |
| typescript | colinhacks/zod | ts6-6.0.3 | failed | True | 3.9 | 3/0/0/0 | 2 | 63 |  |
| typescript | colinhacks/zod | ts7-7.0.2 | failed | True | 1.6 | 3/0/0/0 | 2 | 103 |  |
| typescript | date-fns/date-fns | ts6-6.0.3 | ok | True | 4.5 | 3/0/0/3 | 3 | 59 |  |
| typescript | date-fns/date-fns | ts7-7.0.2 | ok | True | 1.7 | 3/0/0/0 | 3 | 106 |  |
| typescript | hexojs/hexo | ts6-6.0.3 | ok | True | 4.6 | 8/0/0/3 | 0 | 64 |  |
| typescript | hexojs/hexo | ts7-7.0.2 | ok | True | 1.6 | 8/0/0/2 | 0 | 107 |  |
| typescript | mifi/lossless-cut | ts6-6.0.3 | ok | True | 5.8 | 0/0/0/0 | 0 | 60 |  |
| typescript | mifi/lossless-cut | ts7-7.0.2 | ok | True | 1.9 | 0/0/0/0 | 0 | 396 |  |
| typescript | pear-devs/pear-desktop | ts6-6.0.3 | skipped-by-flag | True | 5.9 | 0/0/0/0 | 0 | 64 |  |
| typescript | pear-devs/pear-desktop | ts7-7.0.2 | skipped-by-flag | True | 1.8 | 0/0/0/0 | 0 | 372 |  |
| typescript | solidjs/solid | ts6-6.0.3 | ok | True | 4.1 | 73/0/0/0 | 4 | 59 |  |
| typescript | solidjs/solid | ts7-7.0.2 | ok | True | 1.6 | 73/0/0/0 | 4 | 118 |  |
| typescript | umami-software/umami | ts6-6.0.3 | skipped-by-flag | True | 8.6 | 0/0/0/0 | 0 | 64 |  |
| typescript | umami-software/umami | ts7-7.0.2 | skipped-by-flag | True | 2.0 | 0/0/0/0 | 0 | 584 |  |
| typescript | vadimdemedes/ink | ts6-6.0.3 | skipped-by-flag | True | 4.8 | 0/0/0/1 | 0 | 60 |  |
| typescript | vadimdemedes/ink | ts7-7.0.2 | skipped-by-flag | True | 1.6 | 0/0/0/1 | 0 | 122 |  |

## Recommended exclusions

None.

## Settle time by server (seconds; settled runs only)

- gopls: n=10 median=7.1s max=20.7s
- pyright: n=10 median=3.7s max=4.9s
- rust-analyzer: n=10 median=24.0s max=104.6s
- ts6: n=10 median=5.3s max=10.9s
- ts7: n=10 median=1.8s max=2.3s
