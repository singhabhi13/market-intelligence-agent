import numpy as np
import pandas as pd


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi[avg_loss == 0] = 100.0
    return rsi


def compute_all_indicators(df: pd.DataFrame, rules_cfg: dict = None) -> pd.DataFrame:
    df = df.copy()

    rsi_len = 14
    sma_fast_len = 20
    sma_long_len = 50

    if rules_cfg and "indicators" in rules_cfg:
        ind = rules_cfg["indicators"]
        rsi_len = ind.get("rsi_period", 14)
        sma_fast_len = ind.get("sma_fast_period", 20)
        sma_long_len = ind.get("sma_long_period", 50)

    close = df["close"]

    df["rsi"] = _rsi(close, rsi_len)
    df["sma_fast"] = close.rolling(window=sma_fast_len, min_periods=1).mean()
    df["sma_long"] = close.rolling(window=sma_long_len, min_periods=1).mean()

    df["sma_fast_prev"] = df["sma_fast"].shift(1)
    df["sma_long_prev"] = df["sma_long"].shift(1)
    df["pct_change_1d"] = close.pct_change() * 100

    if "volume" in df.columns and df["volume"].notna().sum() > 0:
        lookback = min(252, len(df))
        df["high_52w"] = df["high"].rolling(window=lookback, min_periods=1).max()
        df["low_52w"] = df["low"].rolling(window=lookback, min_periods=1).min()
    else:
        df["high_52w"] = None
        df["low_52w"] = None

    return df
