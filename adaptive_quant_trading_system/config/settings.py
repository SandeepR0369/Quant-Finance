"""Project settings and defaults.

Universe configuration:
- This file now imports a curated static universe from `src.config.universe`.
    The universe contains 50 large-cap liquid equities plus the index (SPY).

Keep this file minimal; change the universe in `src/config/universe.py`.
"""
from pathlib import Path

# Import the curated universe list (lightweight, static) and expose it to the
# rest of the codebase via SETTINGS['universe']. The loader/backtest expect a
# simple list of tickers.
from src.config.universe import normalized_universe

ROOT = Path(__file__).resolve().parents[1]

SETTINGS = {
        'project_root': str(ROOT),
        'data_dir': str(ROOT / 'data' / 'local_store'),
        'output_dir': str(ROOT / 'reports' / 'output'),
        'log_file': str(ROOT / 'logs' / 'project.log'),
        # Pull universe from curated module; this returns a cleaned list and
        # ensures the index (SPY) is present.
        'universe': normalized_universe(),
        'start_date': '2018-01-01',
        'end_date': '2023-12-31',
        'lookback': 63,
        'risk_aversion': 0.5,
        'initial_capital': 100000
}
