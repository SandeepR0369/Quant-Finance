"""Main entry point for Adaptive Quant Trading System.
This script downloads data, runs a simple backtest, computes analytics, and saves reports.
"""
from src.backtest.engine import BacktestEngine
from src.data.loader import YahooDataLoader
from src.strategy.momentum import AdaptiveMomentumStrategy
from config.settings import SETTINGS
from src.utils.logger import setup_logging
import logging


def main():
    setup_logging(SETTINGS['log_file'])
    logger = logging.getLogger(__name__)
    logger.info('Starting Adaptive Quant Trading System')

    symbols = SETTINGS['universe']
    start = SETTINGS['start_date']
    end = SETTINGS['end_date']

    loader = YahooDataLoader(data_dir=SETTINGS['data_dir'])
    data = loader.download(symbols, start, end)

    strategy = AdaptiveMomentumStrategy(lookback=SETTINGS['lookback'], risk_aversion=SETTINGS['risk_aversion'])

    bt = BacktestEngine(initial_capital=SETTINGS['initial_capital'], data=data, strategy=strategy, output_dir=SETTINGS['output_dir'])
    results = bt.run()

    logger.info('Backtest complete. Results saved to %s', SETTINGS['output_dir'])


if __name__ == '__main__':
    main()
