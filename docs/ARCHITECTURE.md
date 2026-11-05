# Technical Architecture
## Personal Market Intelligence & Trading Signal Agent

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | 2026-05-31 |
| **Companion to** | PRD.md |
| **Design posture** | Open-source, free-tier, low-cost, modular |

---

## 1. Architecture principles
1. **Config over code** — universe, rules, sources, schedules live in YAML/JSON.
2. **Modular ingestion** — each data source is a pluggable adapter behind an interface.
3. **Serverless / zero-ops first** — prefer scheduled CI runners over always-on servers.
4. **Stateless compute, durable data** — compute runs on schedule; state in a small DB/repo.
5. **Provider-agnostic data layer** — swap market-data/LLM providers without touching logic.
6. **Fail loud** — any run failure pings Telegram.

---

## 2. High-level system diagram

```
┌───────────────────────────────────────────────┐
│        SCHEDULER (GitHub Actions cron)        │
│       pre-market / post-market / weekend      │
└───────────────────────┬───────────────────────┘
                        │
                        │ triggers
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                     AGENT CORE (Python)                       │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │  Ingestion   │───►│  Rules /     │───►│  Briefing /     │  │
│  │   Adapters   │    │  Signal      │    │  LLM            │  │
│  │              │    │  Engine      │    │  Summarizer     │  │
│  └──────────────┘    └──────────────┘    └─────────────────┘  │
│         │                   │                       │         │
│         ▼                   ▼                       ▼         │
│     Market data        Buy/Sell/Hold       Personalized brief │
│     News / RSS         + rationale         (news + signals)   │
│     YT transcripts                                            │
└───────────────────────┬───────┬───────────────────────┘
                        │       │
                        │       │ persist + deliver
                        ▼       ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  DATA STORE  │ │ TELEGRAM BOT │ │ WEB DASHBOARD│
        │   SQLite /   │ │ (push report)│ │  (Streamlit) │
        │   Supabase   │ │              │ │              │
        │+ config repo │ │              │ │              │
        └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 3. Component design

### 3.1 Scheduler
- **Choice:** **GitHub Actions** scheduled workflows (`on: schedule: cron`).
- **Why:** Free for public repos / generous free minutes for private; zero servers; secrets management built in; logs & retries included.
- **Alternative:** Oracle Cloud Always-Free VM + system `cron`, or Render/Railway cron.
- Multiple cron entries: pre-market US, post-market US, India EOD, weekend deep-brief.

### 3.2 Ingestion adapters (pluggable)
Interface: `fetch(symbols|query) -> normalized DataFrame/records`.

| Adapter | Source (free) | Used for |
|---|---|---|
| `PriceAdapter` | `yfinance` (primary), Finnhub / Alpha Vantage free tier (fallback) | OHLCV, fundamentals |
| `NewsAdapter` | RSS feeds, NewsAPI free tier, GDELT | Market/economy news |
| `YouTubeAdapter` | `youtube-transcript-api` | Expert commentary transcripts |
| `MacroAdapter` | FRED API (free), economic calendar feeds | Macro/econ data |

Each adapter normalizes to a common schema so downstream code is source-agnostic.

### 3.3 Rules / signal engine
- Reads `config/rules.yaml` (BR13).
- Pipeline: `load prices -> compute indicators (pandas-ta) -> evaluate rule expressions -> emit {symbol, signal, rationale, indicators}`.
- Rule expressions evaluated safely (restricted `eval` / `asteval` over indicator vars).
- Output stored to DB and passed to summarizer/delivery.

### 3.4 Briefing / LLM summarizer
- Aggregates news + signals into a concise, personalized brief.
- **LLM options (cost-tiered):**
  - **Free/local:** **Ollama** (Llama 3.1 / Qwen2.5) on the Always-Free VM.
  - **Free-tier API:** Google Gemini free tier, Groq free tier (very fast).
  - **Low-cost API:** OpenAI/Anthropic small models, used selectively.
- Prompt templates keep tone "trader-focused, concise, cite sources."

### 3.5 Data store
- **MVP:** **SQLite** committed-as-artifact or a JSON/CSV in the repo for portfolio + signal history.
- **Phase 2+:** **Supabase (Postgres, free tier)** for history, dashboard queries.
- Config (rules, watchlist) versioned in Git for auditability.

### 3.6 Delivery
- **Telegram bot** (BR11): `python-telegram-bot`; bot token in secrets; push formatted report (Markdown), support commands like `/research NVDA`, `/signals`, `/brief`.
- **Web dashboard** (BR11): **Streamlit** app on Streamlit Community Cloud (free) or static export to GitHub Pages; shows signals, history, charts, latest brief.

### 3.7 Secrets & config
- API keys, bot token -> **GitHub Actions Secrets** / `.env` (git-ignored).
- User-editable: `config/watchlist.yaml`, `config/rules.yaml`, `config/sources.yaml`, `config/schedule.yaml`.

---

## 4. Recommended tech stack (all free / OSS / low-cost)

| Layer | Tool | Tier |
|---|---|---|
| Language | Python 3.11+ | Free |
| Market data | `yfinance`, Finnhub, Alpha Vantage, FRED | Free / free-tier |
| Indicators | `pandas`, `pandas-ta` (or TA-Lib) | OSS |
| News | RSS (`feedparser`), NewsAPI, GDELT | Free / free-tier |
| YouTube | `youtube-transcript-api` | OSS |
| LLM | Ollama (local) / Groq / Gemini free tier | Free / free-tier |
| Rules eval | `asteval` / safe expression eval | OSS |
| Scheduler | GitHub Actions cron | Free |
| Hosting | GitHub Actions + Oracle Always-Free VM | Free |
| DB | SQLite -> Supabase (Postgres) | Free |
| Delivery | `python-telegram-bot`, Streamlit | OSS / free |
| Secrets | GitHub Actions Secrets / dotenv | Free |

---

## 5. Suggested repository structure

```
market-intelligence-agent/
├── docs/
│   ├── PRD.md
│   └── ARCHITECTURE.md
├── config/
│   ├── watchlist.yaml
│   ├── rules.yaml
│   ├── sources.yaml
│   └── schedule.yaml
├── src/
│   ├── ingestion/
│   │   ├── base.py
│   │   ├── price_yfinance.py
│   │   ├── news_rss.py
│   │   └── youtube.py
│   ├── engine/
│   │   ├── indicators.py
│   │   └── rules.py
│   ├── briefing/
│   │   └── summarizer.py
│   ├── delivery/
│   │   └── telegram_bot.py
│   │   └── formatters.py
│   ├── store/
│   │   └── db.py
│   ├── main.py              # orchestrates a single scheduled run
├── dashboard/
│   ├── app.py               # Streamlit
├── .github/workflows/
│   └── scheduled-run.yaml   # cron
├── requirements.txt
└── .env.example
```

---

## 6. Data flow (single scheduled run)

1. **Trigger:** GitHub Actions cron fires `python -m src.main`.
2. **Load config:** watchlist, rules, sources, schedule.
3. **Ingest:** prices (yfinance) + news (RSS/NewsAPI) [+ YT transcripts in Phase 3].
4. **Compute:** indicators via pandas-ta.
5. **Evaluate:** rules -> Buy/Sell/Hold + rationale per symbol.
6. **Summarize:** LLM builds personalized brief (news + signals).
7. **Persist:** write signals/brief to DB + history.
8. **Deliver:** push to Telegram; update web dashboard data.
9. **On failure:** send error alert to Telegram.

---

## 7. Phasing aligned to architecture

| Phase | Components activated |
|---|---|
| **1 (MVP)** | Scheduler, PriceAdapter, Rules engine, SQLite store, Telegram delivery |
| **2** | NewsAdapter, LLM summarizer, brief delivery |
| **3** | YouTubeAdapter, research command handler, MacroAdapter |
| **4** | Supabase store, Streamlit dashboard |

---

## 8. Cost summary

- **Compute/scheduling:** $0 (GitHub Actions free tier / Oracle Always-Free).
- **Data:** $0 (free + free-tier APIs).
- **LLM:** $0 (local Ollama / free-tier) → optional low single-digit USD if upgraded.
- **Delivery/hosting:** $0 (Telegram, Streamlit Community Cloud).
- **Estimated total:** ~$0/month.
