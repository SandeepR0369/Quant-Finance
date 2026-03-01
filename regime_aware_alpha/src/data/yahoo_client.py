import yfinance as yf
import pandas as pd

def fetch_yahoo_data(symbol, start, end):
    data = yf.download(symbol, start=start, end=end)
    data = data[['Open','High','Low','Close','Volume']]
    data.dropna(inplace=True)
    return data