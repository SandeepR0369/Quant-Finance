import numpy as np
import pandas as pd
from config.settings import TRADING_DAYS

def compute_cagr(returns: pd.Series):
    cumulative = (1 + returns).cumprod()
    years = len(returns) / TRADING_DAYS
    return cumulative.iloc[-1]

def compute_annualized_volatility(returns: pd.Series):
    return returns.std() * np.sqrt(TRADING_DAYS)

def compute_sharpe_ratio(returns: pd.Series, rf: float):
    excess_return = returns.mean()*TRADING_DAYS - rf
    vol = compute_annualized_volatility(returns)
    return excess_return / vol