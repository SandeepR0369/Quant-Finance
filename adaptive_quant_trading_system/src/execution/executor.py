"""Execution engine: converts target weights into orders and simulates fills.

Assumptions:
- Next-bar execution: signals at close(t) are executed at open(t+1).
- Market orders fill at next open price with slippage and commission applied.
- Limit orders simulated: if limit price reachable on that bar (within high/low), fill; otherwise remain unfilled.
"""
from typing import Dict, Tuple
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def weights_to_shares(weights: pd.Series, nav: float, open_prices: pd.Series) -> pd.Series:
    """Convert target weights (summing to 1) into share quantities using nav and open prices.

    weights: Series symbol->weight
    nav: float current portfolio value
    open_prices: Series symbol->price at which execution occurs
    """
    target_value = weights * nav
    shares = (target_value / open_prices).fillna(0).astype(float)
    return shares


def apply_slippage(price: float, slippage_perc: float, side: str = 'buy') -> float:
    """Apply slippage as a fraction of price. For buys, price increases; for sells, price decreases."""
    if price is None or np.isnan(price):
        return price
    if side == 'buy':
        return price * (1 + slippage_perc)
    else:
        return price * (1 - slippage_perc)


def execute_market_orders(target_shares: pd.Series,
                          current_shares: pd.Series,
                          open_prices: pd.Series,
                          high_prices: pd.Series,
                          low_prices: pd.Series,
                          nav: float,
                          commission_perc: float = 0.0005,
                          slippage_perc: float = 0.0005) -> Tuple[pd.DataFrame, float, pd.Series]:
    """Simulate market order execution at next open with slippage and commission.

    Returns:
    - trades_df: DataFrame of executed trades with columns [symbol, exec_price, shares, commission, slippage, side, value]
    - cash_change: float change in cash due to trades (negative means cash spent)
    - new_shares: Series of updated holdings after trades
    """
    trades = []
    new_shares = current_shares.copy().reindex(target_shares.index).fillna(0.0)
    cash_change = 0.0

    for sym in target_shares.index:
        tgt = float(target_shares.get(sym, 0.0))
        cur = float(current_shares.get(sym, 0.0))
        delta = tgt - cur
        if abs(delta) < 1e-8:
            continue
        side = 'buy' if delta > 0 else 'sell'
        # use open price for market order
        p_open = float(open_prices.get(sym, np.nan))
        if np.isnan(p_open):
            logger.debug('Missing open price for %s; skipping', sym)
            continue
        exec_price = apply_slippage(p_open, slippage_perc, side=side)
        shares = abs(delta)
        value = exec_price * shares
        commission = value * commission_perc
        cash_delta = -value if side == 'buy' else value
        cash_delta -= commission

        cash_change += cash_delta
        new_shares[sym] = cur + (delta)

        trades.append({'symbol': sym, 'exec_price': exec_price, 'shares': delta, 'commission': commission, 'slippage': exec_price - p_open, 'side': side, 'value': value})

    trades_df = pd.DataFrame(trades)
    return trades_df, cash_change, new_shares


def execute_limit_orders(limit_orders: pd.DataFrame,
                         current_shares: pd.Series,
                         open_prices: pd.Series,
                         high_prices: pd.Series,
                         low_prices: pd.Series,
                         commission_perc: float = 0.0005) -> Tuple[pd.DataFrame, pd.Series]:
    """Simulate limit orders provided as DataFrame with columns [symbol, limit_price, shares, side].

    If limit_price between low and high of the bar, assume filled at limit_price.
    Returns fills and updated holdings.
    """
    trades = []
    new_shares = current_shares.copy().reindex(limit_orders['symbol']).fillna(0.0)
    for _, row in limit_orders.iterrows():
        sym = row['symbol']
        limit = row['limit_price']
        shares = row['shares']
        side = row.get('side', 'buy')
        low = float(low_prices.get(sym, np.nan))
        high = float(high_prices.get(sym, np.nan))
        exec_price = None
        if np.isnan(low) or np.isnan(high):
            continue
        # If limit within today's range, fill
        if side == 'buy' and (limit >= low and limit <= high):
            exec_price = limit
        if side == 'sell' and (limit >= low and limit <= high):
            exec_price = limit
        if exec_price is None:
            continue
        value = exec_price * shares
        commission = value * commission_perc
        signed_shares = shares if side == 'buy' else -shares
        new_shares[sym] = new_shares.get(sym, 0.0) + signed_shares
        trades.append({'symbol': sym, 'exec_price': exec_price, 'shares': signed_shares, 'commission': commission, 'slippage': 0.0, 'side': side, 'value': value})

    trades_df = pd.DataFrame(trades)
    return trades_df, new_shares
