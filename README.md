# Personal Market Intelligence & Trading Signal Agent

Automated market intelligence platform that fetches real-time market data, runs technical indicators, evaluates configurable rules, aggregates financial news, and generates actionable briefings delivered via Telegram and a Streamlit dashboard.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure credentials
cp ../.env ./.env  # or create your own

# Dry run (prints brief, no Telegram)
DRY_RUN=1 python -m src.main

# Live run (sends to Telegram)
python -m src.main

# Backtest (replay rules over history)
python -m src.backtest --months 12 --csv

# Dashboard
streamlit run dashboard/app.py
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Live mode | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Live mode | Chat ID from @userinfobot |
| `GEMINI_API_KEY` | LLM brief | Free key from Google AI Studio |

## Project Structure

```
config/
├── watchlist.yaml       # Tracked symbols
├── rules.yaml           # Configurable buy/sell rules
├── sources.yaml         # RSS feeds + filtering
└── schedule.yaml        # Cron schedule documentation
src/
├── main.py              # Orchestrator
├── config.py            # YAML + .env loader
├── ingestion/
│   ├── price_yfinance.py
│   └── news_rss.py
├── engine/
│   ├── indicators.py    # RSI, SMA, 52w high/low
│   └── rules.py         # Signal evaluation
├── briefing/
│   └── summarizer.py    # Gemini LLM brief
├── store/
│   └── db.py            # SQLite persistence
├── delivery/
│   └── telegram_bot.py
└── backtest/
    ├── engine.py        # Historical replay
    └── __main__.py      # CLI
dashboard/
└── app.py               # Streamlit UI
docs/
├── PRD.md
└── ARCHITECTURE.md
```

## Trading Rules

Rules are defined in `config/rules.yaml` using simple expressions:
- **Buy**: RSI < 35 (oversold), Golden cross with confirmation
- **Sell**: RSI > 70 (overbought), Death cross with confirmation, 52-week low breakout
- **Hold**: Neither buy nor sell conditions met

Edit `rules.yaml` anytime — no code changes needed.

## Disclaimer

Informational tool only. Not financial advice. Human-in-the-loop required for all trades.
