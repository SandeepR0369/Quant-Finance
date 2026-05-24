"""Position sizing utilities.

Provides volatility-based sizing and optional Kelly criterion sizing.
"""
from typing import Dict
import pandas as pd
import numpy as np


def volatility_based_weights(price_df: pd.DataFrame, lookback: int = 63, target_vol: float = 0.10) -> pd.Series:
    """Compute volatility-based weights across columns using historical returns.

    - price_df: DataFrame of close prices indexed by date, columns are symbols
    - lookback: window to compute realized volatility
    - target_vol: target annualized portfolio volatility (e.g., 0.10 for 10%)

    Returns a Series of weights summing to 1 (or zeros if no data).
    Approach:
    - compute annualized vol per asset: vol_i = std(returns_i) * sqrt(252)
    - raw weight proportional to 1/vol_i
    - normalize to sum to 1
    - scale per target_vol is left for portfolio-level application
    """
    rets = price_df.pct_change().dropna()
    if rets.empty:
        return pd.Series(0.0, index=price_df.columns)
    vol = rets.rolling(lookback).std().iloc[-1] * (252 ** 0.5)
    # use bfill/ffill to be compatible with older/newer pandas versions
    vol = vol.replace(0, np.nan).bfill().ffill().fillna(1e-6)
    inv = 1.0 / vol
    weights = inv / inv.sum()
    return weights.fillna(0.0)


def kelly_fraction(returns: pd.Series, shrink: float = 0.5) -> float:
    """Compute Kelly fraction based on historical returns series.

    Kelly = mean / var. We shrink towards 0 with `shrink` to reduce aggressiveness.
    Returns fractional Kelly between 0 and 1.
    """
    if returns is None or len(returns) < 2:
        return 0.0
    mu = returns.mean()
    var = returns.var()
    if var <= 0:
        return 0.0
    k = mu / var
    k = max(0.0, min(1.0, k * shrink))
    return float(k)
