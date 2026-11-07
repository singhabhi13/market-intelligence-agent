"""Render a static HTML dashboard from the signals SQLite database.

Usage: python tools/render_html.py
Output: docs/index.html (served by GitHub Pages)
"""
from __future__ import annotations

import html
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "signals.sqlite"
OUT_PATH = BASE_DIR / "docs" / "index.html"

ACTION_CLASS = {"BUY": "buy", "SELL": "sell", "HOLD": "hold"}
ACTION_DOT = {"BUY": "#22c55e", "SELL": "#ef4444", "HOLD": "#94a3b8"}


def esc(v) -> str:
    if v is None:
        return ""
    return html.escape(str(v))


def fmt_num(v, digits=2) -> str:
    try:
        if v is None:
            return "n/a"
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def md_to_html(md: str) -> str:
    """Minimal markdown -> HTML for the brief (headings, bold, italic, lists, links)."""
    out_lines = []
    in_list = False
    for raw in md.splitlines():
        stripped = raw.strip()
        if not stripped:
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append("")
            continue

        # detect block type on raw text BEFORE inline formatting
        heading = None
        if stripped.startswith("#### "):
            heading, content = "h4", stripped[5:]
        elif stripped.startswith("### "):
            heading, content = "h3", stripped[4:]
        elif stripped.startswith("## "):
            heading, content = "h2", stripped[3:]
        elif stripped.startswith("# "):
            heading, content = "h3", stripped[2:]
        elif stripped.startswith(("- ", "* ")):
            content = stripped[2:]
            if not in_list:
                out_lines.append("<ul>")
                in_list = True
            out_lines.append(f"<li>{_inline(esc(content))}</li>")
            continue
        else:
            content = stripped

        if in_list:
            out_lines.append("</ul>")
            in_list = False
        body = _inline(esc(content))
        if heading:
            out_lines.append(f"<{heading}>{body}</{heading}>")
        else:
            out_lines.append(f"<p>{body}</p>")
    if in_list:
        out_lines.append("</ul>")
    return "\n".join(out_lines)


def _inline(s: str) -> str:
    # already-escaped text; apply bold/italic/links/code
    import re
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def sparkline(values: list, color: str, width: int = 220, height: int = 48) -> str:
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return '<span class="muted">n/a</span>'
    vmin, vmax = min(vals), max(vals)
    span = (vmax - vmin) or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        if v is None:
            continue
        x = i * (width - 4) / (n - 1) + 2
        y = height - 4 - (v - vmin) / span * (height - 8)
        pts.append(f"{x:.1f},{y:.1f}")
    last = pts[-1].split(",") if pts else ["0", "0"]
    dot = f'<circle cx="{last[0]}" cy="{last[1]}" r="3" fill="{color}"/>'
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="sparkline">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(pts)}"/>'
        f"{dot}</svg>"
    )


def load(conn):
    def q(sql, args=()):
        return conn.execute(sql, args).fetchall()

    cols = [d[1] for d in conn.execute("PRAGMA table_info(signals)")]
    signals = [dict(zip(cols, r)) for r in q(
        "SELECT * FROM signals ORDER BY ts DESC, symbol"
    )]
    brief = q("SELECT ts, content FROM briefs ORDER BY id DESC LIMIT 1")
    news = q("SELECT title, source, url, published FROM news ORDER BY id DESC LIMIT 30")
    return signals, (brief[0] if brief else None), news


def build_html(signals, brief, news) -> str:
    generated = signals[0]["ts"] if signals else "n/a"
    latest_ts = signals[0]["ts"] if signals else None
    latest = [s for s in signals if s["ts"] == latest_ts]

    # history per symbol (chronological)
    hist: dict[str, list] = {}
    for s in reversed(signals):  # signals sorted desc → reverse to asc
        hist.setdefault(s["symbol"], []).append(s)

    # --- signal cards ---
    cards = []
    for s in latest:
        cls = ACTION_CLASS.get(s["signal"], "hold")
        rsi = fmt_num(s.get("rsi"), 1)
        cards.append(f"""
        <div class="card {cls}">
          <div class="card-sym">{esc(s['symbol'])}</div>
          <div class="card-sig">{esc(s['signal'])}</div>
          <div class="card-meta">RSI {rsi} · {fmt_num(s.get('close'))}</div>
        </div>""")

    # --- latest table ---
    rows = []
    for s in latest:
        rows.append(
            "<tr>"
            f"<td>{esc(s['symbol'])}</td>"
            f'<td><span class="pill {ACTION_CLASS.get(s["signal"], "hold")}">{esc(s["signal"])}</span></td>'
            f"<td>{fmt_num(s.get('close'))}</td>"
            f"<td>{fmt_num(s.get('rsi'), 1)}</td>"
            f"<td>{fmt_num(s.get('sma_fast'))}</td>"
            f"<td>{fmt_num(s.get('sma_long'))}</td>"
            f"<td class='rationale'>{esc(s.get('rationale'))}</td>"
            "</tr>"
        )

    # --- per-symbol history ---
    sym_sections = []
    for sym in sorted(hist):
        rows_h = hist[sym]
        closes = [r.get("close") for r in rows_h]
        rsis = [r.get("rsi") for r in rows_h]
        n = len(rows_h)
        last = rows_h[-1]
        hist_rows = []
        for r in reversed(rows_h[-60:]):
            hist_rows.append(
                "<tr>"
                f"<td class='ts'>{esc(r['ts'][:16].replace('T', ' '))}</td>"
                f'<td><span class="pill {ACTION_CLASS.get(r["signal"], "hold")}">{esc(r["signal"])}</span></td>'
                f"<td>{fmt_num(r.get('close'))}</td>"
                f"<td>{fmt_num(r.get('rsi'), 1)}</td>"
                f"<td class='rationale'>{esc(r.get('rationale'))}</td>"
                "</tr>"
            )
        sym_sections.append(f"""
        <details class="sym" open>
          <summary>
            <span class="pill {ACTION_CLASS.get(last['signal'], 'hold')}">{esc(last['signal'])}</span>
            <strong>{esc(sym)}</strong>
            <span class="muted">close {fmt_num(last.get('close'))} · RSI {fmt_num(last.get('rsi'), 1)} · {n} runs</span>
          </summary>
          <div class="charts">
            <div class="chart"><div class="chart-label">Close</div>{sparkline(closes, "#38bdf8")}</div>
            <div class="chart"><div class="chart-label">RSI</div>{sparkline(rsis, "#a78bfa")}</div>
          </div>
          <table>
            <thead><tr><th>Time (UTC)</th><th>Signal</th><th>Close</th><th>RSI</th><th>Rationale</th></tr></thead>
            <tbody>{''.join(hist_rows)}</tbody>
          </table>
        </details>""")

    # --- news ---
    news_items = []
    for title, source, url, published in news:
        t = esc(title)
        if url:
            t = f'<a href="{esc(url)}" target="_blank" rel="noopener">{t}</a>'
        pub = esc((published or "")[:16])
        news_items.append(f'<li>{t} <span class="muted">· {esc(source)} · {pub}</span></li>')

    brief_html = (
        md_to_html(brief[1]) if brief else "<p class='muted'>No brief yet. Run the agent first.</p>"
    )
    brief_ts = esc(brief[0][:19].replace("T", " ")) if brief else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Market Intelligence Agent</title>
<style>
  :root {{
    --bg: #0b1220; --panel: #111a2e; --border: #1e2a44;
    --text: #e2e8f0; --muted: #94a3b8;
    --buy: #22c55e; --sell: #ef4444; --hold: #64748b;
    --accent: #38bdf8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 16px 48px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5;
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
  h2 {{ font-size: 1.1rem; margin: 32px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  h3, h4 {{ margin: 16px 0 8px; }}
  .muted {{ color: var(--muted); font-size: 0.85em; }}
  .foot {{ margin-top: 40px; font-size: 0.8rem; color: var(--muted); }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{ background: #1a2438; padding: 1px 5px; border-radius: 4px; font-size: 0.9em; }}

  .brief {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 20px;
  }}
  .brief p {{ margin: 8px 0; }}
  .brief ul {{ margin: 8px 0; padding-left: 20px; }}

  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }}
  .card {{
    background: var(--panel); border: 1px solid var(--border);
    border-left: 4px solid var(--hold); border-radius: 10px; padding: 12px 14px;
  }}
  .card.buy {{ border-left-color: var(--buy); }}
  .card.sell {{ border-left-color: var(--sell); }}
  .card-sym {{ font-weight: 700; font-size: 1.05rem; }}
  .card-sig {{ font-weight: 600; margin-top: 2px; }}
  .card.buy .card-sig {{ color: var(--buy); }}
  .card.sell .card-sig {{ color: var(--sell); }}
  .card-meta {{ color: var(--muted); font-size: 0.8rem; margin-top: 4px; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 0.78rem; text-transform: uppercase; }}
  td.rationale {{ color: var(--muted); font-size: 0.84rem; }}
  td.ts {{ white-space: nowrap; color: var(--muted); font-size: 0.82rem; }}
  tr:last-child td {{ border-bottom: none; }}

  .pill {{
    display: inline-block; padding: 1px 9px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
    background: #1a2438; color: var(--muted);
  }}
  .pill.buy {{ background: rgba(34,197,94,.15); color: var(--buy); }}
  .pill.sell {{ background: rgba(239,68,68,.15); color: var(--sell); }}

  details.sym {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 10px 14px; margin-bottom: 12px;
  }}
  details.sym summary {{ cursor: pointer; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .charts {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 12px 0 4px; }}
  .chart-label {{ font-size: 0.75rem; color: var(--muted); margin-bottom: 2px; }}
  .spark {{ background: #0d1526; border-radius: 6px; }}

  .news {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 12px 20px; }}
  .news ul {{ margin: 0; padding-left: 18px; }}
  .news li {{ margin: 7px 0; }}

  @media (max-width: 640px) {{
    .charts {{ gap: 12px; }}
    body {{ padding: 16px 10px 32px; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <h1>📈 Market Intelligence &amp; Signals</h1>
  <div class="muted">Last run: {esc(generated[:19].replace('T', ' '))} UTC · Auto-updated by GitHub Actions</div>

  <h2>🤖 Latest Brief</h2>
  <div class="brief">
    {f'<div class="muted" style="margin-bottom:8px">Generated {brief_ts} UTC</div>' if brief_ts else ''}
    {brief_html}
  </div>

  <h2>🎯 Latest Signals</h2>
  <div class="cards">{''.join(cards)}</div>
  <table>
    <thead><tr><th>Symbol</th><th>Signal</th><th>Close</th><th>RSI</th><th>SMA 20</th><th>SMA 50</th><th>Rationale</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2>📊 Signal History</h2>
  {''.join(sym_sections)}

  <h2>📰 Recent News</h2>
  <div class="news"><ul>{''.join(news_items)}</ul></div>

  <div class="foot">Informational only — not financial advice. Generated from data/signals.sqlite by tools/render_html.py.</div>
</div>
</body>
</html>
"""


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    signals, brief, news = load(conn)
    conn.close()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_html(signals, brief, news), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
