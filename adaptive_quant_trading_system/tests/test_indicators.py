import pandas as pd
import numpy as np
from src.indicators.indicators import attach_indicators


def make_sample():
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    close = 100 + np.cumsum(np.random.randn(len(dates)))
    data = pd.DataFrame({'close': close, 'volume': np.random.randint(100, 1000, len(dates))}, index=dates)
    data['open'] = data['close']
    data['high'] = data['close'] * 1.01
    data['low'] = data['close'] * 0.99
    return data


def test_attach_indicators_smoke():
    df = make_sample()
    out = attach_indicators(df, rsi_lengths=[14], atr_lengths=[14], ma_lengths=[20])
    # check expected columns exist
    assert 'rsi_14' in out.columns
    assert 'atr_14' in out.columns
    assert 'sma_20' in out.columns
    assert 'ema_20' in out.columns
