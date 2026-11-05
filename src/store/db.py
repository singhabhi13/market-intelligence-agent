import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any


class SQLiteStore:
    def __init__(self, db_path: str = "data/signals.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY,
                    ts TEXT NOT NULL,
                    symbol TEXT,
                    signal TEXT,
                    rationale TEXT,
                    close REAL,
                    rsi REAL,
                    sma_fast REAL,
                    sma_long REAL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS briefs (
                    id INTEGER PRIMARY KEY,
                    ts TEXT NOT NULL,
                    content TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    source TEXT,
                    url TEXT,
                    published TEXT
                )
            """)
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_signals(self, signals: List[Dict[str, Any]]):
        ts = self._now()
        with self._get_conn() as conn:
            cur = conn.cursor()
            for s in signals:
                cur.execute(
                    "INSERT INTO signals (ts, symbol, signal, rationale, close, rsi, sma_fast, sma_long) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ts, s["symbol"], s["signal"], s["rationale"], s.get("close"), s.get("rsi"), s.get("sma_fast"), s.get("sma_long")),
                )
            conn.commit()

    def save_brief(self, content: str):
        ts = self._now()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO briefs (ts, content) VALUES (?, ?)", (ts, content))
            conn.commit()

    def save_news(self, articles: List[Dict[str, Any]]):
        with self._get_conn() as conn:
            cur = conn.cursor()
            for a in articles:
                cur.execute(
                    "INSERT INTO news (title, source, url, published) VALUES (?, ?, ?, ?)",
                    (a.get("title"), a.get("source"), a.get("link"), a.get("published", "")),
                )
            conn.commit()
