"""
Streamlit dashboard for the market intelligence agent.

Run: streamlit run dashboard/app.py
Reads signal/news/brief history from the SQLite store.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "signals.sqlite"

ACTION_COLOR = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪", "NO_DATA": "⚫"}

st.set_page_config(page_title="Market Intelligence Agent", layout="wide")
st.title("📈 Personal Market Intelligence & Signals")
st.caption("Informational only — not financial advice.")


def _conn():
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(DB_PATH)


conn = _conn()
if conn is None:
    st.warning("No data yet. Run `python -m src.main` (or `DRY_RUN=1 ...`) first.")
    st.stop()


def read(sql: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(sql, conn)
    except Exception:
        return pd.DataFrame()


briefs = read("SELECT ts, content FROM briefs ORDER BY id DESC LIMIT 1")
st.subheader("🤖 Latest Brief")
if not briefs.empty:
    st.caption(f"Generated: {briefs.iloc[0]['ts']}")
    st.markdown(briefs.iloc[0]["content"])
else:
    st.info("No brief stored yet.")

st.divider()

signals = read("SELECT * FROM signals ORDER BY id DESC")
st.subheader("🎯 Latest Signals")
if not signals.empty:
    latest_ts = signals.iloc[0]["ts"]
    latest = signals[signals["ts"] == latest_ts].copy()
    latest["action"] = latest["signal"].map(ACTION_COLOR).fillna("⚪")
    cols = st.columns(min(4, len(latest)))
    for i, (_, row) in enumerate(latest.iterrows()):
        with cols[i % 4]:
            rsi = row["rsi"]
            rsi_s = f"{rsi:.1f}" if pd.notna(rsi) else "n/a"
            st.metric(
                label=f"{ACTION_COLOR.get(row['signal'], '')} {row['symbol']}",
                value=row["signal"],
                delta=f"RSI {rsi_s}",
            )
    st.dataframe(
        latest[["symbol", "signal", "close", "rsi", "rationale"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No signals stored yet.")

st.divider()

st.subheader("📊 Signal History")
if not signals.empty:
    syms = sorted(signals["symbol"].unique())
    sym = st.selectbox("Symbol", syms)
    hist = signals[signals["symbol"] == sym].copy()
    hist["ts"] = pd.to_datetime(hist["ts"])
    hist = hist.sort_values("ts")
    c1, c2 = st.columns(2)
    with c1:
        st.line_chart(hist.set_index("ts")["close"], height=240)
        st.caption("Close")
    with c2:
        st.line_chart(hist.set_index("ts")["rsi"], height=240)
        st.caption("RSI")
    st.dataframe(
        hist[["ts", "signal", "close", "rsi", "rationale"]].iloc[::-1],
        use_container_width=True,
        hide_index=True,
    )

st.divider()

st.subheader("📰 Recent News")
news = read("SELECT title, source, url, published FROM news ORDER BY id DESC LIMIT 30")
if not news.empty:
    for _, n in news.iterrows():
        url = n["url"]
        if url:
            st.markdown(f"- [{n['title']}]({url}) *{n['source']}*")
        else:
            st.markdown(f"- {n['title']} *{n['source']}*")
else:
    st.info("No news stored yet.")
