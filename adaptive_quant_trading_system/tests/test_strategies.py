import pandas as pd
import numpy as np
from src.strategy.trend_momentum import TrendMomentumStrategy
from src.strategy.mean_reversion import MeanReversionStrategy


def make_panel(symbols=['A','B','C'], periods=100):
    dates = pd.date_range('2020-01-01', periods=periods, freq='D')
    data = {}
    for s in symbols:
        close = 100 + np.cumsum(np.random.randn(periods))
        df = pd.DataFrame({'adj_close': close, 'open': close, 'high': close*1.01, 'low': close*0.99, 'volume': np.random.randint(100,1000,periods)}, index=dates)
        data[s] = df
    return data


def test_trend_momentum_signals():
    data = make_panel(['AAPL','MSFT','SPY'], periods=120)
    strat = TrendMomentumStrategy(ma_fast=5, ma_slow=20, top_n=2)
    pos = strat.generate_signals(data)
    assert isinstance(pos, pd.DataFrame)
    assert set(['AAPL','MSFT','SPY']).issubset(pos.columns)


def test_mean_reversion_signals():
    data = make_panel(['AAPL','MSFT','SPY'], periods=120)
    strat = MeanReversionStrategy(top_n=2)
    pos = strat.generate_signals(data)
    assert isinstance(pos, pd.DataFrame)
    assert pos.shape[1] >= 3
