# Adaptive Quant Trading System

Lightweight, modular quantitative trading framework for backtesting simple adaptive strategies.

Run the project:

1. Create and activate a Python 3.11 virtualenv.
2. pip install -r requirements.txt
3. python main.py

Outputs (charts, logs, reports) will be saved in `reports/output/`.

Notes and quick tips:

- Universe: the project uses a curated 50-stock liquid universe plus the ETF index SPY by default. See `src/config/universe.py` to view or change the static list. For quick smoke runs or CI, temporarily reduce the universe to 2–4 tickers in `config/settings.py`.
- Key output artifacts (saved by the backtest engine):
	- `reports/output/equity_curve.png`
	- `reports/output/drawdown.png`
	- `reports/output/rolling_sharpe.png`
	- `reports/output/trade_logs.csv`
	- `reports/output/stop_events.csv`
	- `reports/output/performance_report.yaml`

CI / Smoke-test suggestion:

To avoid long downloads in automated CI, run unit tests only by default and add one optional smoke test job that runs the backtest on a 2–3 symbol universe and a short date range. This keeps the CI fast while preserving reproducibility for manual/full runs.
