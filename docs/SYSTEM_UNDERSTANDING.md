# System Understanding Document — Market Intelligence & Trading Signal Agent

> **Audience:** Future developers or AI models who need to understand how this system works end-to-end.

---

## 1. High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL WORLD                                     │
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ Yahoo    │   │ RSS      │   │ Google   │   │ Telegram │   │ GitHub   │ │
│  │ Finance  │   │ Feeds    │   │ Gemini   │   │ Bot API  │   │ Actions  │ │
│  │ (prices) │   │ (news)   │   │ (LLM)    │   │ (delivery)│  │ (cron)   │ │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘ │
│       │              │              │              │              │        │
└───────┼──────────────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AGENT CORE (Python)                                   │
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  Ingestion  │──▶│   Engine    │──▶│   Briefing   │──▶│   Delivery   │  │
│  │  Adapters   │   │  (Signals)  │   │  (LLM/Temp)  │   │  (Telegram)  │  │
│  └─────────────┘   └─────────────┘   └──────────────┘   └──────────────┘  │
│         │                │                  │                   │          │
│         ▼                ▼                  ▼                   ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SQLite Store                                   │   │
│  │              (signals, briefs, news tables)                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────┐
│  Streamlit Dashboard │
│  (reads SQLite)      │
└──────────────────────┘
```

---

## 2. Single Run Data Flow (main.py)

```
START: python -m src.main
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 1: Load Configs                                     │
│                                                          │
│   config/watchlist.yaml ──▶ [AAPL, NVDA, MSFT, ...]     │
│   config/rules.yaml     ──▶ {buy: [...], sell: [...]}   │
│   config/sources.yaml   ──▶ {rss_feeds: [...], ...}     │
│   .env                  ──▶ GEMINI_API_KEY, TELEGRAM_*  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 2: Fetch Prices (yfinance)                          │
│                                                          │
│   For each symbol in watchlist:                          │
│     yf.Ticker("AAPL").history(period="6mo")             │
│     → DataFrame [open, high, low, close, volume]         │
│     → columns lowercased                                 │
│                                                          │
│   Result: { "AAPL": DataFrame, "NVDA": DataFrame, ... }  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 3: Compute Indicators (pure pandas/numpy)           │
│                                                          │
│   For each symbol's DataFrame:                          │
│     ┌─────────────────────────────────────────────────┐  │
│     │ close.ewm(alpha=1/14) → RSI(14)                │  │
│     │ close.rolling(20)     → SMA fast (20)           │  │
│     │ close.rolling(50)     → SMA long (50)           │  │
│     │ SMA fast shift(1)     → SMA fast prev           │  │
│     │ SMA long shift(1)     → SMA long prev           │  │
│     │ close.pct_change()    → pct_change_1d           │  │
│     │ high.rolling(252)     → high_52w                │  │
│     │ low.rolling(252)      → low_52w                 │  │
│     └─────────────────────────────────────────────────┘  │
│                                                          │
│   Output: DataFrame with extra indicator columns         │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 4: Evaluate Rules (asteval)                         │
│                                                          │
│   Take latest row of indicators:                         │
│     {close: 340.64, rsi: 57.27, sma_fast: 335.1, ...}  │
│                                                          │
│   Inject into asteval symbol table:                      │
│     aeval.symtable["rsi"] = 57.27                       │
│     aeval.symtable["close"] = 340.64                    │
│     ...                                                  │
│                                                          │
│   Evaluate buy rules:                                    │
│     "rsi < 35"                          → False          │
│     "sma_fast > sma_long and ..."       → False          │
│     → No buy trigger                   → check sell     │
│                                                          │
│   Evaluate sell rules:                                   │
│     "rsi > 70"                          → False          │
│     "sma_fast < sma_long and ..."       → False          │
│     "close < low_52w * 1.02"           → False          │
│     → No sell trigger                   → HOLD          │
│                                                          │
│   Output: {symbol: "AAPL", signal: "HOLD",              │
│            rationale: "No criteria met",                 │
│            close: 340.64, rsi: 57.27, ...}              │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 5: Fetch News (feedparser)                          │
│                                                          │
│   For each RSS feed in sources.yaml:                    │
│     feedparser.parse(url) → entries                     │
│     Filter: published > now - max_age_hours (36h)        │
│     Extract: title, source, link, published              │
│                                                          │
│   Sort: headlines mentioning watchlist symbols first     │
│   Cap: max_items (40)                                    │
│                                                          │
│   Output: [{title: "...", source: "CNBC", ...}, ...]    │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 6: Generate Brief (Gemini or template)             │
│                                                          │
│   ┌─────────────────────────────────────────────────┐    │
│   │ IF GEMINI_API_KEY is set and valid:            │    │
│   │                                                 │    │
│   │   Build prompt:                                 │    │
│   │     "You are a market analyst..."               │    │
│   │     + signals list                              │    │
│   │     + news headlines (15)                       │    │
│   │     + "Generate brief under 300 words"          │    │
│   │                                                 │    │
│   │   Call gemini-3.1-flash-lite                    │    │
│   │   → Returns AI-generated markdown brief        │    │
│   └─────────────────────────────────────────────────┘    │
│                                                          │
│   ┌─────────────────────────────────────────────────┐    │
│   │ ELSE (fallback):                                │    │
│   │                                                 │    │
│   │   Build template:                               │    │
│   │     "### Market Briefing"                       │    │
│   │     + signal list                               │    │
│   │     + top 10 headlines                          │    │
│   └─────────────────────────────────────────────────┘    │
│                                                          │
│   Output: markdown string                                │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 7: Persist to SQLite                                │
│                                                          │
│   data/signals.sqlite                                    │
│   ┌──────────────────────────────────────────────────┐   │
│   │ signals table:  (ts, symbol, signal, rationale,  │   │
│   │                  close, rsi, sma_fast, sma_long) │   │
│   │ briefs table:   (ts, content)                    │   │
│   │ news table:     (title, source, url, published)  │   │
│   └──────────────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ STEP 8: Deliver                                          │
│                                                          │
│   IF DRY_RUN=1:                                          │
│     print(brief) to console          ← testing mode     │
│                                                          │
│   ELSE:                                                  │
│     POST to Telegram Bot API                             │
│     → User receives message on phone                    │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
                     END
```

---

## 3. Component Architecture (Package Structure)

```
market-intelligence-agent/
│
├── config/                          ◄── User-editable, no code changes needed
│   ├── watchlist.yaml               │   Which stocks to track
│   ├── rules.yaml                   │   Buy/sell rule expressions
│   ├── sources.yaml                 │   RSS feeds + filtering params
│   └── schedule.yaml                │   Cron schedule documentation
│
├── src/
│   ├── main.py                      ◄── Orchestrator: wires everything together
│   ├── config.py                    ◄── YAML loader + .env loader
│   │
│   ├── ingestion/                   ◄── Data fetching (pluggable adapters)
│   │   ├── price_yfinance.py        │   Stock prices from Yahoo Finance
│   │   └── news_rss.py              │   News headlines from RSS feeds
│   │
│   ├── engine/                      ◄── Signal computation
│   │   ├── indicators.py            │   RSI, SMA, 52w high/low (pure pandas)
│   │   └── rules.py                 │   Rule evaluation via asteval
│   │
│   ├── briefing/                    ◄── AI summary generation
│   │   └── summarizer.py            │   Gemini LLM + template fallback
│   │
│   ├── store/                       ◄── Persistence
│   │   └── db.py                    │   SQLite (signals, briefs, news)
│   │
│   ├── delivery/                    ◄── Output channels
│   │   └── telegram_bot.py          │   Telegram Bot API
│   │
│   └── backtest/                    ◄── Historical validation
│       ├── engine.py                │   Day-by-day rule replay
│       └── __main__.py              │   CLI entry point
│
├── dashboard/
│   └── app.py                       ◄── Streamlit web UI (reads SQLite)
│
├── docs/
│   ├── PRD.md                       ◄── Product requirements
│   ├── ARCHITECTURE.md              ◄── Technical architecture
│   ├── HANDOVER.md                  ◄── Resume-work context
│   └── SYSTEM_UNDERSTANDING.md      ◄── This file
│
├── requirements.txt                 ◄── Python dependencies
├── .env.example                     ◄── Template for secrets
└── .gitignore                       ◄── What NOT to commit
```

**Dependency direction** (who imports whom):

```
main.py
  ├──▶ config.py           (load YAML)
  ├──▶ ingestion/*          (fetch data)
  ├──▶ engine/*             (compute signals)
  ├──▶ briefing/*           (generate brief)
  ├──▶ store/*              (persist)
  └──▶ delivery/*           (send)

backtest/engine.py
  ├──▶ config.py
  ├──▶ engine/rules.py      (evaluate)
  └──▶ ingestion/price_yfinance.py (fetch)

dashboard/app.py
  └──▶ store/db.py          (read only)
```

---

## 4. Signal Engine Detail

```
┌──────────────────────────────────────────────────────────────┐
│                    INPUT: 6 months of daily OHLCV data       │
│                    Example: AAPL DataFrame (126 rows)        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌──────────────────────────────────────┐ │
│  │ Raw Price   │    │         Computed Indicators          │ │
│  │ Data        │    │                                      │ │
│  │             │    │  rsi:        57.27                    │ │
│  │ close: 340  │───▶│  sma_fast:   335.10  (20-day avg)    │ │
│  │ high:  342  │    │  sma_long:   338.50  (50-day avg)    │ │
│  │ low:   338  │    │  sma_fast_prev: 334.80 (yesterday)   │ │
│  │ volume: 50M │    │  sma_long_prev:  338.60 (yesterday)  │ │
│  │             │    │  pct_change_1d:  1.2%                │ │
│  └─────────────┘    │  high_52w:   365.00                  │ │
│                     │  low_52w:    280.00                  │ │
│                     └──────────────┬───────────────────────┘ │
│                                    │                          │
│                                    ▼                          │
│                     ┌──────────────────────────────────────┐ │
│                     │        Rule Evaluation               │ │
│                     │        (asteval interpreter)         │ │
│                     │                                      │ │
│                     │  Buy rules:                          │ │
│                     │    "rsi < 35"                        │ │
│                     │    57.27 < 35 → FALSE               │ │
│                     │                                      │ │
│                     │    "sma_fast > sma_long and          │ │
│                     │     sma_fast_prev <= sma_long_prev"  │ │
│                     │    335.1 > 338.5 → FALSE           │ │
│                     │                                      │ │
│                     │  Sell rules:                         │ │
│                     │    "rsi > 70"                        │ │
│                     │    57.27 > 70 → FALSE               │ │
│                     │                                      │ │
│                     │    "close < low_52w * 1.02"         │ │
│                     │    340 < 285.6 → FALSE             │ │
│                     │                                      │ │
│                     │  No rules fired → HOLD              │ │
│                     └──────────────────┬───────────────────┘ │
│                                        │                      │
├────────────────────────────────────────┼──────────────────────┤
                                        ▼
                     ┌──────────────────────────────────────┐
                     │  OUTPUT:                             │
                     │  {                                   │
                     │    "symbol": "AAPL",                 │
                     │    "signal": "HOLD",                 │
                     │    "rationale": "No criteria met",   │
                     │    "close": 340.64,                  │
                     │    "rsi": 57.27,                     │
                     │    "sma_fast": 335.10,               │
                     │    "sma_long": 338.50                │
                     │  }                                   │
                     └──────────────────────────────────────┘
```

### Rule examples (from config/rules.yaml):

```
BUY when:                          SELL when:
─────────────                      ─────────────
rsi < 35          (oversold)       rsi > 70          (overbought)
                                    
sma_fast > sma_long               sma_fast < sma_long
AND sma_fast_prev                 AND sma_fast_prev
    <= sma_long_prev                  >= sma_long_prev
(golden cross)                    (death cross)
                                    
                                   close < low_52w * 1.02
                                   (breaking near 52w low)
```

---

## 5. Backtest Engine Detail

```
For each symbol, walk through history day by day:

Day 1 ────── Day 2 ────── ... ────── Day N
  │             │                     │
  ▼             ▼                     ▼
Check:       Check:                Check:
signals      signals               signals
  │             │                     │
  ▼             ▼                     ▼

State machine (long-only):
                    ┌──────────┐
          BUY ─────▶│ IN POS   │──────▶ SELL / stop-loss / take-profit
                    │          │                │
                    └──────────┘                │
                         ▲                      │
                         └──────────────────────┘
                              (can re-enter)

Exit rules:
  1. sell_signal  → SELL rule fires
  2. stop_loss    → price drops 8% below entry
  3. take_profit  → price rises 20% above entry
  4. open_eod     → position still open at end → mark to market

Output per symbol:
  - List of trades (entry/exit date, price, return%)
  - Win rate: % of profitable trades
  - Total return: compounded return
  - CSV of all daily signals (optional)
```

---

## 6. Dashboard Data Flow

```
┌─────────────────────┐
│  Streamlit server   │
│  streamlit run      │
│  dashboard/app.py   │
└──────────┬──────────┘
           │ reads
           ▼
┌─────────────────────────────────────────────────────┐
│  data/signals.sqlite                                │
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │signals  │  │briefs   │  │news     │             │
│  │8 rows   │  │1 row    │  │40 rows  │             │
│  │(latest) │  │(latest) │  │(recent) │             │
│  └────┬────┘  └────┬────┘  └────┬────┘             │
│       │            │            │                   │
└───────┼────────────┼────────────┼───────────────────┘
        │            │            │
        ▼            ▼            ▼
┌─────────────────────────────────────────────────────┐
│  Dashboard sections:                                │
│                                                     │
│  🤖 Latest Brief     ← briefs table (latest row)   │
│  🎯 Latest Signals   ← signals table (latest ts)    │
│     - 8 metric cards (color-coded BUY/SELL/HOLD)   │
│     - RSI values in delta                          │
│  📊 Signal History   ← signals table (per symbol)   │
│     - Close price line chart                       │
│     - RSI line chart                               │
│     - Full signal history table                    │
│  📰 Recent News      ← news table (latest 30)      │
│     - Clickable headlines with source              │
└─────────────────────────────────────────────────────┘
```

---

## 7. Deployment Architecture (Target State)

```
┌─────────────────────────────────────────────────────────────────┐
│                        GITHUB REPO                              │
│  market-intelligence-agent                                      │
│  ├── src/ config/ dashboard/ docs/ requirements.txt             │
│  ├── .github/workflows/scheduled-run.yml                        │
│  └── Secrets: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, ...          │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
     ┌──────────▼──────────┐       ┌──────────▼──────────┐
     │   GitHub Actions    │       │  Streamlit Cloud    │
     │   (scheduled cron)  │       │  (dashboard host)   │
     │                     │       │                     │
     │  Pre-market: 12:30  │       │  Reads SQLite       │
     │  Post-market: 21:30 │       │  Shows charts       │
     │  India EOD: 10:30   │       │  Shows brief        │
     │                     │       │                     │
     │  Runs:              │       │  Port: 8501         │
     │  python -m src.main │       │                     │
     └──────────┬──────────┘       └─────────────────────┘
                │
     ┌──────────▼──────────┐
     │   Data + Delivery   │
     │                     │
     │  yfinance → prices  │
     │  RSS → news         │
     │  Gemini → brief     │
     │  SQLite → persist   │
     │  Telegram → notify  │
     └─────────────────────┘
```

---

## 8. Key Design Decisions

| Decision | Why |
|---|---|
| **YAML for rules** | User can edit buy/sell rules without touching code |
| **asteval for evaluation** | Safe expression evaluation (no arbitrary code execution) |
| **Pure pandas indicators** | No numba/llvmlite dependency (works on Alpine/musl) |
| **SQLite** | Zero-ops local storage, no server needed |
| **Template fallback** | System still works if Gemini API is down/key missing |
| **lowercase columns** | yfinance 1.x returns `Close` → normalize to `close` |
| **Column normalization** | Insulates the rest of the code from yfinance API changes |
| **Signal dict includes indicators** | Dashboard needs `close`/`rsi` for display |

---

## 9. How the Pieces Connect (One Diagram)

```
  YOUR EDITS                    THE ENGINE                      OUTPUT
  ──────────                    ──────────                      ──────

  watchlist.yaml ──┐
                   │     ┌──────────────────┐
  rules.yaml ──────┼────▶│                  │     ┌──────────────┐
                   │     │   main.py        │     │  SQLite      │
  sources.yaml ────┼────▶│   orchestrator   │────▶│  (history)   │
                   │     │                  │     └──────┬───────┘
  .env ────────────┘     │  1. fetch prices │            │
                         │  2. compute RSI  │            │
   Yahoo Finance ◄───────│  3. eval rules   │            ▼
   (live data)           │  4. fetch news   │     ┌──────────────┐
                         │  5. LLM brief    │     │  Streamlit   │
   RSS Feeds ◄───────────│  6. save to DB   │     │  Dashboard   │
   (live news)           │  7. send/notify  │     └──────────────┘
                         │                  │
   Google Gemini ◄───────│                  │
   (AI summary)          └────────┬─────────┘
                                  │
                                  ▼
                           ┌──────────────┐
                           │  Telegram    │
                           │  (your phone)│
                           └──────────────┘
```
