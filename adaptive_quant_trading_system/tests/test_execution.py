import pandas as pd
import numpy as np
from src.execution.executor import weights_to_shares, execute_market_orders


def make_sample():
    dates = pd.date_range('2020-01-01', periods=5, freq='D')
    prices = pd.DataFrame({'AAPL':[100,101,102,103,104],'MSFT':[200,201,198,202,205]}, index=dates)
    openp = prices
    high = prices * 1.01
    low = prices * 0.99
    return prices, openp, high, low


def test_weights_to_shares():
    prices, openp, high, low = make_sample()
    weights = pd.Series({'AAPL':0.6,'MSFT':0.4})
    nav = 100000
    shares = weights_to_shares(weights, nav, openp.iloc[0])
    assert shares['AAPL'] > 0
    assert shares['MSFT'] > 0


def test_execute_market_orders():
    prices, openp, high, low = make_sample()
    target_shares = pd.Series({'AAPL':10,'MSFT':5})
    current_shares = pd.Series({'AAPL':0,'MSFT':0})
    trades, cash_change, new_shares = execute_market_orders(target_shares, current_shares, openp.iloc[1], high.iloc[1], low.iloc[1], nav=100000, commission_perc=0.001, slippage_perc=0.001)
    assert not trades.empty
    assert 'exec_price' in trades.columns
    assert new_shares['AAPL'] == 10

