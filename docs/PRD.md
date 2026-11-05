# Product Requirements Document (PRD)
## Personal Market Intelligence & Trading Signal Agent

| | |
|---|---|
| **Document version** | 1.0 |
| **Date** | 2026-05-31 |
| **Owner** | A. Singh (Investor / Swing Trader) |
| **Status** | Draft for MVP build |
| **Budget posture** | Open-source / free-tier / low-cost only |

---

## 1. Overview

### 1.1 Problem statement
The user is an active investor and swing trader who needs to stay continuously informed about finance, markets, and the economy. Today the user depends on YouTube market experts and a manually-maintained Google Sheet for buy/sell indications. Both are **passive, fragmented, and easy to miss**. Important, time-sensitive, market-moving information is missed, and portfolio signal generation requires manual spreadsheet refreshes.

### 1.2 Vision
An **always-on, AI-agent-driven platform** that:
1. Proactively **briefs** the user with personalized market intelligence.
2. **Researches** stocks/sectors/macro themes on demand and proactively.
3. Tracks a **portfolio/watchlist** and emits **Buy/Sell/Hold** signals from user-defined, editable rules.
4. Runs **automatically in the cloud** and delivers reports via **Telegram and a web dashboard** — using **open-source, free/low-budget** tooling.

### 1.3 Goals & success criteria
- The user no longer misses material market events relevant to their holdings/watchlist.
- Time spent manually gathering information drops by ~80%.
- The Google Sheet is fully replaced by an automated, cloud-hosted engine.
- Trading rules are editable by the user at any time without code changes.
- Total running cost stays at or near **$0/month** (free tiers).

### 1.4 Non-goals (initial release)
- No automated order placement / broker execution (signals only, human decides).
- No financial advice guarantees — informational tool only.
- No real-time tick-level streaming in MVP (EOD + scheduled intraday is enough).

---

## 2. Users & personas

| Persona | Description | Primary needs |
|---|---|---|
| **Primary (the user)** | Active swing trader, tech-stock focus (US/NASDAQ), also India & global | Timely briefs, signal alerts, automated rules, zero manual Google Sheet updates |

### 2.1 Market scope
- **Priority 1:** US / NASDAQ — **technology stocks**.
- **Priority 2:** India (NSE/BSE).
- **Priority 3:** Select global / other, when notably relevant.

---

## 3. Requirements

### 3.1 Functional requirements (Business Requirements BR1–BR13)

**Pillar A – Intelligence & Briefing**
- **BR1 – Personalized curation.** Filter/prioritize finance, market, and economy news by the user's preferences, holdings, watchlist, and sectors (tech-weighted).
- **BR2 – Proactive briefing.** Scheduled digests (pre-market, post-market, weekend) plus event-triggered alerts for high-impact news.
- **BR3 – Autonomous research.** On-demand and proactive research on a ticker, sector, or macro theme, returning synthesized, actionable summaries.
- **BR4 – Expert commentary aggregation.** Ingest and summarize trusted sources (YouTube channels, analysts, news) so the user gets insight without watching hours of video.
- **BR5 – Actionable & trader-focused.** Surface catalysts, earnings, economic calendar events, and technical/sentiment signals relevant to swing trades.
- **BR6 – Self-service awareness.** Reduce dependence on third parties; empower the user to independently discover market-moving information.

**Pillar B – Portfolio & Signals**
- **BR7 – Portfolio & watchlist management.** Add/track stocks with entry price, quantity, target, stop-loss, and notes.
- **BR8 – Rules-based signal engine.** Fetch data, compute indicators, apply rules, output Buy/Sell/Hold per instrument (replaces the Google Sheet).
- **BR13 – Configurable rules.** Rules defined in a human-editable config (YAML/JSON); engine reads them dynamically each run. Editable anytime, no code change.

**Pillar C – Automation & Hosting**
- **BR9 – Automation.** Scheduled execution (cron), no manual trigger.
- **BR10 – Cloud hosting.** Runs unattended on free/low-cost infrastructure.

**Pillar D – Delivery & Cost**
- **BR11 – Multi-channel delivery.** Reports via Telegram bot **and** a web dashboard/link.
- **BR12 – Open-source / low-budget.** Prefer free, open-source, self-hostable tools.

### 3.2 Non-functional requirements

| Category | Requirement |
|---|---|
| **Cost** | ~$0/month target; never exceed low single-digit USD/month. |
| **Reliability** | Scheduled job must run on time; failures alert the user via Telegram. |
| **Security** | API keys/secrets stored as encrypted secrets (never committed). |
| **Maintainability** | Config-driven rules; modular ingestion sources. |
| **Latency** | Daily brief delivered within the chosen schedule window (e.g., pre-market). |
| **Extensibility** | New data sources, rules, and channels added without rewrites. |
| **Data accuracy** | Use reputable free data sources; flag stale/missing data. |
| **Compliance** | Clearly labeled "informational, not financial advice." |

### 3.3 Rule engine specification (BR8/BR13)
The engine evaluates each rule expression against computed indicator values and emits a signal with the rationale (which rules fired).

Rules are declarative. Example schema (YAML):

```yaml
universe:
  - AAPL
  - NVDA
  - MSFT

indicators:
  rsi: {period: 14}
  sma_fast: {period: 20}
  sma_long: {period: 50}

rules:
  buy:
    - "rsi < 35"
    - "sma_fast > sma_long"  # golden-cross bias
  sell:
    - "rsi > 70"
    - "close < sma_long"
# Hold = neither buy nor sell conditions met

risk:
  stop_loss_pct: 8
  take_profit_pct: 20
```

---

## 4. Scope & phased roadmap

| Phase | Scope | BRs | Outcome |
|---|---|---|---|
| **Phase 1 (MVP)** | Portfolio/watchlist config + rules engine + data fetch + **Telegram report** | BR7, BR8, BR9, BR10, BR11(partial), BR12, BR13 | Google Sheet replaced; daily automated signals to Telegram |
| **Phase 2** | News/RSS ingestion + LLM-summarized personalized brief | BR1, BR2, BR5 | Daily curated market brief |
| **Phase 3** | YouTube transcript summarization + on-demand research agent | BR3, BR4, BR6 | Expert-commentary digests + "research this" command |
| **Phase 4** | Web dashboard (history, charts, signal log) | BR11(full) | Interactive web view alongside Telegram |

---

## 5. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Free data source rate limits / outages | Missing/stale signals | Cache; multiple providers (yfinance + Finnhub/Alpha Vantage fallback) |
| Yahoo Finance unofficial API breakage | Engine fails | Abstract data layer; swap providers via config |
| LLM cost creep | Budget overrun | Use free-tier or local model (Ollama); summarize selectively |
| Over-reliance on signals | Bad trades | Label as informational; show rationale; human-in-the-loop |
| Secret leakage | Security | Use GitHub Actions Secrets / env vars; never commit keys |

---

## 6. Open questions
- Preferred Telegram alert frequency (daily only vs. intraday triggers)?
- Which specific YouTube channels/analysts to prioritize (Phase 3)?
- Web dashboard hosting preference (Streamlit Cloud vs. GitHub Pages + static)?
- India data source preference (NSE tools can be flaky) — acceptable to use EOD?
