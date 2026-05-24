import pandas as pd
import numpy as np

from src.optimization import optimizer


class DummyStrategy:
    def __init__(self, param_a=1):
        self.param_a = param_a

    def generate_signals(self, data):
        # trivial: make weights proportional to param_a
        dates = list(data.values())[0].index
        cols = list(data.keys())
        df = pd.DataFrame(0.0, index=dates, columns=cols)
        df.iloc[:, 0] = 1.0 * self.param_a
        return df


class DummyEngine:
    def __init__(self, strat):
        self.strat = strat

    def run(self):
        # return fake perf depending on param
        score = float(self.strat.param_a)
        return {'perf': {'sharpe': score}}


def backtester_factory(strat):
    return DummyEngine(strat)


def test_grid_search_basic():
    data = {'A': pd.DataFrame({'adj_close': [1, 2, 3]}, index=pd.date_range('2020-01-01', periods=3))}
    grid = {'param_a': [0.5, 1.0, 2.0]}
    results = optimizer.grid_search(DummyStrategy, grid, data, lambda s: backtester_factory(s), scoring='sharpe')
    assert results[0]['score'] == 2.0
