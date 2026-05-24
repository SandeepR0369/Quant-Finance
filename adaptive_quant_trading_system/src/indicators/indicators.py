"""Technical indicators wrapper using pandas_ta.

This module provides reusable indicators and an `attach_indicators` function
that computes and attaches indicators to a price DataFrame. It is intentionally
designed to avoid look-ahead bias: all indicators are computed using only
historical data up to each timestamp (pandas_ta adheres to this by default).

Indicators included:
- RSI
- ATR
- Bollinger Bands
- SMA and EMA
- Volume-based indicators (VWAP via rolling)

API contract:
- Input: `price_df` - DataFrame with columns ['open','high','low','close','volume'] or at minimum ['close']
- Output: DataFrame with additional columns named like 'rsi_{n}', 'atr_{n}', 'bb_upper_{n}',
  'bb_mid_{n}', 'bb_lower_{n}', 'sma_{n}', 'ema_{n}', 'vwap_{n}'

Ensure the returned DataFrame is aligned to the input index and contains no forward-looking values.
"""
from __future__ import annotations
from typing import List, Optional
import pandas as pd
import ta
import logging

logger = logging.getLogger(__name__)


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    # If only 'adj_close' present, backfill open/high/low with close
    cols = df.columns
    if 'close' not in cols and 'adj_close' in cols:
        df = df.rename(columns={'adj_close': 'close'})
    if 'open' not in df.columns:
        df['open'] = df['close']
    if 'high' not in df.columns:
        df['high'] = df['close']
    if 'low' not in df.columns:
        df['low'] = df['close']
    if 'volume' not in df.columns:
        df['volume'] = 0.0
    return df[['open', 'high', 'low', 'close', 'volume']]


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Relative Strength Index (RSI).

    Theory: RSI measures recent gains vs losses over a lookback. Values above
    70 are typically overbought and below 30 oversold (configurable).

    Uses Wilder smoothing by default via pandas_ta.
    """
    # ta.momentum.RSIIndicator expects pandas Series
    r = ta.momentum.RSIIndicator(close=series, window=length)
    return r.rsi()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range (ATR): a volatility measure.

    Higher ATR indicates higher volatility; used for position sizing and regime detection.
    """
    # ta.volatility.AverageTrueRange
    at = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=length)
    return at.average_true_range()


def bollinger_bands(series: pd.Series, length: int = 20, std: int = 2) -> pd.DataFrame:
    """Bollinger Bands: mid-band is SMA(length), upper/lower are mid +/- std * rolling std.

    Returns DataFrame with columns ['BBL', 'BBM', 'BBU', 'BBBANDWIDTH']
    """
    bb = ta.volatility.BollingerBands(close=series, window=length, window_dev=std)
    out = pd.DataFrame(index=series.index)
    out['bb_mid'] = bb.bollinger_mavg()
    out['bb_upper'] = bb.bollinger_hband()
    out['bb_lower'] = bb.bollinger_lband()
    out['bb_width'] = (out['bb_upper'] - out['bb_lower']) / out['bb_mid']
    return out


def sma(series: pd.Series, length: int = 50) -> pd.Series:
    """Simple Moving Average."""
    sma_ind = ta.trend.SMAIndicator(close=series, window=length)
    return sma_ind.sma_indicator()


def ema(series: pd.Series, length: int = 50) -> pd.Series:
    """Exponential Moving Average."""
    ema_ind = ta.trend.EMAIndicator(close=series, window=length)
    return ema_ind.ema_indicator()


def vwap(df: pd.DataFrame, length: Optional[int] = None) -> pd.Series:
    """Volume-weighted average price. If length provided, return rolling VWAP.

    If no volume information is present, returns NaN.
    """
    if 'volume' not in df.columns or df['volume'].sum() == 0:
        logger.debug('No volume present for VWAP; returning NaN series')
        return pd.Series(index=df.index, data=[float('nan')] * len(df))
    pv = df['close'] * df['volume']
    if length is None:
        return pv.cumsum() / df['volume'].cumsum()
    else:
        return (pv.rolling(length).sum() / df['volume'].rolling(length).sum())


def attach_indicators(price_df: pd.DataFrame,
                      rsi_lengths: List[int] = [14],
                      atr_lengths: List[int] = [14],
                      bb_length: int = 20,
                      bb_std: int = 2,
                      ma_lengths: List[int] = [20, 50, 200],
                      vwap_length: Optional[int] = None) -> pd.DataFrame:
    """Attach indicators to a DataFrame with OHLCV columns.

    Returns a new DataFrame with additional columns. This function is vectorized
    and avoids look-ahead by relying on pandas_ta, which uses past values only.
    Column naming convention: indicator_window (e.g., rsi_14, atr_14, sma_50)
    """
    df = price_df.copy()
    df = _ensure_ohlcv(df)

    # RSI
    for r in rsi_lengths:
        df[f'rsi_{r}'] = rsi(df['close'], length=r)

    # ATR
    for a in atr_lengths:
        df[f'atr_{a}'] = atr(df['high'], df['low'], df['close'], length=a)

    # Bollinger Bands
    bb = bollinger_bands(df['close'], length=bb_length, std=bb_std)
    df = df.join(bb)

    # Moving Averages
    for m in ma_lengths:
        df[f'sma_{m}'] = sma(df['close'], length=m)
        df[f'ema_{m}'] = ema(df['close'], length=m)

    # VWAP
    if vwap_length is None:
        df['vwap'] = vwap(df, None)
    else:
        df[f'vwap_{vwap_length}'] = vwap(df, vwap_length)

    return df


def example_usage():
    """Example usage: loads a CSV from data/local_store/AAPL.csv (if present)
    and computes indicators and returns first few rows.
    """
    import os
    path = os.path.join('data', 'local_store', 'AAPL.csv')
    if not os.path.exists(path):
        logger.warning('Example data %s not found', path)
        return None
    p = pd.read_csv(path, parse_dates=True, index_col=0)
    if 'Adj Close' in p.columns:
        p = p.rename(columns={'Adj Close': 'close'})
    elif 'adj_close' in p.columns:
        p = p.rename(columns={'adj_close': 'close'})
    df = attach_indicators(p)
    return df.head()
