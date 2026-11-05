import yfinance as yf
import pandas as pd
from typing import List, Dict

class PriceAdapter:
    @staticmethod
    def fetch_data(symbols: List[str], period: str = "6mo", interval: str = "1d") -> Dict[str, pd.DataFrame]:
        data = {}
        for symbol in symbols:
            try:
                df = yf.Ticker(symbol).history(period=period, interval=interval)
                if not df.empty:
                    df = df.rename(columns={c: c.lower() for c in df.columns})
                    df.index = pd.to_datetime(df.index)
                    data[symbol] = df
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
        return data
