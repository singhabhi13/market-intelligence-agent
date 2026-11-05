import os
from pathlib import Path

from src.config import load_yaml, load_env
from src.ingestion.price_yfinance import PriceAdapter
from src.ingestion.news_rss import NewsAdapter
from src.engine.rules import SignalEngine
from src.briefing.summarizer import generate_brief
from src.store.db import SQLiteStore
from src.delivery.telegram_bot import TelegramDelivery

BASE_DIR = Path(__file__).resolve().parent.parent


def main():
    load_env()

    watchlist = load_yaml(str(BASE_DIR / "config" / "watchlist.yaml"))
    rules_cfg = load_yaml(str(BASE_DIR / "config" / "rules.yaml"))
    sources_cfg = load_yaml(str(BASE_DIR / "config" / "sources.yaml"))

    symbols = watchlist.get("universe", [])
    prices = PriceAdapter.fetch_data(symbols)
    engine = SignalEngine(rules_cfg)
    signals = [engine.evaluate_symbol(sym, df) for sym, df in prices.items()]

    sources_cfg["watchlist"] = symbols
    news = NewsAdapter(sources_cfg).fetch_latest_news()

    brief = generate_brief(signals, news)

    db = SQLiteStore(str(BASE_DIR / "data" / "signals.sqlite"))
    db.save_signals(signals)
    db.save_brief(brief)
    db.save_news(news)

    if os.getenv("DRY_RUN", "0") == "1":
        print("=== DRY RUN BRIEFING ===")
        print(brief)
    else:
        TelegramDelivery().send_message(brief)


if __name__ == "__main__":
    main()
