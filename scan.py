"""
scan.py — daily stock scanner using Finnhub free tier

Commands:
  python scan.py earnings    Stocks reporting today ±1 day + post-move
  python scan.py movers      Top gainers & losers from watchlist
  python scan.py conviction  Analyst buy-rating × discount from 52W high
  python scan.py all         Run all three
"""

import os
import time
from datetime import date, timedelta

import click
import requests
from sty import fg
from tabulate import tabulate


# ── Watchlist (~50 liquid S&P 100 names) ─────────────────────────────────────
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK.B",
    "JPM",  "V",    "UNH",  "XOM",   "LLY",  "JNJ",  "WMT",  "MA",
    "PG",   "HD",   "ORCL", "COST",  "MRK",  "ABBV", "CVX",  "BAC",
    "KO",   "PEP",  "CSCO", "TMO",   "ACN",  "MCD",  "ABT",  "NKE",
    "DHR",  "TXN",  "NEE",  "PM",    "AMGN", "LIN",  "RTX",  "QCOM",
    "HON",  "IBM",  "GE",   "CAT",   "SBUX", "BA",   "GS",   "MS",
    "NFLX", "AMD",
]

BASE = "https://finnhub.io/api/v1"
THROTTLE = 0.5   # seconds between calls — stays well under 60/min


# ── Shared helpers ────────────────────────────────────────────────────────────
def get_key():
    key = os.environ.get("FINNHUB_KEY", "").strip()
    if not key:
        raise click.ClickException(
            "Finnhub API key not set.\n"
            "  1. Get a free key at https://finnhub.io/register\n"
            "  2. export FINNHUB_KEY=your_key"
        )
    return key


def get(endpoint, params, key):
    """Single API call with throttle."""
    time.sleep(THROTTLE)
    resp = requests.get(
        f"{BASE}/{endpoint}",
        params={**params, "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def pct_color(val):
    if val is None:
        return "—"
    s = f"{val:+.2f}%"
    if val < 0:
        return fg(220, 40, 40) + s + fg.rs
    return fg(40, 180, 80) + s + fg.rs


def sym_fmt(s):
    return fg(255, 140, 20) + s.upper() + fg.rs


def print_table(headers, rows, title):
    click.echo(f"\n{fg(200,200,200)}// {title}{fg.rs}")
    if not rows:
        click.echo("  no results\n")
        return
    click.echo(tabulate([headers] + rows, headers="firstrow", tablefmt="github"))
    click.echo()


# ── A: Earnings Catalyst ──────────────────────────────────────────────────────
def run_earnings(key):
    today = date.today()
    frm   = (today - timedelta(days=1)).isoformat()
    to    = (today + timedelta(days=1)).isoformat()

    data = get("calendar/earnings", {"from": frm, "to": to}, key)
    items = data.get("earningsCalendar", [])

    if not items:
        print_table([], [], "earnings catalyst  (±1 day)")
        return

    rows = []
    for item in items:
        sym     = item.get("symbol", "")
        eps_est = item.get("epsEstimate")
        eps_act = item.get("epsActual")
        rev_est = item.get("revenueEstimate")
        dt      = item.get("date", "")

        try:
            q       = get("quote", {"symbol": sym}, key)
            price   = q.get("c")
            pct     = q.get("dp")
        except requests.RequestException:
            price, pct = None, None

        surprise = ""
        if eps_est and eps_act:
            diff = eps_act - eps_est
            surprise = (fg(40, 180, 80) if diff >= 0 else fg(220, 40, 40)) \
                     + f"{diff:+.2f}" + fg.rs

        rows.append([
            sym_fmt(sym),
            dt,
            f"${price:.2f}" if price else "—",
            pct_color(pct),
            f"{eps_est:.2f}" if eps_est is not None else "—",
            f"{eps_act:.2f}" if eps_act is not None else "—",
            surprise,
        ])

    headers = ["SYM", "DATE", "PRICE", "%", "EPS EST", "EPS ACT", "SURPRISE"]
    print_table(headers, rows, "earnings catalyst  (±1 day)")


# ── B: Momentum Movers ────────────────────────────────────────────────────────
def run_movers(key):
    results = []
    click.echo(f"\n{fg(200,200,200)}// movers — fetching {len(WATCHLIST)} quotes…{fg.rs}")

    for sym in WATCHLIST:
        try:
            q = get("quote", {"symbol": sym}, key)
            c, dp, h, l, pc = q.get("c"), q.get("dp"), q.get("h"), q.get("l"), q.get("pc")
            if not c:
                continue
            # 52W position: where today's price sits between low and high
            metric = get("stock/metric", {"symbol": sym, "metric": "all"}, key)
            m      = metric.get("metric", {})
            w52h   = m.get("52WeekHigh")
            w52l   = m.get("52WeekLow")
            if w52h and w52l and w52h != w52l:
                pos52 = (c - w52l) / (w52h - w52l) * 100
            else:
                pos52 = None
            results.append((sym, c, dp, h, l, pos52))
        except requests.RequestException:
            continue

    results.sort(key=lambda x: x[2] or 0, reverse=True)
    gainers = results[:5]
    losers  = results[-5:][::-1]

    def make_rows(items):
        rows = []
        for sym, price, dp, h, l, pos52 in items:
            rows.append([
                sym_fmt(sym),
                f"{price:.2f}",
                f"{h:.2f}" if h else "—",
                f"{l:.2f}" if l else "—",
                pct_color(dp),
                f"{pos52:.0f}%" if pos52 is not None else "—",
            ])
        return rows

    headers = ["SYM", "PRICE", "HIGH", "LOW", "%", "52W POS"]
    print_table(headers, make_rows(gainers), "top gainers")
    print_table(headers, make_rows(losers),  "top losers")


# ── C: Analyst Conviction ─────────────────────────────────────────────────────
def run_conviction(key):
    results = []
    click.echo(f"\n{fg(200,200,200)}// conviction — fetching recommendations…{fg.rs}")

    for sym in WATCHLIST:
        try:
            recs = get("stock/recommendation", {"symbol": sym}, key)
            if not recs:
                continue
            latest  = recs[0]   # most recent period
            strong_buy = latest.get("strongBuy", 0)
            buy        = latest.get("buy", 0)
            hold       = latest.get("hold", 0)
            sell       = latest.get("sell", 0) + latest.get("strongSell", 0)
            total      = strong_buy + buy + hold + sell
            if total == 0:
                continue
            buy_pct = (strong_buy + buy) / total * 100

            q      = get("quote", {"symbol": sym}, key)
            price  = q.get("c")
            if not price:
                continue

            metric = get("stock/metric", {"symbol": sym, "metric": "all"}, key)
            m      = metric.get("metric", {})
            w52h   = m.get("52WeekHigh")
            disc   = ((w52h - price) / w52h * 100) if w52h else None

            # Score: analyst conviction × discount from 52W high
            score = buy_pct * (disc or 0) / 100
            results.append((sym, price, buy_pct, hold / total * 100,
                            sell / total * 100, disc, score))
        except requests.RequestException:
            continue

    results.sort(key=lambda x: x[6], reverse=True)
    top = results[:10]

    rows = []
    for sym, price, bp, hp, sp, disc, score in top:
        rows.append([
            sym_fmt(sym),
            f"{price:.2f}",
            fg(40, 180, 80) + f"{bp:.0f}%" + fg.rs,
            f"{hp:.0f}%",
            fg(220, 40, 40) + f"{sp:.0f}%" + fg.rs,
            f"{disc:.1f}%" if disc is not None else "—",
            f"{score:.1f}",
        ])

    headers = ["SYM", "PRICE", "BUY%", "HOLD%", "SELL%", "↓52W", "SCORE"]
    print_table(headers, rows, "analyst conviction  (top 10)")


# ── CLI ───────────────────────────────────────────────────────────────────────
@click.command(help=(
    "Scan for interesting stocks using Finnhub free tier.\n\n"
    "COMMAND:\n\n"
    "  earnings    Stocks reporting earnings today ±1 day\n\n"
    "  movers      Top 5 gainers and losers from watchlist\n\n"
    "  conviction  Analyst buy-rating × 52W discount (top 10)\n\n"
    "  all         Run all three\n\n"
    "Requires:  export FINNHUB_KEY=your_key"
))
@click.argument("command", type=click.Choice(["earnings", "movers", "conviction", "all"]))
def scan(command):
    key = get_key()
    if command in ("earnings", "all"):
        run_earnings(key)
    if command in ("movers", "all"):
        run_movers(key)
    if command in ("conviction", "all"):
        run_conviction(key)


if __name__ == "__main__":
    scan()
