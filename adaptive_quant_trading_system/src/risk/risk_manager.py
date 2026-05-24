"""Risk manager: enforces position sizing, stops, daily loss and drawdown limits."""
from typing import Dict, Any
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self,
                 max_daily_loss: float = 0.02,  # fraction of NAV
                 max_portfolio_drawdown: float = 0.2,  # fraction
                 stop_loss_pct: float = 0.05,  # fixed stop-loss per position
                 trailing_stop_pct: float = 0.1,  # trailing stop
                 volatility_target: float = 0.10,  # target portfolio vol
                 use_kelly: bool = False):
        self.max_daily_loss = max_daily_loss
        self.max_portfolio_drawdown = max_portfolio_drawdown
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.volatility_target = volatility_target
        self.use_kelly = use_kelly

        # stateful tracking
        self.peak_nav = None
        self.daily_loss_today = 0.0
        self.trail_levels = {}  # symbol -> trailing stop price
        # entry prices tracked externally via Account but keep local view for quick checks
        self.entry_prices = {}  # symbol -> entry price
        # stop event log
        self.stop_events = []

    def initialize(self, starting_nav: float):
        self.peak_nav = starting_nav

    def check_portfolio_limits(self, account_snapshot: Dict[str, Any]) -> bool:
        """Return True if portfolio is allowed to continue trading, False if halted due to drawdown."""
        nav = account_snapshot['nav']
        if self.peak_nav is None:
            self.peak_nav = nav
        if nav > self.peak_nav:
            self.peak_nav = nav
        drawdown = (self.peak_nav - nav) / (self.peak_nav + 1e-9)
        if drawdown > self.max_portfolio_drawdown:
            logger.warning('Portfolio halted: drawdown %.2f exceeds max %.2f', drawdown, self.max_portfolio_drawdown)
            return False
        return True

    def apply_daily_loss(self, account_snapshot: Dict[str, Any], loss_amount: float) -> bool:
        """Apply realized loss for the day; return False if daily limit exceeded."""
        nav = account_snapshot['nav']
        self.daily_loss_today += loss_amount
        if self.daily_loss_today / (nav + 1e-9) > self.max_daily_loss:
            logger.warning('Daily loss limit exceeded: %.4f of NAV', self.daily_loss_today / nav)
            return False
        return True

    def enforce_stops(self, positions: pd.Series, high_prices: pd.Series, low_prices: pd.Series, open_prices: pd.Series = None):
        """Detect stop breaches using intraday high/low (for day t+1). Returns:

        - stop_orders: list of dicts with keys: symbol, side, limit_price, shares, reason
        - new_positions: Series with positions zeroed where stop triggers

        Execution rule (backtest-safe):
        - For each position, compute stop price (fixed or trailing).
        - If stop price lies within [low, high] for the bar, we assume stop executed at stop price.
        - If open already on the wrong side (e.g., open <= stop), execute at open.
        """
        stop_orders = []
        new_positions = positions.copy()
        for sym, pos in positions.items():
            if pos == 0:
                continue
            high = float(high_prices.get(sym, np.nan))
            low = float(low_prices.get(sym, np.nan))
            open_p = None if open_prices is None else float(open_prices.get(sym, np.nan))
            if np.isnan(high) or np.isnan(low):
                continue

            entry = self.entry_prices.get(sym, None)
            # fixed stop
            if entry is not None:
                if pos > 0:
                    stop_price = entry * (1 - self.stop_loss_pct)
                    triggered = (low <= stop_price <= high) or (open_p is not None and open_p <= stop_price)
                    if triggered:
                        exec_price = open_p if (open_p is not None and open_p <= stop_price) else stop_price
                        qty = abs(pos)
                        stop_orders.append({'symbol': sym, 'side': 'sell', 'limit_price': exec_price, 'shares': -qty, 'reason': 'fixed'})
                        new_positions[sym] = 0.0
                        self.stop_events.append({'symbol': sym, 'price': exec_price, 'reason': 'fixed'})
                        logger.info('Fixed stop hit for %s at price %.2f (entry %.2f)', sym, exec_price, entry)
                else:
                    stop_price = entry * (1 + self.stop_loss_pct)
                    triggered = (low <= stop_price <= high) or (open_p is not None and open_p >= stop_price)
                    if triggered:
                        exec_price = open_p if (open_p is not None and open_p >= stop_price) else stop_price
                        qty = abs(pos)
                        stop_orders.append({'symbol': sym, 'side': 'buy', 'limit_price': exec_price, 'shares': qty, 'reason': 'fixed'})
                        new_positions[sym] = 0.0
                        self.stop_events.append({'symbol': sym, 'price': exec_price, 'reason': 'fixed'})
                        logger.info('Fixed stop hit for short %s at price %.2f (entry %.2f)', sym, exec_price, entry)

            # trailing stop
            trail = self.trail_levels.get(sym, None)
            if trail is not None:
                if pos > 0:
                    triggered = (low <= trail <= high) or (open_p is not None and open_p <= trail)
                    if triggered:
                        exec_price = open_p if (open_p is not None and open_p <= trail) else trail
                        qty = abs(pos)
                        stop_orders.append({'symbol': sym, 'side': 'sell', 'limit_price': exec_price, 'shares': -qty, 'reason': 'trailing'})
                        new_positions[sym] = 0.0
                        self.stop_events.append({'symbol': sym, 'price': exec_price, 'reason': 'trailing'})
                        logger.info('Trailing stop hit for %s at price %.2f (trail %.2f)', sym, exec_price, trail)
                else:
                    triggered = (low <= trail <= high) or (open_p is not None and open_p >= trail)
                    if triggered:
                        exec_price = open_p if (open_p is not None and open_p >= trail) else trail
                        qty = abs(pos)
                        stop_orders.append({'symbol': sym, 'side': 'buy', 'limit_price': exec_price, 'shares': qty, 'reason': 'trailing'})
                        new_positions[sym] = 0.0
                        self.stop_events.append({'symbol': sym, 'price': exec_price, 'reason': 'trailing'})
                        logger.info('Trailing stop hit for short %s at price %.2f (trail %.2f)', sym, exec_price, trail)

        return stop_orders, new_positions

    def update_trails(self, positions: pd.Series, prices):
        """Update trailing stop levels for held positions.

        prices may be a Series (symbol->price) or a single-row DataFrame; we normalize to a Series.
        """
        # normalize prices to a Series (handle single-row DataFrame)
        if isinstance(prices, pd.DataFrame):
            # if DataFrame has one row, take that row; otherwise require caller to pass series
            if len(prices) == 1:
                prices = prices.iloc[0]
            else:
                raise ValueError('update_trails expects a Series or single-row DataFrame')

        for sym, pos in positions.items():
            if pos == 0:
                self.trail_levels.pop(sym, None)
                continue
            cur_price = prices.get(sym, None)
            try:
                if cur_price is None or (isinstance(cur_price, float) and np.isnan(cur_price)):
                    continue
            except Exception:
                # if cur_price is a pandas scalar, use pandas isna
                if pd.isna(cur_price):
                    continue
            # set trail at (1 - trailing_stop_pct) * cur_price if new high
            new_trail = float(cur_price) * (1 - self.trailing_stop_pct)
            old = self.trail_levels.get(sym, 0)
            # only move trail up
            self.trail_levels[sym] = max(old, new_trail)

    def set_entry_prices_from_account(self, account):
        """Sync entry prices from Account.entry_price Series into RiskManager."""
        for sym, price in account.entry_price.items():
            if not (price is None or (isinstance(price, float) and np.isnan(price))):
                self.entry_prices[sym] = float(price)
            else:
                self.entry_prices.pop(sym, None)

    def scale_for_volatility(self, target_weights: pd.Series, vol_signal: float) -> pd.Series:
        """Scale target weights based on vol signal (e.g., reduce exposure if vol high)."""
        # vol_signal is a multiplier (1.0 normal, >1.0 high vol)
        if vol_signal <= 1.0:
            return target_weights
        return target_weights * (1.0 / vol_signal)
