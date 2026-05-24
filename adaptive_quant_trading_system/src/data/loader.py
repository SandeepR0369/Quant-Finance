"""Data loader module to fetch historical price data using yfinance.
Saves downloaded CSVs to local store to avoid repeated downloads.
"""
from typing import List, Dict
import yfinance as yf
import pandas as pd
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class YahooDataLoader:
    def __init__(self, data_dir: str = 'data/local_store'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # required normalized columns
        self._required_cols = ['open', 'high', 'low', 'close', 'volume', 'adj_close']

    def download(self, symbols: List[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
        """Download historical adjusted close prices for symbols and return dict of DataFrames.

        Handles variations in yfinance output and caches CSVs. Returns DataFrames with a
        single column named 'adj_close' and a DatetimeIndex.
        """
        result = {}
        for s in symbols:
            try:
                path = self.data_dir / f"{s}.csv"
                df = None

                # if cache exists, try to load it with explicit date parsing and normalization
                if path.exists():
                    logger.info('Loading %s from cache %s', s, path)
                    try:
                        df = pd.read_csv(path, index_col=0, parse_dates=[0])
                        df.index = pd.to_datetime(df.index)
                        # normalize columns
                        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
                        # rewrite normalized cache to ensure schema consistency
                        try:
                            df.to_csv(path)
                        except Exception:
                            logger.debug('Could not rewrite cache for %s', s)
                        # if index still not datetime, force redownload
                        if not pd.api.types.is_datetime64_any_dtype(df.index):
                            logger.warning('Cached CSV for %s has invalid index, forcing redownload', s)
                            df = None
                    except Exception:
                        logger.warning('Failed to load cache for %s, forcing redownload', s)
                        df = None

                # if no valid cache, download from yfinance
                if df is None:
                    logger.info('Downloading %s from Yahoo Finance', s)
                    df = yf.download(s, start=start, end=end, progress=False)
                    # fallback: sometimes yf.download returns unexpected structure; try Ticker.history
                    if df is None or getattr(df, 'empty', True):
                        logger.info('yf.download returned empty for %s, trying Ticker.history()', s)
                        try:
                            df = yf.Ticker(s).history(start=start, end=end)
                        except Exception:
                            df = None
                    if df is None or getattr(df, 'empty', True):
                        logger.warning('No data for %s', s)
                        continue

                    # normalize and cache
                    try:
                        df.index = pd.to_datetime(df.index)
                    except Exception:
                        pass
                    try:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = ['_'.join(map(str, c)).strip().lower().replace(' ', '_') for c in df.columns]
                        else:
                            df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
                    except Exception:
                        pass
                    try:
                        df.to_csv(path)
                    except Exception:
                        logger.debug('Failed to write downloaded cache for %s', s)

                # at this point df is loaded; normalize columns and validate required ones
                try:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = ['_'.join(map(str, c)).strip().lower().replace(' ', '_') for c in df.columns]
                    else:
                        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
                except Exception:
                    pass

                # required columns check
                missing = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c not in df.columns]
                if missing:
                    # try fuzzy-fallback by substring
                    for col in list(df.columns):
                        cl = col.lower()
                        if 'open' in cl and 'open' not in df.columns:
                            df = df.rename(columns={col: 'open'})
                        if 'high' in cl and 'high' not in df.columns:
                            df = df.rename(columns={col: 'high'})
                        if 'low' in cl and 'low' not in df.columns:
                            df = df.rename(columns={col: 'low'})
                        if 'close' in cl and 'close' not in df.columns:
                            df = df.rename(columns={col: 'close'})
                        if 'volume' in cl and 'volume' not in df.columns:
                            df = df.rename(columns={col: 'volume'})
                    missing2 = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c not in df.columns]
                    if missing2:
                        logger.error('Unable to find required columns %s for %s after normalization; skipping symbol', missing2, s)
                        continue

                # create adj_close if possible
                if 'adj_close' in df.columns:
                    adj = df['adj_close']
                elif 'close' in df.columns:
                    adj = df['close']
                else:
                    logger.error('No close/adj_close found for %s after normalization; skipping', s)
                    continue

                # build normalized OHLCV DataFrame
                df2 = df[['open', 'high', 'low', 'close', 'volume']].copy()
                df2['adj_close'] = adj
                try:
                    df2.index = pd.to_datetime(df2.index)
                except Exception:
                    if 'date' in df2.columns:
                        df2 = df2.set_index(pd.to_datetime(df2['date']))
                        df2 = df2.drop(columns=['date'], errors=True)

                # ensure cache holds the normalized schema
                try:
                    df2.to_csv(path)
                except Exception:
                    logger.debug('Could not overwrite normalized cache for %s', s)

                result[s] = df2
            except Exception as e:
                logger.exception('Failed to download %s: %s', s, e)
        return result
