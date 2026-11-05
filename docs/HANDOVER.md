# Project Handover Report — Market Intelligence & Trading Signal Agent

> **Purpose:** This document provides complete context for any future developer or AI model to resume work on this project without needing to re-discover anything.

---

## 1. What This Project Is

An automated market intelligence platform that:
- Fetches real-time stock prices (yfinance)
- Computes technical indicators (RSI, SMA, 52-week high/low)
- Evaluates user-configurable buy/sell rules (YAML, no code changes)
- Aggregates financial news from RSS feeds
- Generates an AI market brief via Google Gemini
- Persists everything to SQLite
- Delivers via Telegram bot and a Streamlit web dashboard
- Supports historical backtesting of trading rules

**Target user:** A swing trader who wants automated daily signals and briefings instead of manually watching YouTube experts and maintaining a Google Sheet.

**Budget constraint:** ~$0/month. Free tiers only.

---

## 2. Current State (as of 2026-10-29)

### Working
- Full pipeline: fetch → compute → evaluate → summarize → persist → deliver
- Dry run mode (`DRY_RUN=1`) prints brief without Telegram
- Gemini LLM brief generation (model: `gemini-3.1-flash-lite`)
- SQLite persistence (signals, briefs, news tables)
- Backtester (`python -m src.backtest --months 12`)
- Streamlit dashboard (brief, signal metrics, history charts, news)
- News RSS ingestion with age filtering and watchlist prioritization
- `.env` loading via `python-dotenv`

### Not yet done
- Telegram bot delivery (code exists but credentials not configured)
- GitHub Actions scheduled workflow
- Streamlit Community Cloud deployment
- YouTube transcript ingestion (Phase 3)
- On-demand `/research` Telegram command (Phase 3)
- Groq/Ollama LLM adapter (optional)

---

## 3. How to Run

### Prerequisites
- Python 3.12+ (tested on 3.12.13)
- Internet access (yfinance, RSS, Gemini API)

### Setup
```bash
cd market-intelligence-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
```

### Commands
```bash
# Dry run (no Telegram, prints brief to console)
DRY_RUN=1 python -m src.main

# Live run (sends to Telegram)
python -m src.main

# Backtest rules over historical data
python -m src.backtest --months 12 --csv

# Dashboard
streamlit run dashboard/app.py
```

### Environment Variables (.env)
| Variable | Required | Where to get |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Live mode only | @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | Live mode only | @userinfobot on Telegram |
| `GEMINI_API_KEY` | LLM brief | https://aistudio.google.com/apikey |

---

## 4. Architecture

```
src/main.py (orchestrator)
├── src/config.py                  → loads YAML configs + .env
├── src/ingestion/price_yfinance.py → fetches OHLCV data from Yahoo
├── src/ingestion/news_rss.py       → parses RSS feeds, filters by age/watchlist
├── src/engine/indicators.py        → computes RSI, SMA, 52w high/low (pure pandas)
├── src/engine/rules.py             → evaluates YAML rule expressions via asteval
├── src/briefing/summarizer.py      → calls Gemini API, falls back to template
├── src/store/db.py                 → SQLite persistence (signals, briefs, news)
├── src/delivery/telegram_bot.py    → sends messages via Telegram Bot API
└── src/backtest/engine.py          → replays rules over history, simulates trades
```

**Data flow (single run):**
1. Load configs (watchlist, rules, sources)
2. Fetch prices for all watchlist symbols
3. Compute indicators (RSI, SMA, 52w high/low)
4. Evaluate buy/sell rules → signal per symbol
5. Fetch latest news headlines
6. Generate brief (Gemini LLM or template fallback)
7. Save signals + brief + news to SQLite
8. Deliver via Telegram (or print in dry-run mode)

---

## 5. Key Configuration Files

### config/watchlist.yaml
Symbols to track. Currently: AAPL, NVDA, MSFT, GOOGL, AMZN, META, TCS.NS, INFY.NS.
Edit freely. Yahoo Finance symbols (`.NS` suffix for NSE India).

### config/rules.yaml
Trading rules as simple expressions. Available variables:
`close, rsi, sma_fast, sma_long, sma_fast_prev, sma_long_prev, pct_change_1d, volume, high_52w, low_52w`

Current rules:
- **Buy:** RSI < 35 (oversold), Golden cross with prev-bar confirmation
- **Sell:** RSI > 70 (overbought), Death cross with confirmation, 52-week low breakout
- **Risk:** stop_loss_pct: 8, take_profit_pct: 20

### config/sources.yaml
RSS feeds with filtering config:
- `max_age_hours: 36` — ignore headlines older than this
- `max_items: 40` — cap headlines passed to LLM
- `prioritize_watchlist: true` — sort headlines mentioning watchlist tickers first

### config/schedule.yaml
Documentation of intended cron schedules (actual cron lives in GitHub Actions).

---

## 6. Known Issues & Gotchas

1. **pandas-ta removed.** Originally used `pandas-ta`, but it requires `numba`/`llvmlite` which has no musl (Alpine) wheel. Replaced with pure pandas/numpy in `src/engine/indicators.py`. If deploying on glibc systems, you could optionally switch back.

2. **yfinance column names.** yfinance 1.x returns capitalized columns (`Close`, `Open`). The adapter normalizes to lowercase. If yfinance changes again, check `price_yfinance.py`.

3. **Gemini model name.** The working model for the current API key is `gemini-3.1-flash-lite`. Google deprecates models frequently — if you get a 404, check available models via:
   ```
   https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY
   ```

4. **google-generativeai deprecated.** The project uses the newer `google-genai` package. Do not switch back to `google.generativeai`.

5. **SQLite path.** Default is `data/signals.sqlite`. The `data/` directory is gitignored. It gets created automatically.

6. **Dashboard RSI display.** The `evaluate_symbol` method returns `close/rsi/sma_fast/sma_long` in the signal dict. If these show `None`, check that `src/engine/rules.py` returns these fields.

---

## 7. Project History

| Date | What happened |
|---|---|
| 2026-05-31 | PRD and architecture docs written. v2 created with backtester, dashboard, docs. |
| 2026-06-01 | Session report: Phase 2 features implemented (news, LLM brief, dashboard, backtest). |
| 2026-10-20 | v3 created as modular refactor. v2 and v3 merged: v3 structure + v2 features. |
| 2026-10-20 | Fixed: missing `import pandas`, yfinance column names, `evaluate_symbol` return fields. |
| 2026-10-20 | Replaced pandas-ta with pure pandas (musl compatibility). Installed on Alpine Linux. |
| 2026-10-29 | Gemini API key added. Switched from `google-generativeai` to `google-genai`. Model set to `gemini-3.1-flash-lite`. |
| 2026-10-29 | Created clean `market-intelligence-agent/` folder for GitHub push. |

---

## 8. Deployment Plan (Not Yet Done)

### Recommended: GitHub Actions + Streamlit Cloud (all free)

1. **Push to GitHub:**
   ```bash
   cd market-intelligence-agent
   git init && git add . && git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Add GitHub Secrets** (repo → Settings → Secrets → Actions):
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

3. **Create GitHub Actions workflow** (`.github/workflows/scheduled-run.yml`):
   ```yaml
   name: Market Brief
   on:
     schedule:
       - cron: '30 12 * * 1-5'   # US pre-market
       - cron: '30 21 * * 1-5'   # US post-market
   jobs:
     run:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with: { python-version: '3.12' }
         - run: pip install -r requirements.txt
         - run: python -m src.main
           env:
             GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
             TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
             TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
   ```

4. **Deploy dashboard:** Connect repo to Streamlit Community Cloud (share.streamlit.io). Set secrets in Streamlit Cloud settings.

### Alternative: Oracle Cloud Always-Free VM
Run everything on one box: cron + Streamlit + Telegram + SQLite. No GitHub Actions dependency.

---

## 9. Future Roadmap

| Phase | Scope | Status |
|---|---|---|
| Phase 1 (MVP) | Prices, rules engine, SQLite, Telegram | Done |
| Phase 2 | News, LLM brief, dashboard, backtest | Done |
| Phase 3 | YouTube transcripts, `/research` Telegram command, macro data (FRED) | Not started |
| Phase 4 | Supabase (Postgres), portfolio tracking with entry/exit prices | Not started |

---

## 10. Contact / Artifacts

- **Source code:** `market-intelligence-agent/` (clean folder for GitHub)
- **Original working copy:** `market_intelligence_project 3/` (has .venv and data/)
- **Older iteration (v2):** `market_intelligence_project 2/` (has full docs, backtester)
- **Session report:** `docs/session_report.md`
- **PRD:** `docs/PRD.md`
- **Architecture:** `docs/ARCHITECTURE.md`
