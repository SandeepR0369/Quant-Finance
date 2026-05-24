"""Regime detection module.

Simple regime classification based on rolling market volatility (std of returns)
or ATR on a market index. Returns a Series with values 'low' or 'high' (or 0/1 flag)
that can be used to scale exposure.
"""
from typing import Optional
import pandas as pd
import numpy as np
from src.indicators.indicators import atr


def detect_regime(prices: pd.Series, window: int = 63, method: str = 'std', threshold: float = 1.0) -> pd.Series:
    """Detect regimes: 'low' or 'high' volatility.

    - method='std': compute rolling std of returns; mark 'high' when std > threshold * long-term median
    - method='atr': compute ATR and compare to rolling median

    Returns Series indexed like prices with values 'low' or 'high'.
    """
    if method == 'std':
        rets = prices.pct_change().fillna(0)
        roll = rets.rolling(window).std()
        med = roll.median()
        # threshold scales median; if threshold=1.0, high when roll > median
        flag = pd.Series(np.where(roll > (threshold * med), 'high', 'low'), index=prices.index)
        return flag
    elif method == 'atr':
        # expect prices to be a DataFrame for atr; here we accept Series and treat high/low near close
        if isinstance(prices, pd.Series):
            df = pd.DataFrame({'open': prices, 'high': prices, 'low': prices, 'close': prices})
        else:
            df = prices
        a = atr(df['high'], df['low'], df['close'], length=window)
        med = a.median()
        flag = pd.Series(np.where(a > (threshold * med), 'high', 'low'), index=a.index)
        return flag
    else:
        raise ValueError('Unknown method')
