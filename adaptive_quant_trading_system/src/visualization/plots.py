"""Visualization helpers: basic, professional-looking charts for backtest outputs.

Developer note: keep functions small and pure; they accept dataframes/series and return path where image saved.
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path


def _style():
    plt.style.use('seaborn-darkgrid')


def plot_equity(equity: pd.Series, trades: pd.DataFrame = None, stops: pd.DataFrame = None, regimes: pd.Series = None, out_path: Path = None):
    _style()
    fig, ax = plt.subplots(figsize=(12, 6))
    equity.plot(ax=ax, label='Equity')
    ax.set_ylabel('Portfolio Value')
    ax.set_title('Equity Curve')

    # plot buy/sell markers from trades
    if trades is not None and not trades.empty:
        buys = trades[trades['shares'] > 0]
        sells = trades[trades['shares'] < 0]
        if not buys.empty:
            for _, r in buys.iterrows():
                if 'date' in r:
                    ax.scatter(r['date'], equity.loc[r['date']], marker='^', color='green', s=40, zorder=5)
        if not sells.empty:
            for _, r in sells.iterrows():
                if 'date' in r:
                    ax.scatter(r['date'], equity.loc[r['date']], marker='v', color='red', s=40, zorder=5)

    # stop markers
    if stops is not None and not stops.empty:
        for _, r in stops.iterrows():
            if 'date' in r and r['date'] in equity.index:
                ax.scatter(r['date'], equity.loc[r['date']], marker='x', color='orange', s=60, zorder=6)

    # regime shading
    if regimes is not None and not regimes.empty:
        # simple approach: find contiguous blocks where regime == value
        prev = None
        start = None
        for dt, v in regimes.items():
            if prev is None:
                prev = v
                start = dt
                continue
            if v != prev:
                # shade
                ax.axvspan(start, dt, alpha=0.08, color='grey' if prev == 'low' else 'lightblue')
                start = dt
                prev = v
        # final span
        if start is not None:
            ax.axvspan(start, regimes.index[-1], alpha=0.08, color='grey')

    if out_path is None:
        out_path = Path('reports/output/equity_curve.png')
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_drawdown(equity: pd.Series, out_path: Path = None):
    _style()
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max
    fig, ax = plt.subplots(figsize=(12, 4))
    drawdown.plot(ax=ax)
    ax.set_title('Drawdown')
    if out_path is None:
        out_path = Path('reports/output/drawdown.png')
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_rolling_sharpe(returns: pd.Series, window: int = 63, out_path: Path = None):
    _style()
    rs = returns.rolling(window).mean() / returns.rolling(window).std()
    rs = rs * np.sqrt(252)
    fig, ax = plt.subplots(figsize=(12, 4))
    rs.plot(ax=ax)
    ax.set_title(f'Rolling Sharpe (window={window})')
    if out_path is None:
        out_path = Path('reports/output/rolling_sharpe.png')
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_allocation(weights_df: pd.DataFrame, out_path: Path = None):
    _style()
    fig, ax = plt.subplots(figsize=(12, 4))
    weights_df.fillna(0).plot.area(ax=ax)
    ax.set_title('Allocation Over Time')
    if out_path is None:
        out_path = Path('reports/output/allocation.png')
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
