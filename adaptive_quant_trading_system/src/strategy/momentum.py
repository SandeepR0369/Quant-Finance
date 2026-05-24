"""Adaptive momentum strategy: allocate to top momentum stocks with simple risk scaling."""
from typing import Dict
import pandas as pd
import numpy as np
import logging


logger = logging.getLogger(__name__)


class AdaptiveMomentumStrategy:
    def __init__(self, lookback: int = 63, risk_aversion: float = 0.5, top_n: int = 2):
        self.lookback = lookback
        self.risk_aversion = risk_aversion
        self.top_n = top_n

    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Return a positions DataFrame indexed by date with columns for each symbol (weights).

        data: dict of symbol -> DataFrame with 'adj_close'
        """
        prices = pd.DataFrame({s: df['adj_close'] for s, df in data.items()})
        returns = prices.pct_change()

        momentum = prices.pct_change(self.lookback)
        # Rank by momentum each day and go long top_n equally weighted
        positions = pd.DataFrame(index=prices.index, columns=prices.columns).fillna(0.0)

        for date in momentum.index:
            try:
                row = momentum.loc[date].dropna()
                if row.empty:
                    continue
                top = row.nlargest(self.top_n).index.tolist()
                weight = 1.0 / self.top_n
                positions.loc[date, top] = weight
            except Exception:
                continue

        # Simple risk scaling: shrink weights by volatility
        vol = returns.rolling(self.lookback).std()
        vol = vol.replace(0, np.nan).bfill().ffill()
        # divide positions by volatility to scale risk; avoid division by zero
        scaled = positions.div(vol.replace(0, np.nan)).fillna(0)
        # Re-normalize to sum to 1 each day
        scaled = scaled.div(scaled.abs().sum(axis=1).replace(0, 1), axis=0).fillna(0)
        return scaled
