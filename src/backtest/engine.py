"""Backtest engine: replay the SAME config rules over history.

For each symbol, walk day-by-day using only data available up to that day
(no lookahead), evaluate config/rules.yaml, and simulate a simple long-only
strategy: enter on BUY, exit on SELL or stop-loss/take-profit from risk:.
Outputs per-symbol trades, summary stats, and optional CSV of signals.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.config import load_yaml
from src.engine.rules import evaluate
from src.ingestion.price_yfinance import PriceAdapter

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class Trade:
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    reason: str

    @property
    def return_pct(self) -> float:
        return (self.exit_price / self.entry_price - 1) * 100


@dataclass
class SymbolResult:
    symbol: str
    trades: list[Trade] = field(default_factory=list)
    signal_rows: list[dict] = field(default_factory=list)

    @property
    def total_return_pct(self) -> float:
        eq = 1.0
        for t in self.trades:
            eq *= (1 + t.return_pct / 100)
        return (eq - 1) * 100

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.return_pct > 0)
        return wins / len(self.trades) * 100


def _min_bars(rules_cfg: dict) -> int:
    ind = rules_cfg.get("indicators", {})
    return max(ind.get("rsi_period", 14), ind.get("sma_long_period", 50)) + 5


def backtest_symbol(symbol: str, df: pd.DataFrame, rules_cfg: dict) -> SymbolResult:
    res = SymbolResult(symbol=symbol)
    risk = rules_cfg.get("risk", {})
    stop = risk.get("stop_loss_pct")
    take = risk.get("take_profit_pct")

    start = _min_bars(rules_cfg)
    in_pos = False
    entry_price = 0.0
    entry_date = ""

    for i in range(start, len(df)):
        window = df.iloc[: i + 1]
        sig = evaluate(symbol, window, rules_cfg)
        date = str(window.index[-1].date())
        close = sig.features.get("close")
        if close is None:
            continue

        res.signal_rows.append({
            "date": date,
            "action": sig.action,
            "close": round(close, 2),
            "rsi": round(sig.features.get("rsi") or 0, 1),
            "sma_fast": round(sig.features.get("sma_fast") or 0, 2),
            "sma_long": round(sig.features.get("sma_long") or 0, 2),
            "rationale": "; ".join(sig.rationale),
        })

        if not in_pos:
            if sig.action == "BUY":
                in_pos, entry_price, entry_date = True, close, date
        else:
            exit_reason = None
            if stop is not None and close <= entry_price * (1 - stop / 100):
                exit_reason = "stop_loss"
            elif take is not None and close >= entry_price * (1 + take / 100):
                exit_reason = "take_profit"
            elif sig.action == "SELL":
                exit_reason = "sell_signal"

            if exit_reason:
                res.trades.append(Trade(symbol, entry_date, entry_price, date, close, exit_reason))
                in_pos = False

    if in_pos:
        last_close = float(df["close"].iloc[-1])
        res.trades.append(Trade(symbol, entry_date, entry_price, str(df.index[-1].date()), last_close, "open_eod"))

    return res


def write_csv(res: SymbolResult) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"backtest_{res.symbol.replace('.', '_')}.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "action", "close", "rsi", "sma_fast", "sma_long", "rationale"])
        w.writeheader()
        w.writerows(res.signal_rows)
    return path


def run(months: int = 12, want_csv: bool = False) -> list[SymbolResult]:
    base = Path(__file__).resolve().parent.parent.parent
    watchlist = load_yaml(str(base / "config" / "watchlist.yaml"))
    rules_cfg = load_yaml(str(base / "config" / "rules.yaml"))
    period = f"{max(1, months)}mo"
    price_data = PriceAdapter.fetch_data(watchlist.get("universe", []), period=period)

    results = []
    for sym, df in price_data.items():
        res = backtest_symbol(sym, df, rules_cfg)
        results.append(res)
        if want_csv:
            write_csv(res)
    return results
