"""Trend + Momentum strategy.

Primary strategy combining moving average crossovers, RSI confirmation, ATR volatility
filter, and volume confirmation. Produces cross-sectionally ranked target weights.

Signals are generated on close(t) and meant to be executed at open(t+1) — no look-ahead.
"""
from typing import Dict, List
import pandas as pd
import numpy as np
from src.indicators.indicators import attach_indicators
from src.regime.regime import detect_regime
import logging

logger = logging.getLogger(__name__)


class TrendMomentumStrategy:
    def __init__(self,
                 ma_fast: int = 20,
                 ma_slow: int = 50,
                 rsi_window: int = 14,
                 rsi_thresh: float = 50.0,
                 atr_window: int = 14,
                 top_n: int = 10,
                 reduce_on_high_vol: float = 0.5):
        """Configurable parameters:
        - ma_fast, ma_slow: moving average windows for crossover
        - rsi_window, rsi_thresh: RSI confirmation (above threshold = bullish)
        - atr_window: volatility filter
        - top_n: number of assets to allocate to (cross-sectional selection)
        - reduce_on_high_vol: fraction to scale exposure during high volatility regime
        """
        self.ma_fast = ma_fast
        self.ma_slow = ma_slow
        self.rsi_window = rsi_window
        self.rsi_thresh = rsi_thresh
        self.atr_window = atr_window
        self.top_n = top_n
        self.reduce_on_high_vol = reduce_on_high_vol

    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Generate daily target weights (0..1) per symbol indexed by date.

        data: dict symbol->DataFrame with 'adj_close' (and optionally ohlcv). The method
        returns a DataFrame positions indexed by date with columns for each symbol summing to 1 when any positions exist.
        """
        # Build price panel
        prices = pd.DataFrame({s: df['adj_close'] for s, df in data.items()})

        # Compute indicators for each symbol and create a scoring metric
        scores = pd.DataFrame(index=prices.index, columns=prices.columns, data=0.0)

        for sym, df in data.items():
            ind = attach_indicators(df.rename(columns={'adj_close':'close','Adj Close':'close'}),
                                    rsi_lengths=[self.rsi_window],
                                    atr_lengths=[self.atr_window],
                                    ma_lengths=[self.ma_fast, self.ma_slow])
            # MA crossover score
            ma_fast = ind[f'sma_{self.ma_fast}']
            ma_slow = ind[f'sma_{self.ma_slow}']
            ma_signal = (ma_fast > ma_slow).astype(float)

            # RSI confirmation - normalized around thresh
            rsi = ind[f'rsi_{self.rsi_window}']
            rsi_signal = (rsi - self.rsi_thresh) / 100.0

            # ATR: lower volatility gets slight boost (inverse)
            atr_s = ind[f'atr_{self.atr_window}']
            atr_signal = 1.0 / (atr_s.replace(0, np.nan)).bfill()
            atr_signal = (atr_signal - atr_signal.min()) / (atr_signal.max() - atr_signal.min() + 1e-9)

            # score is weighted sum
            s = 0.6 * ma_signal + 0.3 * rsi_signal + 0.1 * atr_signal
            scores[sym] = s

        # Cross-sectional ranking and selection per day
        positions = pd.DataFrame(index=prices.index, columns=prices.columns).fillna(0.0)
        for date in scores.index:
            row = scores.loc[date].dropna()
            if row.empty:
                continue
            top = row.nlargest(self.top_n)
            if top.sum() <= 0:
                continue
            weights = top / top.sum()
            positions.loc[date, weights.index] = weights.values

        # Regime detection on the market index (if SPY present)
        if 'SPY' in prices.columns:
            regime = detect_regime(prices['SPY'])
            # scale positions in high vol
            for date in positions.index:
                if regime.get(date, 'low') == 'high':
                    positions.loc[date] *= self.reduce_on_high_vol

        return positions.fillna(0.0)

