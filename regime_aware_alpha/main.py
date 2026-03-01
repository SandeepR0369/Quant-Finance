# main.py

import os
import sys
import argparse
import logging

import pandas as pd
from config.settings import *
from src.data.yahoo_client import fetch_yahoo_data
from src.data.kite_client import load_session_or_env, get_kite
from src.analytics.returns import compute_simple_returns
from src.analytics.risk_metrics import compute_cagr, compute_annualized_volatility, compute_sharpe_ratio
from src.analytics.drawdown import compute_drawdown
from src.visualization.plots import plot_equity_curve, plot_drawdown


logging.basicConfig(level=logging.INFO)


def fetch_data_yahoo(symbol: str):
    logging.info(f"Fetching Yahoo data for {symbol}")
    return fetch_yahoo_data(symbol, START_DATE, END_DATE)


def fetch_data_kite(symbol: str):
    logging.info(f"Fetching Kite data for {symbol}")

    api_key, api_secret, access_token = load_session_or_env()

    if not api_key or not access_token:
        print("Kite credentials missing.")
        sys.exit(1)

    kite = get_kite(api_key, access_token)

    instruments = kite.instruments("NSE")
    instrument_token = None

    for ins in instruments:
        if ins["tradingsymbol"] == symbol:
            instrument_token = ins["instrument_token"]
            break

    if not instrument_token:
        print(f"Instrument {symbol} not found in NSE instruments.")
        sys.exit(1)

    data = kite.historical_data(
        instrument_token,
        START_DATE,
        END_DATE,
        interval="day"
    )

    
    df = pd.DataFrame(data)
    df.set_index("date", inplace=True)
    return df


def run_analysis(data):

    # --- 1. Extract correct price column safely ---
    if "close" in data.columns:
        price_series = data["close"]
    elif "Close" in data.columns:
        price_series = data["Close"]
    else:
        raise ValueError("Close column not found in data")

    # --- 2. Force Series (avoid accidental DataFrame) ---
    if isinstance(price_series, pd.DataFrame):
        price_series = price_series.iloc[:, 0]

    price_series = price_series.squeeze()

    # --- 3. Compute returns ---
    returns = compute_simple_returns(price_series)

    # --- 4. Ensure returns is Series ---
    if isinstance(returns, pd.DataFrame):
        returns = returns.iloc[:, 0]

    # --- 5. Risk metrics ---
    cagr = float(compute_cagr(returns))
    vol = float(compute_annualized_volatility(returns))
    sharpe = float(compute_sharpe_ratio(returns, RISK_FREE_RATE_INDIA))

    cumulative = (1 + returns).cumprod()
    drawdown = compute_drawdown(cumulative)

    max_dd = float(drawdown.min())

    # --- 6. Print clean formatted output ---
    print("\n===== PERFORMANCE SUMMARY =====")
    print(f"CAGR: {cagr:.2%}")
    print(f"Volatility: {vol:.2%}")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Max Drawdown: {max_dd:.2%}")

    # --- 7. Plot ---
    plot_equity_curve(cumulative)
    plot_drawdown(drawdown)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-source", choices=["yahoo", "kite"], default="yahoo")
    parser.add_argument("--symbol", default="^NSEI")

    args = parser.parse_args()

    if args.data_source == "yahoo":
        data = fetch_data_yahoo(args.symbol)

    elif args.data_source == "kite":
        data = fetch_data_kite(args.symbol)

    else:
        print("Invalid data source")
        sys.exit(1)

    run_analysis(data)


if __name__ == "__main__":
    main()