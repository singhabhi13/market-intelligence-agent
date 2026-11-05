import pandas as pd
from asteval import Interpreter
from typing import Dict, Any

from src.engine.indicators import compute_all_indicators


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else round(f, 2)


class SignalEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.rules_config = rules_config
        self.aeval = Interpreter()

    def evaluate_symbol(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty or len(df) < 55:
            return {"symbol": symbol, "signal": "HOLD", "rationale": "Insufficient data"}

        df_ind = compute_all_indicators(df, self.rules_config)
        latest = df_ind.iloc[-1].to_dict()

        for k, v in latest.items():
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                self.aeval.symtable[k] = v

        buy_rules = self.rules_config.get("rules", {}).get("buy", [])
        sell_rules = self.rules_config.get("rules", {}).get("sell", [])

        buy_fired = [r for r in buy_rules if self.aeval(r)]
        if buy_fired:
            signal, rationale = "BUY", f"Buy triggers: {', '.join(buy_fired)}"
        else:
            sell_fired = [r for r in sell_rules if self.aeval(r)]
            if sell_fired:
                signal, rationale = "SELL", f"Sell triggers: {', '.join(sell_fired)}"
            else:
                signal, rationale = "HOLD", "No criteria met"

        return {
            "symbol": symbol,
            "signal": signal,
            "rationale": rationale,
            "close": _num(latest.get("close")),
            "rsi": _num(latest.get("rsi")),
            "sma_fast": _num(latest.get("sma_fast")),
            "sma_long": _num(latest.get("sma_long")),
        }


def evaluate(symbol: str, df: pd.DataFrame, rules_cfg: dict):
    from dataclasses import dataclass, field

    @dataclass
    class SignalResult:
        symbol: str
        action: str
        rationale: list
        features: dict = field(default_factory=dict)

    if df.empty or len(df) < 55:
        return SignalResult(symbol, "HOLD", ["Insufficient data"], {})

    df_ind = compute_all_indicators(df, rules_cfg)
    latest = df_ind.iloc[-1].to_dict()

    aeval = Interpreter()
    for k, v in latest.items():
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            aeval.symtable[k] = v

    buy_rules = rules_cfg.get("rules", {}).get("buy", [])
    sell_rules = rules_cfg.get("rules", {}).get("sell", [])

    buy_fired = [r for r in buy_rules if aeval(r)]
    if buy_fired:
        return SignalResult(symbol, "BUY", buy_fired, latest)

    sell_fired = [r for r in sell_rules if aeval(r)]
    if sell_fired:
        return SignalResult(symbol, "SELL", sell_fired, latest)

    return SignalResult(symbol, "HOLD", ["No criteria met"], latest)
