import pandas as pd
import os
from pathlib import Path

from src.data.loader import YahooDataLoader


def test_normalize_columns(tmp_path, monkeypatch):
    # create a CSV with mixed-case headers
    csv = tmp_path / 'TEST.csv'
    df = pd.DataFrame({
        'Date': pd.date_range('2020-01-01', periods=3),
        'Open': [1, 2, 3],
        'High': [1.1, 2.1, 3.1],
        'Low': [0.9, 1.9, 2.9],
        'Close': [1, 2, 3],
        'Volume': [100, 200, 300]
    })
    df.to_csv(csv, index=False)

    loader = YahooDataLoader(data_dir=str(tmp_path))
    res = loader.download(['TEST'], start='2020-01-01', end='2020-01-10')
    assert 'TEST' in res
    out = res['TEST']
    # check normalized columns
    for c in ['open', 'high', 'low', 'close', 'volume', 'adj_close']:
        assert c in out.columns


def test_missing_required_columns(tmp_path):
    # create a CSV missing 'Open' column
    csv = tmp_path / 'MISS.csv'
    df = pd.DataFrame({
        'Date': pd.date_range('2020-01-01', periods=3),
        'Close': [1, 2, 3],
        'Volume': [100, 200, 300]
    })
    df.to_csv(csv, index=False)
    loader = YahooDataLoader(data_dir=str(tmp_path))
    res = loader.download(['MISS'], start='2020-01-01', end='2020-01-10')
    # loader should skip symbol due to missing open/high/low
    assert 'MISS' not in res
