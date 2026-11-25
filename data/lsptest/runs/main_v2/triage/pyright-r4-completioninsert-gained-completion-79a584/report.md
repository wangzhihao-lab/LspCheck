# [pyright 1.1.414] completion edit is not valid (completionInsert:gained)

Draft for the author (not filed). Group `pyright-r4-completioninsert-gained-completion-79a584`, signature `pyright|r4_edits|completionInsert:gained`, case family `completion`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `virattt/ai-hedge-fund@7d897a002c26` (corpus, commit 7d897a002c263f106201154d877a4bcf74efae03), language python

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/completion` on `hedge_fund/event_study/__main__.py` at line 60, column 9 (LSP position {line: 59, character: 8}); insert the item: the file must not gain a syntax error.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "future feature _VersionInfo is not defined"
]
```

Project file `hedge_fund/event_study/__main__.py`:

```
   1 | """Run the event study engine. Screen-record friendly output.
     ...
   3 | Usage: poetry run python -m hedge_fund.event_study
   4 | """
     ...
   6 | from __future__ import annotations
     ...
   8 | import sys
   9 | import time
     ...
  11 | from hedge_fund.data import FDClient
  12 | from hedge_fund.event_study import compute_car
     ...
  15 | TICKERS = [
  16 |     # Tech (21)
  17 |     "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "NFLX", "CRM", "ADBE",
  18 |     "ORCL", "INTC", "AMD", "CSCO", "IBM", "UBER", "SHOP", "SNOW", "PLTR", "PANW", "CRWD",
  19 |     # Financials (15)
  20 |     "JPM", "GS", "BAC", "WFC", "MS", "C", "BLK", "SCHW", "AXP", "COF",
  21 |     "USB", "PNC", "TFC", "BK", "CME",
  22 |     # Healthcare (15)
  23 |     "JNJ", "PFE", "UNH", "MRK", "LLY", "ABBV", "TMO", "ABT", "BMY", "AMGN",
  24 |     "GILD", "ISRG", "VRTX", "REGN", "MDT",
  25 |     # Energy (8)
  26 |     "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX",
  27 |     # Consumer / Retail (15)
  28 |     "HD", "LOW", "COST", "WMT", "KO", "PEP", "MCD", "SBUX", "NKE", "TGT",
  29 |     "TJX", "ROST", "DG", "DLTR", "YUM",
  30 |     # Industrials (10)
  31 |     "CAT", "DE", "HON", "UPS", "RTX", "BA", "LMT", "GE", "MMM", "UNP",
  32 |     # Media / Telecom (7)
  33 |     "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "WBD",
  34 |     # Other (10)
  35 |     "V", "MA", "PYPL", "NEE", "D", "SO", "DUK", "ABNB", "COIN", "NOW",
  36 | ]
  37 | EARNINGS_LIMIT = 8
     ...
  39 | GREEN = "\033[32m"
  40 | RED = "\033[31m"
  41 | DIM = "\033[90m"
  42 | RESET = "\033[0m"
     ...
  45 | def progress(text: str) -> None:
  46 |     sys.stdout.write(f"\r{text}")
  47 |     sys.stdout.flush()
     ...
  50 | def typed(text: str, delay: float = 0.02) -> None:
  51 |     for ch in text:
  52 |         sys.stdout.write(ch)
  53 |         sys.stdout.flush()
  54 |         time.sleep(delay)
  55 |     sys.stdout.write("\n")
  56 |     sys.stdout.flush()
     ...
  59 | def color_car(v: float | None) -> str:
  60 |     if v is None:
  61 |         return f"{DIM}{'N/A':>8}{RESET}"
  62 |     pct = v * 100
  63 |     s = f"{pct:+7.2f}%"
  64 |     c = GREEN if pct >= 0 else RED
  65 |     return f"{c}{s}{RESET}"
     ...
  68 | def color_eps(s: str | None) -> str:
  69 |     if s == "BEAT":
  70 |         return f"{GREEN}BEAT{RESET}"
  71 |     if s == "MISS":
  72 |         return f"{RED}MISS{RESET}"
  73 |     if s == "MEET":
  74 |         return "MEET"
  75 |     return f"{DIM}   -{RESET}"
     ...
  78 | def main() -> None:
  79 |     import logging
  80 |     logging.getLogger("hedge_fund.data.client").setLevel(logging.ERROR)
     ...
  82 |     n = len(TICKERS)
     ...
  84 |     # Fetch with progress
  85 |     progress(f"Fetching data... [0/{n}]")
  86 |     with FDClient() as fd:
  87 |         from datetime import date
  88 |         spy_prices = fd.get_prices("SPY", "2023-01-01", date.today().isoformat())
  89 |         spy_closes = {p.time[:10]: p.close for p in spy_prices}
     ...
  91 |         from hedge_fund.event_study.engine import _compute_ticker_events
  92 |         all_events = []
  93 |         for i, ticker in enumerate(TICKERS):
  94 |             progress(f"Fetching data... [{i + 1}/{n}] {ticker}")
  95 |             events = _compute_ticker_events(ticker, fd, spy_closes, earnings_limit=EARNINGS_LIMIT)
  96 |             all_events.extend(events)
     ...
  98 |     # Filter to labeled events only
  99 |     all_events = [e for e in all_events if e.eps_surprise is not None]
     ...
 101 |     # Aggregate
 102 |     from hedge_fund.event_study.engine import _aggregate
 103 |     aggregates = _aggregate(all_events, 10_000, 42)
     ...
 105 |     # Clear progress line
 106 |     sys.stdout.write("\r" + " " * 60 + "\r")
 107 |     sys.stdout.flush()
     ...
 109 |     typed(f"Event Study: {len(all_events)} earnings events across {len(set(e.ticker for e in all_events))} tickers")
 110 |     print()
     ...
 112 |     print(f"  {'Ticker':<6} {'Date':<12} {'Type':<6} {'EPS':<4}  {'CAR[0,1]':>8} {'CAR[0,5]':>8} {'CAR[0,20]':>8}   {'Beta':>5} {'R2':>5}")
 113 |     print(f"  {'-' * 78}")
     ...
 115 |     for e in sorted(all_events, key=lambda x: (x.ticker, x.event_date)):
 116 |         eps = color_eps(e.eps_surprise)
 117 |         c1 = color_car(e.car_0_1)
 118 |         c5 = color_car(e.car_0_5)
 119 |         c20 = color_car(e.car_0_20)
     ...
 121 |         print(
 122 |             f"  {e.ticker:<6} {e.event_date:<12} {e.source_type:<6} {eps}"
 123 |             f"  {c1} {c5} {c20}"
 124 |             f"   {e.market_model.beta:5.2f} {e.market_model.r_squared:5.2f}"
 125 |         )
 126 |         time.sleep(0.6)
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r4-completioninsert-gained-completion-79a584/repro.json
```

## Evidence and reduction

- representative 41dcb7100681-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects virattt/ai-hedge-fund@7d897a002c26, timings settled, seeds 2

## Possibly related issues (search results, to be checked by the author)

- none found
- queries: `completionInsert unexpected repo:microsoft/pyright is:issue`; `completionInsert "wrong edit" repo:microsoft/pyright is:issue`
