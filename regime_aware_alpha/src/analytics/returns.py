import numpy as np
import pandas as pd

def compute_simple_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().dropna()

def compute_log_returns(prices: pd.Series) -> pd.Series:
    return np.log(prices / prices.shift(1)).dropna()