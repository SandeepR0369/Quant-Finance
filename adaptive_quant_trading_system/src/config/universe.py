"""Curated universe of liquid large-cap equities for cross-sectional experiments.

This module provides a simple, static list of 50 liquid, large-cap US equities
plus one market index (SPY) to satisfy CPAT breadth requirements. The list is
intentionally conservative and academic: it's a snapshot of commonly used, highly
liquid names (many overlap with S&P 100 / S&P 500 large caps).

"""

from typing import List

# Curated 50 large-cap liquid equities (S&P100 / large-cap style selection).
# This selection is stable, widely-traded, and commonly used in academic work.
UNIVERSE: List[str] = [
    'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'GOOG', 'FB', 'META', 'NVDA', 'TSLA',
    'BRK-B', 'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'BAC', 'XOM',
    'PFE', 'VZ', 'ADBE', 'CMCSA', 'NFLX', 'INTC', 'T', 'CSCO', 'KO', 'PEP',
    'WMT', 'MRK', 'ABBV', 'ABT', 'CRM', 'AVGO', 'NKE', 'ORCL', 'CVX', 'MCD',
    'TXN', 'PM', 'ACN', 'NEE', 'DHR', 'QCOM', 'LIN', 'COST', 'LOW', 'AMD'
]

# Market index used for regime detection and market-reference (kept separate
# to make index inclusion explicit). We prefer SPY as a widely-available ETF.
INDEX = 'SPY'


def normalized_universe() -> List[str]:
    """Return a cleaned universe: unique tickers + index ensured.

    - Removes duplicates while preserving order.
    - Ensures the index symbol (SPY) is present exactly once at the end of the
      list for convenience (engine/strategies can reference it explicitly).
    """
    seen = set()
    cleaned = []
    for t in UNIVERSE:
        # normalize small formatting differences (uppercase expected)
        tt = t.strip().upper()
        if tt not in seen:
            seen.add(tt)
            cleaned.append(tt)

    # Ensure index is included once
    idx = INDEX.strip().upper()
    if idx not in seen:
        cleaned.append(idx)

    return cleaned


if __name__ == '__main__':
    # simple smoke-run to show the list length
    u = normalized_universe()
    print(f"Universe contains {len(u)} symbols (including index '{INDEX}').")
