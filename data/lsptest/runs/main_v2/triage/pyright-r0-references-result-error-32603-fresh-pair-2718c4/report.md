# [pyright 1.1.414] references fails with an internal error (-32603) in a fresh session

Draft for the author (not filed). Group `pyright-r0-references-result-error-32603-fresh-pair-2718c4`, signature `pyright|r0_crash|references:result->error:-32603`, case family `fresh-pair`.

## Server

- pyright 1.1.414; launch `~/.local/state/fnm_multishells/54519_1794979407073/bin/node temp/lsp_servers/pyright-1.1.414/node_modules/pyright/langserver.index.js --stdio`; entry sha256 f200762078eb9880; package version 1.1.414; node v24.3.0
- project `virattt/ai-hedge-fund@7d897a002c26` (corpus, commit 7d897a002c263f106201154d877a4bcf74efae03), language python

## Relation violated

A request on an unmodified project must not fail with an internal error, kill the server or time out; here it does so in two independent fresh sessions (R0 crash check).

## Minimal steps (LSP)

1. Start pyright 1.1.414 on the project root; answer workspace/configuration with the settings under Environment.
2. didOpen every target file, wait until the server is idle, then send the queries; the failing request is below.
3. Query `textDocument/references` on `hedge_fund/backtesting/__init__.py` line 3, column 22 (LSP position {line: 2, character: 21}); it fails like this in two independent fresh sessions (expected: an answer).

## Expected vs actual

Expected (fresh session / reference):

```json
"an answer that is not a server error, a crash or a timeout"
```

Actual:

```json
[
 "error",
 -32603
]
```

Project file `hedge_fund/backtesting/__init__.py`:

```
   1 | """v2 backtesting — simulate a fund (or a single alpha model) over history."""
     ...
   3 | from hedge_fund.backtesting.engine import BacktestEngine
   4 | from hedge_fund.backtesting.fund import (
   5 |     FundBacktestMetrics,
   6 |     FundBacktestResult,
   7 |     backtest_fund,
   8 |     rebalance_grid,
   9 | )
  10 | from hedge_fund.backtesting.models import (
  11 |     BacktestResult,
  12 |     PerformanceMetrics,
  13 |     Trade,
  14 | )
     ...
  16 | __all__ = [
  17 |     "BacktestEngine",
  18 |     "BacktestResult",
  19 |     "FundBacktestMetrics",
  20 |     "FundBacktestResult",
  21 |     "PerformanceMetrics",
  22 |     "Trade",
  23 |     "backtest_fund",
  24 |     "rebalance_grid",
  25 | ]
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/pyright-r0-references-result-error-32603-fresh-pair-2718c4/repro.json
```

## Evidence and reduction

- representative 0cc564977c8a-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 1 violation(s) in 1 run(s), projects virattt/ai-hedge-fund@7d897a002c26, timings settled, seeds 1

## Possibly related issues (search results, to be checked by the author)

- [microsoft/pyright#11041](https://github.com/microsoft/pyright/issues/11041) Avoid triggering reportUnreachable on exception raising? (open, 2025-10-17, 5 comments)
- [microsoft/pyright#11366](https://github.com/microsoft/pyright/issues/11366) Inconsistent error reporting for function return type based on which exception is raised (closed, 2026-04-07, 2 comments)
- [microsoft/pyright#11186](https://github.com/microsoft/pyright/issues/11186) Pyright fails to flag illegal generic exception in except clause (closed, 2025-12-23, 1 comments)
- [microsoft/pyright#10546](https://github.com/microsoft/pyright/issues/10546) Add support for Python 3.14 multi-exception syntax (closed, 2025-06-05, 1 comments)
- [microsoft/pyright#9717](https://github.com/microsoft/pyright/issues/9717) Reachability analysis does not understand control flow exceptions (StopIteration) (closed, 2025-01-16, 2 comments)
- [microsoft/pyright#5588](https://github.com/microsoft/pyright/issues/5588) node report issues - JavaScript heap out of memory (closed, 2023-07-27, 3 comments)
- [microsoft/pyright#5689](https://github.com/microsoft/pyright/issues/5689) pyright shuts down on opening python file - used with eglot and emacs 29.1 (closed, 2023-08-11, 1 comments)
- [microsoft/pyright#3239](https://github.com/microsoft/pyright/issues/3239) Out of memory crash pyright-langserver (closed, 2022-03-23, 28 comments)
- queries: `"Debug Failure. Did not find evaluation scope" repo:microsoft/pyright is:issue`; `exception in:title repo:microsoft/pyright is:issue`; `references "internal error" repo:microsoft/pyright is:issue`; `references exception repo:microsoft/pyright is:issue`

## Server log excerpt (last confirming replay)

```
[pyright-1.1.414-tr2718c4-r0-replay-baseline-20261118-223636-31cdfb] textDocument/references -> error -32603: Request textDocument/references failed with message: Debug Failure. Did not find evaluation scope
[pyright-1.1.414-tr2718c4-r0-replay-control-20261118-223636-8590fd] textDocument/references -> error -32603: Request textDocument/references failed with message: Debug Failure. Did not find evaluation scope
```
