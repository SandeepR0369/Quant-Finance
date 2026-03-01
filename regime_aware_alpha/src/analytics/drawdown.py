import pandas as pd

def compute_drawdown(cumulative_returns: pd.Series):
    rolling_max = cumulative_returns.cummax()
    drawdown = cumulative_returns / rolling_max - 1
    return drawdown