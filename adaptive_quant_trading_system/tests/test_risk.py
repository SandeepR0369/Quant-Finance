import pandas as pd
import numpy as np
from src.risk.position_sizer import volatility_based_weights, kelly_fraction
from src.risk.risk_manager import RiskManager


def make_prices():
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    data = pd.DataFrame({'AAPL':100+np.cumsum(np.random.randn(100)),'MSFT':200+np.cumsum(np.random.randn(100))}, index=dates)
    return data


def test_volatility_weights():
    p = make_prices()
    w = volatility_based_weights(p, lookback=20)
    assert isinstance(w, pd.Series)
    assert abs(w.sum() - 1.0) < 1e-6


def test_kelly_fraction():
    rets = pd.Series(np.random.randn(100)/100)
    k = kelly_fraction(rets)
    assert 0.0 <= k <= 1.0


def test_risk_manager():
    rm = RiskManager(max_daily_loss=0.01, max_portfolio_drawdown=0.5)
    rm.initialize(100000)
    snapshot = {'nav':100000}
    assert rm.check_portfolio_limits(snapshot)

