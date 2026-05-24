import pytest
from src.strategy.momentum import AdaptiveMomentumStrategy
from src.data.loader import YahooDataLoader
from config.settings import SETTINGS


def test_loader_downloads():
    loader = YahooDataLoader(data_dir=SETTINGS['data_dir'])
    data = loader.download(['AAPL'], '2020-01-01', '2020-02-01')
    assert 'AAPL' in data


def test_strategy_signals():
    loader = YahooDataLoader(data_dir=SETTINGS['data_dir'])
    data = loader.download(['AAPL', 'MSFT'], '2020-01-01', '2020-06-01')
    strat = AdaptiveMomentumStrategy(lookback=20)
    sig = strat.generate_signals(data)
    assert not sig.empty
