"""Lightweight optimizer: grid search + basic walk-forward splitter.

Developer note: keep simple and deterministic. This module runs backtests for each parameter set and collects a scoring metric.
Walk-forward is implemented by splitting date ranges into sequential train/test folds.
"""
from typing import Dict, List, Callable, Tuple
import itertools
import pandas as pd
import numpy as np


def grid_search(strategy_cls, param_grid: Dict[str, List], data: Dict[str, pd.DataFrame], backtester_factory: Callable, scoring: str = 'sharpe') -> List[Dict]:
    """Run simple grid search. Returns list of results sorted by score desc.

    backtester_factory(params) -> BacktestEngine instance to run.
    """
    keys = list(param_grid.keys())
    combos = list(itertools.product(*[param_grid[k] for k in keys]))
    results = []
    for c in combos:
        params = dict(zip(keys, c))
        strat = strategy_cls(**params)
        engine = backtester_factory(strat)
        res = engine.run()
        score = res['perf'].get(scoring, 0.0)
        results.append({'params': params, 'score': score, 'perf': res['perf']})
    results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
    return results_sorted


def walk_forward_split(dates: pd.DatetimeIndex, train_window: int, test_window: int, step: int) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    """Return list of (train_idx, test_idx) date ranges; windows in days. Simple, non-overlapping test windows."""
    res = []
    start = dates[0]
    end = dates[-1]
    cur = start
    while True:
        train_start = cur
        train_end = train_start + pd.Timedelta(days=train_window)
        test_start = train_end
        test_end = test_start + pd.Timedelta(days=test_window)
        if test_end > end:
            break
        train_idx = dates[(dates >= train_start) & (dates < train_end)]
        test_idx = dates[(dates >= test_start) & (dates < test_end)]
        if len(train_idx) == 0 or len(test_idx) == 0:
            break
        res.append((train_idx, test_idx))
        cur = cur + pd.Timedelta(days=step)
    return res
