# LSP test corpus preparation

Generated: 2026-09-23 10:40:57

40 projects x their language's server(s) = 50 records.

Settle rule: push servers (pyright, ts6, gopls) wait for publishDiagnostics on every opened file plus 3s with no server traffic at all; pull servers (ts7, rust-analyzer) poll textDocument/diagnostic until two consecutive polls agree; rust-analyzer additionally waits for a quiescent experimental/serverStatus notification. Hard cap: 600s per project x server.

"Import noise" is a heuristic over the final diagnostics: pyright reportMissingImports/reportMissingModuleSource, TS codes 2307/2306/2792/7016, rust-analyzer unresolved-import, plus a generic message regex (cannot find module/package, could not be resolved, missing go.sum entry, ...). "Overwhelming noise" below means >= 100 noise diagnostics, or noise making up >= 70% of >= 20 diagnostics.

## Results

| Language | Repo | Server | Deps | Settled | Seconds | Diag E/W/I/H | Noise | Peak RSS MB | Notes |
|---|---|---|---|---|---:|---|---:|---:|---|
| go | XTLS/Xray-core | gopls-v0.23.0 | ok | True | 6.0 | 0/0/0/3 | 0 | 263 |  |
| go | caddyserver/caddy | gopls-v0.23.0 | ok | True | 5.9 | 0/0/0/0 | 0 | 386 |  |
| go | charmbracelet/bubbletea | gopls-v0.23.0 | ok | True | 4.8 | 0/0/0/0 | 0 | 323 |  |
| go | fatedier/frp | gopls-v0.23.0 | ok | True | 8.3 | 0/0/0/0 | 0 | 1128 |  |
| go | gin-gonic/gin | gopls-v0.23.0 | ok | True | 8.0 | 0/0/0/0 | 0 | 809 |  |
| go | jesseduffield/lazydocker | gopls-v0.23.0 | ok | True | 6.2 | 0/0/0/1 | 0 | 558 |  |
| go | junegunn/fzf | gopls-v0.23.0 | ok | True | 4.9 | 0/0/2/0 | 0 | 222 |  |
| go | nektos/act | gopls-v0.23.0 | ok | True | 5.1 | 0/0/0/0 | 0 | 202 |  |
| go | router-for-me/CLIProxyAPI | gopls-v0.23.0 | ok | True | 5.7 | 0/1/0/3 | 0 | 297 |  |
| go | spf13/cobra | gopls-v0.23.0 | ok | True | 4.5 | 0/0/0/0 | 0 | 162 |  |
| python | D4Vinci/Scrapling | pyright-1.1.414 | n/a | True | 4.6 | 0/0/0/0 | 0 | 216 |  |
| python | Graphify-Labs/graphify | pyright-1.1.414 | n/a | True | 6.0 | 1/0/0/102 | 0 | 328 |  |
| python | Panniantong/Agent-Reach | pyright-1.1.414 | n/a | True | 4.4 | 0/0/0/5 | 0 | 169 |  |
| python | TauricResearch/TradingAgents | pyright-1.1.414 | n/a | True | 5.7 | 2/0/0/0 | 0 | 210 |  |
| python | TheAlgorithms/Python | pyright-1.1.414 | n/a | True | 7.2 | 0/0/0/0 | 0 | 422 |  |
| python | Z4nzu/hackingtool | pyright-1.1.414 | n/a | True | 8.2 | 1/0/0/0 | 0 | 204 |  |
| python | browser-use/browser-use | pyright-1.1.414 | n/a | True | 5.3 | 0/0/0/0 | 0 | 287 |  |
| python | github/spec-kit | pyright-1.1.414 | n/a | True | 10.3 | 1/0/0/1 | 0 | 237 |  |
| python | hiyouga/LlamaFactory | pyright-1.1.414 | n/a | True | 5.3 | 0/0/0/0 | 0 | 163 |  |
| python | pallets/flask | pyright-1.1.414 | n/a | True | 4.4 | 5/2/0/5 | 5 | 199 |  |
| rust | AlexsJones/llmfit | rust-analyzer-2026-09-21 | ok | True | 139.0 | 0/0/0/0 | 0 | 3566 |  |
| rust | BurntSushi/ripgrep | rust-analyzer-2026-09-21 | ok | True | 21.8 | 0/0/0/0 | 0 | 781 |  |
| rust | FuelLabs/fuels-rs | rust-analyzer-2026-09-21 | ok | True | 194.8 | 0/0/0/0 | 0 | 2954 |  |
| rust | alacritty/alacritty | rust-analyzer-2026-09-21 | ok | True | 20.9 | 0/0/0/15 | 0 | 1315 |  |
| rust | dani-garcia/vaultwarden | rust-analyzer-2026-09-21 | ok | True | 109.1 | 1/0/0/8 | 0 | 2881 |  |
| rust | lapce/lapce | rust-analyzer-2026-09-21 | ok | True | 183.8 | 0/0/0/0 | 0 | 3256 |  |
| rust | rtk-ai/rtk | rust-analyzer-2026-09-21 | ok | True | 152.8 | 0/0/0/1 | 0 | 1395 |  |
| rust | rust-lang/rustlings | rust-analyzer-2026-09-21 | ok | True | 53.4 | 0/0/0/3 | 0 | 705 |  |
| rust | sharkdp/bat | rust-analyzer-2026-09-21 | ok | True | 30.4 | 0/0/0/1 | 0 | 1249 |  |
| rust | sxyazi/yazi | rust-analyzer-2026-09-21 | ok | True | 80.5 | 0/0/0/0 | 0 | 2573 |  |
| typescript | ChatGPTNextWeb/NextChat | ts6-6.0.3 | ok | True | 5.5 | 0/0/0/0 | 0 | 64 |  |
| typescript | ChatGPTNextWeb/NextChat | ts7-7.0.2 | ok | True | 1.6 | 0/0/0/0 | 0 | 193 |  |
| typescript | ChromeDevTools/chrome-devtools-mcp | ts6-6.0.3 | ok | True | 6.1 | 4/0/0/0 | 2 | 60 |  |
| typescript | ChromeDevTools/chrome-devtools-mcp | ts7-7.0.2 | ok | True | 1.7 | 4/0/0/0 | 2 | 223 |  |
| typescript | Fission-AI/OpenSpec | ts6-6.0.3 | ok | True | 4.4 | 0/0/0/1 | 0 | 64 |  |
| typescript | Fission-AI/OpenSpec | ts7-7.0.2 | ok | True | 1.6 | 0/0/0/0 | 0 | 119 |  |
| typescript | chenglou/pretext | ts6-6.0.3 | ok | True | 5.4 | 0/0/0/0 | 0 | 64 |  |
| typescript | chenglou/pretext | ts7-7.0.2 | ok | True | 1.7 | 0/0/0/0 | 0 | 225 |  |
| typescript | modelcontextprotocol/servers | ts6-6.0.3 | ok | True | 9.6 | 0/0/0/0 | 0 | 63 |  |
| typescript | modelcontextprotocol/servers | ts7-7.0.2 | ok | True | 1.7 | 0/0/0/0 | 0 | 146 |  |
| typescript | pmndrs/zustand | ts6-6.0.3 | ok | True | 5.1 | 9/0/0/0 | 5 | 59 |  |
| typescript | pmndrs/zustand | ts7-7.0.2 | ok | True | 1.6 | 9/0/0/0 | 5 | 70 |  |
| typescript | react-hook-form/react-hook-form | ts6-6.0.3 | ok | True | 4.0 | 11/0/0/0 | 6 | 64 |  |
| typescript | react-hook-form/react-hook-form | ts7-7.0.2 | ok | True | 1.6 | 11/0/0/0 | 6 | 77 |  |
| typescript | reduxjs/redux | ts6-6.0.3 | ok | True | 3.9 | 38/0/0/0 | 6 | 60 |  |
| typescript | reduxjs/redux | ts7-7.0.2 | ok | True | 1.5 | 38/0/0/0 | 6 | 56 |  |
| typescript | upstash/context7 | ts6-6.0.3 | ok | True | 5.3 | 0/0/0/0 | 0 | 64 |  |
| typescript | upstash/context7 | ts7-7.0.2 | ok | True | 1.6 | 0/0/0/0 | 0 | 104 |  |
| typescript | vercel/hyper | ts6-6.0.3 | ok | True | 4.8 | 1/0/0/1 | 1 | 64 |  |
| typescript | vercel/hyper | ts7-7.0.2 | ok | True | 1.7 | 1/0/0/1 | 1 | 140 |  |

## Recommended exclusions

None.

## Settle time by server (seconds; settled runs only)

- gopls: n=10 median=5.8s max=8.3s
- pyright: n=10 median=5.5s max=10.3s
- rust-analyzer: n=10 median=94.8s max=194.8s
- ts6: n=10 median=5.2s max=9.6s
- ts7: n=10 median=1.6s max=1.7s
