import pandas as pd
import numpy as np

from src.risk.risk_manager import RiskManager
from src.portfolio.accounting import Account


def make_account(symbols, cash=100000):
    acc = Account(initial_cash=cash, symbols=symbols)
    return acc


def test_fixed_stop_trigger():
    symbols = ['AAPL']
    acc = make_account(symbols)
    # buy 10 shares at entry price 100
    acc.holdings['AAPL'] = 10
    acc.entry_price['AAPL'] = 100.0
    rm = RiskManager(stop_loss_pct=0.05)
    rm.set_entry_prices_from_account(acc)
    # simulate next bar with low that breaches stop (<=95)
    high = pd.Series({'AAPL': 101.0})
    low = pd.Series({'AAPL': 94.0})
    open_p = pd.Series({'AAPL': 100.5})
    stops, new_pos = rm.enforce_stops(acc.holdings, high, low, open_prices=open_p)
    assert len(stops) == 1
    assert new_pos['AAPL'] == 0.0


def test_trailing_stop_trigger():
    symbols = ['MSFT']
    acc = make_account(symbols)
    acc.holdings['MSFT'] = 20
    acc.entry_price['MSFT'] = 200.0
    rm = RiskManager(trailing_stop_pct=0.1)
    rm.set_entry_prices_from_account(acc)
    # set an existing trail at 180 (10% below 200)
    rm.trail_levels['MSFT'] = 180.0
    high = pd.Series({'MSFT': 185.0})
    low = pd.Series({'MSFT': 170.0})
    open_p = pd.Series({'MSFT': 182.0})
    stops, new_pos = rm.enforce_stops(acc.holdings, high, low, open_prices=open_p)
    assert any(s['reason'] == 'trailing' for s in stops)
    assert new_pos['MSFT'] == 0.0


def test_portfolio_drawdown_halt():
    symbols = ['AAPL']
    acc = make_account(symbols, cash=1000)
    acc.holdings['AAPL'] = 10
    acc.entry_price['AAPL'] = 100.0
    acc.cash = 0.0
    acc.mark_to_market(pd.Series({'AAPL': 50.0}))
    rm = RiskManager(max_portfolio_drawdown=0.2)
    rm.initialize(1000)
    # now account nav is 500, which is 50% drawdown -> should halt
    ok = rm.check_portfolio_limits(acc.snapshot())
    assert not ok
