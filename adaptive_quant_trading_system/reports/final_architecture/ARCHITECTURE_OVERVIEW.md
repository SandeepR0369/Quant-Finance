# Architecture Overview

This note explains how the project is organized and how data/commands flow through the system. It references the actual folder structure in the repository.

## Folder structure (relevant parts)
```
src/
  data/
    loader.py            # data ingestion & normalization
  indicators/
    indicators.py        # RSI, ATR, Bollinger etc.
  strategy/
    trend_momentum.py
    mean_reversion.py
  execution/
    executor.py          # simulate market/limit fills
  portfolio/
    accounting.py        # ledger, entry prices, pnl
  risk/
    risk_manager.py
    position_sizer.py
  backtest/
    engine.py            # orchestration: daily loop
  analytics/
    metrics.py           # cagr, sharpe, sortino, stop stats
  visualization/
    plots.py             # equity, drawdown, rolling sharpe
  optimization/
    optimizer.py         # grid search + walk-forward skeleton

reports/
  output/                # generated artifacts
  final_report/          # this document package

```

## Data flow
1. `main.py` calls `YahooDataLoader.download()` to retrieve a dict of DataFrames keyed by ticker.
2. `src/backtest/engine.py` builds `prices` frames from the loader output and passes data to the strategy's `generate_signals`.
3. Strategy returns a `pd.DataFrame` of target weights indexed by date; engine aligns weights to price index.
4. Sizing (`position_sizer`) computes volatility scaling; risk controller (`risk_manager`) may alter weights.
5. Engine calls `enforce_stops` to detect stop fills for t+1 intrabar and execute them before normal rebalancing.
6. Normal rebalancing uses `executor.execute_market_orders` to create fills at open(t+1) adjusted for slippage.
7. Fills are applied to `accounting.Account` to update holdings, entry prices and realized PnL.
8. At the end of the bar the engine `mark_to_market` the account using close(t+1) and records NAV.

## Execution flow (runtime ordering, critical)
- Signals at close(t)
- Volatility sizing & risk scaling
- Risk checks (drawdown, daily loss)
- RiskManager.set_entry_prices_from_account(account)
- RiskManager.update_trails(...) using last available prices
- RiskManager.enforce_stops(...) using t+1 high/low/open → execute stop trades
- Recompute holdings and zero out weights for stopped symbols
- Execute normal market rebalancing at t+1 open
- Apply trades to ledger and mark to market at t+1 close

This ordering ensures forced exits are final for that bar and prevents immediate re-entry, which is a key defensibility point.

## Risk flow
- Position sizing is performed pre-trade.
- Stop detection runs and produces concrete stop orders which the engine executes immediately.
- Drawdown and daily loss checks may halt the run entirely.

## Analytics & optimization flow
- After the run, engine calls analytics functions in `src/analytics/metrics.py` to produce `performance_report.yaml` and various charts saved to `reports/output/`.
- `src/optimization/optimizer.py` can be used to iterate parameter grids with a simple walk-forward split; it is designed for reproducible experiments rather than exhaustive hyper-optimization.

## Why this organization
- Single-responsibility modules are easier to test.
- Centralized data normalization avoids subtle bugs (KeyError: 'open').
- Clear ordering makes stop enforcement auditable and reproducible in a viva.

