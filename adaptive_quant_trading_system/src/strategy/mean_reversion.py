"""Mean-reversion strategy variant using Bollinger Bands + RSI.

Generates signals to buy when price touches lower band with oversold RSI and sell when price touches upper band with overbought RSI.
"""
from typing import Dict
import pandas as pd
import numpy as np
from src.indicators.indicators import attach_indicators
from src.regime.regime import detect_regime
import logging

logger = logging.getLogger(__name__)


class MeanReversionStrategy:
    def __init__(self,
                 bb_length: int = 20,
                 bb_std: int = 2,
                 rsi_window: int = 14,
                 rsi_buy: int = 30,
                 rsi_sell: int = 70,
                 top_n: int = 10,
                 reduce_on_high_vol: float = 0.5):
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.rsi_window = rsi_window
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
        self.top_n = top_n
        self.reduce_on_high_vol = reduce_on_high_vol

    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        prices = pd.DataFrame({s: df['adj_close'] for s, df in data.items()})
        scores = pd.DataFrame(index=prices.index, columns=prices.columns, data=0.0)

        for sym, df in data.items():
            ind = attach_indicators(df.rename(columns={'adj_close':'close','Adj Close':'close'}),
                                    rsi_lengths=[self.rsi_window],
                                    bb_length=self.bb_length, bb_std=self.bb_std)
            # price position relative to bands
            price = ind['close']
            lower = ind['bb_lower']
            upper = ind['bb_upper']
            mid = ind['bb_mid']
            rsi = ind[f'rsi_{self.rsi_window}']

            # buy signal when price < lower and rsi < rsi_buy
            buy = ((price < lower) & (rsi < self.rsi_buy)).astype(float)
            # sell signal when price > upper and rsi > rsi_sell
            sell = -((price > upper) & (rsi > self.rsi_sell)).astype(float)

            score = buy + sell
            scores[sym] = score

        # cross-sectional selection: pick top N buys (positive) and top N sells (negative)
        positions = pd.DataFrame(index=prices.index, columns=prices.columns).fillna(0.0)
        for date in scores.index:
            row = scores.loc[date].dropna()
            if row.empty:
                continue
            buys = row[row > 0].nlargest(self.top_n)
            sells = row[row < 0].nsmallest(self.top_n)
            if not buys.empty:
                w = buys / buys.sum()
                positions.loc[date, w.index] = w.values
            if not sells.empty:
                w = sells.abs() / sells.abs().sum()
                # represent short positions as negative weights
                positions.loc[date, w.index] = -w.values

        # regime-aware scaling using SPY
        if 'SPY' in prices.columns:
            regime = detect_regime(prices['SPY'])
            for date in positions.index:
                if regime.get(date, 'low') == 'high':
                    positions.loc[date] *= self.reduce_on_high_vol

        return positions.fillna(0.0)
