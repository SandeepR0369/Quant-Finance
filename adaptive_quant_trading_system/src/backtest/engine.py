"""Simple backtest engine with daily rebalancing.
Saves equity curve, drawdown, rolling Sharpe, and trade logs to output directory.
"""
from typing import Dict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
import os
import yaml

from src.execution.executor import weights_to_shares, execute_market_orders
from src.portfolio.accounting import Account
from src.risk.risk_manager import RiskManager
from src.risk.position_sizer import volatility_based_weights, kelly_fraction

logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(self, initial_capital: float, data: Dict[str, pd.DataFrame], strategy, output_dir: str):
        self.initial_capital = initial_capital
        self.data = data
        self.strategy = strategy
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict:
        prices = pd.DataFrame({s: df['adj_close'] for s, df in self.data.items()})
        prices = prices.sort_index()

        if prices.empty:
            logger.warning('No price data available for backtest; aborting run.')
            return {'equity': pd.Series(dtype=float), 'returns': pd.Series(dtype=float), 'trades': pd.DataFrame(), 'perf': {}}

        logger.info('Starting backtest run with execution simulation')
        # generate raw target weights (signals)
        target_weights = self.strategy.generate_signals(self.data)

        # Ensure we have price columns for open/high/low
        price_open = pd.DataFrame({s: df['open'] for s, df in self.data.items()})
        price_high = pd.DataFrame({s: df['high'] for s, df in self.data.items()})
        price_low = pd.DataFrame({s: df['low'] for s, df in self.data.items()})
        price_close = prices

        # align weights to price index
        target_weights = target_weights.reindex(prices.index).ffill().fillna(0)

        # initialize account
        account = Account(initial_cash=self.initial_capital, symbols=list(prices.columns))
        risk = RiskManager()
        risk.initialize(self.initial_capital)

        nav_series = []
        trade_log = []

        dates = prices.index
        for i in range(len(dates) - 1):
            t = dates[i]
            t1 = dates[i + 1]
            # target weights computed on t (close), executed at t+1 open
            weights_t = target_weights.loc[t]

            # position sizing: compute volatility-based sizing using recent history
            hist = price_close.loc[:t].tail(63)
            if not hist.empty:
                try:
                    vol_w = volatility_based_weights(hist, lookback=63)
                    vol_w = vol_w.reindex(weights_t.index).fillna(1.0)
                    combined = weights_t * vol_w
                    if combined.abs().sum() > 0:
                        weights_t = combined / combined.abs().sum()
                except Exception:
                    logger.exception('Volatility-based sizing failed; using strategy weights')

            # optional Kelly scaling
            try:
                if risk.use_kelly and 'SPY' in price_close.columns:
                    market_rets = price_close['SPY'].pct_change().loc[:t].dropna()
                    kf = kelly_fraction(market_rets)
                    weights_t = weights_t * kf
            except Exception:
                logger.exception('Kelly scaling failed')

            # allow risk manager to modify weights (e.g., scale for volatility)
            weights_t = risk.scale_for_volatility(weights_t, vol_signal=1.0)

            # enforce portfolio-level limits
            if not risk.check_portfolio_limits(account.snapshot()):
                logger.warning('Risk manager halted trading at %s', t)
                break

            # synchronize entry prices into the risk manager
            risk.set_entry_prices_from_account(account)

            # update trailing levels based on holdings and yesterday's prices
            risk.update_trails(account.holdings, price_close.loc[:t].iloc[-1:] if not price_close.loc[:t].empty else price_close.loc[t])

            # Detect stop events using next-bar intraday high/low (t+1)
            stop_orders, post_stop_positions = risk.enforce_stops(account.holdings, price_high.loc[t1], price_low.loc[t1], open_prices=price_open.loc[t1])
            if stop_orders:
                # convert stop_orders to a trades DataFrame and execute immediately at reported limit_price
                stop_trades = []
                for so in stop_orders:
                    sym = so['symbol']
                    exec_price = so.get('limit_price', price_open.loc[t1].get(sym, np.nan))
                    shares = so['shares']
                    side = so['side']
                    value = abs(shares) * exec_price
                    commission = value * 0.001
                    stop_trades.append({'symbol': sym, 'exec_price': exec_price, 'shares': shares, 'commission': commission, 'slippage': 0.0, 'side': side, 'value': value})
                stop_df = pd.DataFrame(stop_trades)
                account.apply_trades(stop_df)
                account.mark_to_market(price_close.loc[t1])
                # append stop trades to trade log with reason
                if not stop_df.empty:
                    stop_df['date'] = t1
                    stop_df['reason'] = [so['reason'] for so in stop_orders]
                    trade_log.append(stop_df)

                # after stops, recompute current holdings and zero weights for stopped symbols
                current_shares = account.holdings.reindex(weights_t.index).fillna(0.0)
                for so in stop_orders:
                    weights_t[so['symbol']] = 0.0
            else:
                current_shares = account.holdings.reindex(weights_t.index).fillna(0.0)

            # compute target shares based on NAV at t (use account.nav or initial capital)
            nav = account.nav if account.nav is not None else self.initial_capital
            open_prices = price_open.loc[t1]

            target_shares = weights_to_shares(weights_t, nav, open_prices)

            # execute market orders at t+1 open
            trades_df, cash_change, new_shares = execute_market_orders(target_shares, current_shares, open_prices, price_high.loc[t1], price_low.loc[t1], nav,
                                                                        commission_perc=0.001, slippage_perc=0.0005)
            # apply trades
            account.apply_trades(trades_df)

            # mark to market at close t+1 for unrealized PnL
            account.mark_to_market(price_close.loc[t1])

            # record trades
            if not trades_df.empty:
                trades_df['date'] = t1
                trade_log.append(trades_df)

            nav_series.append({'date': t1, 'nav': account.nav})

        nav_df = pd.DataFrame(nav_series).set_index('date')
        equity = nav_df['nav']

        # Save outputs
        eq_path = self.output_dir / 'equity.csv'
        equity.to_csv(eq_path, header=['equity'])

        # charts and structured stop logging
        returns = equity.pct_change().fillna(0)
        # write structured stop events if present on risk manager
        try:
            from src.visualization.plots import plot_equity, plot_drawdown, plot_rolling_sharpe, plot_allocation
            # collect stop events from risk if available
            stop_events = []
            # trade_log may contain stop reason; build DataFrame of stops
            for df in trade_log:
                if 'reason' in df.columns:
                    stop_events.append(df[df['reason'].notna()][['date', 'symbol', 'exec_price', 'shares', 'reason']])
            stops_df = pd.concat(stop_events, ignore_index=True) if stop_events else pd.DataFrame()
            # write stops CSV
            stops_path = self.output_dir / 'stop_events.csv'
            stops_df.to_csv(stops_path, index=False)

            # replace inline plotting with visualization module
            plot_equity(equity, trades=pd.concat(trade_log, ignore_index=True) if trade_log else pd.DataFrame(), stops=stops_df, regimes=None, out_path=self.output_dir / 'equity_curve.png')
            plot_drawdown(equity, out_path=self.output_dir / 'drawdown.png')
            plot_rolling_sharpe(returns, out_path=self.output_dir / 'rolling_sharpe.png')
            # if we had weights history (not currently captured), we could plot allocation
        except Exception:
            # fallback to existing plotting if visualization module missing or fails
            self._plot_equity(equity)
            self._plot_drawdown(equity)
            self._plot_rolling_sharpe(returns)

        # concat trade logs
        trades = pd.concat(trade_log, ignore_index=True) if trade_log else pd.DataFrame()
        trades_path = self.output_dir / 'trade_logs.csv'
        trades.to_csv(trades_path, index=False)

        perf = self._performance_report(equity, returns)
        perf_path = self.output_dir / 'performance_report.yaml'
        
        with open(perf_path, 'w') as f:
            yaml.safe_dump(perf, f)

        return {
            'equity': equity,
            'returns': returns,
            'trades': trades,
            'perf': perf
        }

    def _plot_equity(self, equity: pd.Series):
        fig, ax = plt.subplots(figsize=(10, 6))
        equity.plot(ax=ax)
        ax.set_title('Equity Curve')
        ax.set_ylabel('Portfolio Value')
        path = self.output_dir / 'equity_curve.png'
        fig.savefig(path)
        plt.close(fig)
        logger.info('Saved equity curve to %s', path)

    def _plot_drawdown(self, equity: pd.Series):
        roll_max = equity.cummax()
        drawdown = (equity - roll_max) / roll_max
        fig, ax = plt.subplots(figsize=(10, 4))
        drawdown.plot(ax=ax)
        ax.set_title('Drawdown')
        path = self.output_dir / 'drawdown.png'
        fig.savefig(path)
        plt.close(fig)
        logger.info('Saved drawdown chart to %s', path)

    def _plot_rolling_sharpe(self, port_rets: pd.Series, window: int = 63):
        # daily returns assumed; annualize with 252
        rs = port_rets.rolling(window).mean() / port_rets.rolling(window).std()
        rs = rs * (252 ** 0.5)
        fig, ax = plt.subplots(figsize=(10, 4))
        rs.plot(ax=ax)
        ax.set_title('Rolling Sharpe (window=%d)' % window)
        path = self.output_dir / 'rolling_sharpe.png'
        fig.savefig(path)
        plt.close(fig)
        logger.info('Saved rolling Sharpe chart to %s', path)

    def _generate_trade_logs(self, positions: pd.DataFrame) -> pd.DataFrame:
        trades = []
        prev = pd.Series(0, index=positions.columns)
        for date, row in positions.iterrows():
            diff = row.fillna(0) - prev.fillna(0)
            for sym, change in diff.items():
                if abs(change) > 1e-8:
                    trades.append({'date': date, 'symbol': sym, 'size_change': float(change)})
            prev = row
        return pd.DataFrame(trades)

    def _performance_report(self, equity: pd.Series, port_rets: pd.Series) -> Dict:
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
        annualized_return = float((1 + total_return) ** (252 / len(port_rets)) - 1)
        ann_vol = float(port_rets.std() * (252 ** 0.5))
        sharpe = float(annualized_return / ann_vol) if ann_vol != 0 else 0.0
        max_dd = float(((equity / equity.cummax()) - 1).min())
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': ann_vol,
            'sharpe': sharpe,
            'max_drawdown': max_dd
        }
