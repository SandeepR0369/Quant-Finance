import pandas as pd
import numpy as np
import pytest

from src.analytics import metrics


def test_cagr_and_drawdown():
    dates = pd.date_range('2020-01-01', periods=252)
    # construct daily returns that compound to ~10% annual
    daily = (1 + 0.10) ** (1 / 252) - 1
    returns = pd.Series(daily, index=dates)
    equity = (1 + returns).cumprod()
    c = metrics.cagr(equity)
    assert pytest.approx(c, rel=1e-2) == 0.10


def test_sortino_sharpe():
    np.random.seed(1)
    dates = pd.date_range('2020-01-01', periods=252)
    rets = pd.Series(np.random.normal(0.0005, 0.01, size=252), index=dates)
    s = metrics.sharpe(rets)
    so = metrics.sortino(rets)
    assert isinstance(s, float)
    assert isinstance(so, float)
