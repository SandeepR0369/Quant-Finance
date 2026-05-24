"""Portfolio accounting: maintain cash, holdings, realized/unrealized PnL and NAV."""
from typing import Dict, Tuple
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class Account:
    def __init__(self, initial_cash: float, symbols: list):
        self.cash = float(initial_cash)
        self.holdings = pd.Series(0.0, index=symbols, dtype=float)
        # track average entry price per symbol for stop calculations and realized PnL
        self.entry_price = pd.Series(np.nan, index=symbols, dtype=float)
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.nav = float(initial_cash)

    def apply_trades(self, trades: pd.DataFrame):
        """Apply trade rows with columns [symbol, exec_price, shares, commission, value]."""
        if trades is None or trades.empty:
            return
        # apply each trade and maintain entry price and realized PnL
        for _, row in trades.iterrows():
            sym = row['symbol']
            shares = float(row['shares'])
            price = float(row['exec_price'])
            commission = float(row.get('commission', 0.0))
            # buy reduces cash, sell increases cash
            cash_delta = -price * shares - commission
            self.cash += cash_delta

            prev = float(self.holdings.get(sym, 0.0))
            new = prev + shares

            # update realized PnL when reducing or reversing a position
            if prev != 0 and np.sign(prev) != 0 and np.sign(shares) != 0 and np.sign(prev) != np.sign(new):
                # closing or reversing: compute closed portion
                closed = min(abs(prev), abs(shares))
                entry = float(self.entry_price.get(sym, np.nan))
                if not np.isnan(entry):
                    # if we were long and sold, pnl = closed * (sell_price - entry)
                    pnl = 0.0
                    if prev > 0:  # long being sold
                        pnl = closed * (price - entry)
                    else:  # short being covered
                        pnl = closed * (entry - price)
                    self.realized_pnl += pnl

            # update holdings
            self.holdings[sym] = new

            # update or clear entry price
            if new == 0:
                # position fully closed
                self.entry_price[sym] = np.nan
            else:
                # if adding to an existing position with same sign, update weighted avg
                prev_entry = float(self.entry_price.get(sym, np.nan))
                if np.isnan(prev_entry) or np.sign(prev) == 0 or np.sign(prev) == np.sign(shares):
                    # new average price
                    total_cost_prev = prev * (prev_entry if not np.isnan(prev_entry) else 0.0)
                    total_cost_new = total_cost_prev + shares * price
                    self.entry_price[sym] = total_cost_new / new
                else:
                    # reversing handled above; set entry for remaining portion
                    remaining = new
                    self.entry_price[sym] = price

    def mark_to_market(self, prices: pd.Series):
        """Update unrealized PnL and NAV using given price series for holdings."""
        # assume prices contains current market prices
        # compute unrealized using entry prices for correct PnL accounting
        mv = 0.0
        unreal = 0.0
        for sym, qty in self.holdings.items():
            p = float(prices.get(sym, np.nan))
            if np.isnan(p) or qty == 0:
                continue
            mv += qty * p
            entry = float(self.entry_price.get(sym, np.nan))
            if np.isnan(entry):
                # fallback: assume zero cost basis
                unreal += qty * p
            else:
                if qty > 0:
                    unreal += qty * (p - entry)
                else:
                    unreal += abs(qty) * (entry - p)

        self.unrealized_pnl = unreal
        self.nav = self.cash + mv
        return self.nav

    def snapshot(self) -> Dict:
        return {
            'cash': self.cash,
            'holdings': self.holdings.copy(),
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'nav': self.nav
        }
