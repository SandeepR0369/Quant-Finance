
import pandas as pd
import numpy as np
from typing import List, Dict


def compute_drawdown(equity: pd.Series) -> pd.Series:
    """Return drawdown series (negative values)."""
    roll_max = equity.cummax()
    return (equity - roll_max) / roll_max


def cagr(equity: pd.Series) -> float:
    """Compound annual growth rate from equity series."""
    if equity.empty:
        return 0.0
    n_periods = len(equity)
    if n_periods <= 1:
        return 0.0
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    years = float(n_periods) / 252.0
    if years <= 0:
        return 0.0
    return (1 + total_return) ** (1 / years) - 1


def annualized_vol(returns: pd.Series) -> float:
    return float(returns.std() * np.sqrt(252)) if not returns.empty else 0.0


def sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    ar = (1 + returns.mean()) ** 252 - 1 if not returns.empty else 0.0
    vol = annualized_vol(returns)
    return float((ar - rf) / vol) if vol > 0 else 0.0


def sortino(returns: pd.Series, mar: float = 0.0) -> float:
    """Sortino ratio using MAR (minimum acceptable return) annualized."""
    if returns.empty:
        return 0.0
    dr = returns[returns < mar]
    downside = dr.std() * np.sqrt(252) if not dr.empty else 0.0
    ann_ret = (1 + returns.mean()) ** 252 - 1
    return float((ann_ret - mar) / downside) if downside > 0 else 0.0


def max_drawdown(equity: pd.Series) -> float:
    dd = compute_drawdown(equity)
    return float(dd.min()) if not dd.empty else 0.0


def calmar(equity: pd.Series) -> float:
    ann = cagr(equity)
    mdd = abs(max_drawdown(equity))
    return float(ann / mdd) if mdd > 0 else 0.0


def profit_factor(trades: pd.DataFrame) -> float:
    """Profit factor = gross wins / gross losses. trades must have 'value' and 'shares' and we compute pnl per trade if 'pnl' present or infer from sign/value."""
    if trades is None or trades.empty:
        return 0.0
    if 'pnl' in trades.columns:
        wins = trades.loc[trades['pnl'] > 0, 'pnl'].sum()
        losses = -trades.loc[trades['pnl'] < 0, 'pnl'].sum()
    else:
        # best-effort: assume positive value*shares implies buy or sell direction ambiguity; return NaN-like 0
        return 0.0
    return float(wins / losses) if losses > 0 else float('inf') if wins > 0 else 0.0


def win_rate(trades: pd.DataFrame) -> float:
    if trades is None or trades.empty or 'pnl' not in trades.columns:
        return 0.0
    wins = trades['pnl'] > 0
    return float(wins.sum() / len(trades))


def turnover(trades: pd.DataFrame, avg_aum: float) -> float:
    """Simple turnover: sum(|value exchanged|) / avg AUM over period."""
    if trades is None or trades.empty or avg_aum <= 0:
        return 0.0
    exchanged = trades['value'].abs().sum()
    return float(exchanged / avg_aum)


def stop_stats(stop_events: List[Dict]) -> Dict:
    """Compute simple stop-loss statistics from stop_events list of dicts.

    Expected keys: symbol, price, reason, exec_price, entry_price, date
    """
    if not stop_events:
        return {'n_stops': 0, 'avg_loss': 0.0, 'median_loss': 0.0}
    import math
    losses = []
    for e in stop_events:
        entry = e.get('entry_price')
        exec_p = e.get('price', e.get('exec_price'))
        if entry is None or exec_p is None:
            continue
        # loss from entry to stop for long positions
        losses.append((exec_p - entry) / (entry + 1e-9))
    if not losses:
        return {'n_stops': 0, 'avg_loss': 0.0, 'median_loss': 0.0}
    arr = np.array(losses)
    return {'n_stops': len(arr), 'avg_loss': float(arr.mean()), 'median_loss': float(np.median(arr))}


def regime_performance(returns: pd.Series, regimes: pd.Series) -> Dict:
    """Compute performance grouped by regime labels (regimes indexed like returns)."""
    out = {}
    if returns.empty or regimes is None:
        return out
    df = pd.DataFrame({'ret': returns}).join(regimes.rename('regime'))
    for name, g in df.groupby('regime'):
        out[name] = {
            'cagr': cagr((1 + g['ret']).cumprod()),
            'ann_vol': annualized_vol(g['ret']),
            'sharpe': sharpe(g['ret'])
        }
    return out


def rolling_sharpe(returns: pd.Series, window: int = 63) -> pd.Series:
    rs = returns.rolling(window).mean() / returns.rolling(window).std()
    return rs * np.sqrt(252)
