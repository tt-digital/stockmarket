"""
scan.py — daily stock scanner using Finnhub free tier

Commands:
  python scan.py earnings    Stocks reporting today ±1 day + post-move
  python scan.py movers      Top gainers & losers from watchlist
  python scan.py conviction  Analyst buy-rating × 52W discount (top 10)
  python scan.py all         Run all three

ISIN + WKN are hardcoded for all 63 watchlist stocks; earnings symbols
outside the watchlist show '—'.
"""

import os
import time
from datetime import date, timedelta

import click
import requests
from sty import fg
from tabulate import tabulate


# ── Watchlist (~63 stocks: S&P 100 core + semis, intl ADRs, pharma, financials)
WATCHLIST = [
    # S&P 100 core
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK.B",
    "JPM",  "V",    "UNH",  "XOM",   "LLY",  "JNJ",  "WMT",  "MA",
    "PG",   "HD",   "ORCL", "COST",  "MRK",  "ABBV", "CVX",  "BAC",
    "KO",   "PEP",  "CSCO", "TMO",   "ACN",  "MCD",  "ABT",  "NKE",
    "DHR",  "TXN",  "NEE",  "PM",    "AMGN", "LIN",  "RTX",  "QCOM",
    "HON",  "IBM",  "GE",   "CAT",   "SBUX", "BA",   "GS",   "MS",
    "NFLX", "AMD",
    # Semiconductors / hardware
    "AMAT", "MRVL", "ARM",
    # International (ADR / cross-listed)
    "ASML", "TSM",  "NVO",  "SAP",
    # Pharma / biotech
    "REGN", "ISRG", "VRTX",
    # Financials / data
    "BLK",  "SPGI", "MCO",
]

FH_BASE  = "https://finnhub.io/api/v1"
THROTTLE = 0.5   # seconds between Finnhub calls

# ── ISIN / WKN static table (63 watchlist stocks) ─────────────────────────────
ISIN_WKN = {
    "AAPL":  ("US0378331005", "865985"),
    "MSFT":  ("US5949181045", "870747"),
    "NVDA":  ("US67066G1040", "918422"),
    "GOOGL": ("US02079K3059", "A14Y6F"),
    "AMZN":  ("US0231351067", "906866"),
    "META":  ("US30303M1027", "A1JWVX"),
    "TSLA":  ("US88160R1014", "A1CX3T"),
    "BRK.B": ("US0846701086", "900944"),
    "JPM":   ("US46625H1005", "850628"),
    "V":     ("US92826C8394", "A0NC7B"),
    "UNH":   ("US91324P1021", "869561"),
    "XOM":   ("US30231G1022", "852549"),
    "LLY":   ("US5324571083", "858560"),
    "JNJ":   ("US4781601046", "853260"),
    "WMT":   ("US9311421039", "860853"),
    "MA":    ("US57636Q1040", "A0F602"),
    "PG":    ("US7427181091", "852062"),
    "HD":    ("US4370761029", "866953"),
    "ORCL":  ("US68389X1054", "871460"),
    "COST":  ("US22160K1051", "888351"),
    "MRK":   ("US58933Y1055", "A0YD8Q"),
    "ABBV":  ("US00287Y1091", "A1J84E"),
    "CVX":   ("US1667641005", "852552"),
    "BAC":   ("US0605051046", "858388"),
    "KO":    ("US1912161007", "850663"),
    "PEP":   ("US7134481081", "851995"),
    "CSCO":  ("US17275R1023", "878841"),
    "TMO":   ("US8835561023", "A14Y74"),
    "ACN":   ("IE00B7BKVD75", "A0YZ78"),
    "MCD":   ("US5801351017", "856958"),
    "ABT":   ("US0028241000", "850103"),
    "NKE":   ("US6541061031", "866993"),
    "DHR":   ("US2358511028", "866197"),
    "TXN":   ("US8825081040", "852654"),
    "NEE":   ("US65339F1012", "A0NHL8"),
    "PM":    ("US7181721090", "A0NDBJ"),
    "AMGN":  ("US0311621009", "867900"),
    "LIN":   ("IE00BZ12WP82", "A2DKLU"),
    "RTX":   ("US75513E1010", "A2PGM6"),
    "QCOM":  ("US7475251036", "883121"),
    "HON":   ("US4385161066", "870888"),
    "IBM":   ("US4592001014", "851399"),
    "GE":    ("US36266G1013", "A3DLAP"),
    "CAT":   ("US1491231015", "858437"),
    "SBUX":  ("US8552441094", "884437"),
    "BA":    ("US0970231058", "850471"),
    "GS":    ("US38141G1040", "920332"),
    "MS":    ("US6174464486", "885836"),
    "NFLX":  ("US64110L1061", "552484"),
    "AMD":   ("US0079031078", "863186"),
    # Semiconductors / hardware
    "AMAT":  ("US0382221051", "865177"),
    "MRVL":  ("US57344Q1058", "A2QM30"),
    "ARM":   ("GB00BN090394", "A3EX3R"),
    # International (ADR / cross-listed)
    "ASML":  ("NL0010273215", "A1J4U4"),
    "TSM":   ("US8740391003", "909800"),
    "NVO":   ("DK0062498333", "A3EU6F"),   # Novo Nordisk B share
    "SAP":   ("DE0007164600", "716460"),
    # Pharma / biotech
    "REGN":  ("US75886F1075", "881535"),
    "ISRG":  ("US46120E6023", "203810"),
    "VRTX":  ("US92532F1003", "882807"),
    # Financials / data
    "BLK":   ("US09247X1019", "928193"),
    "SPGI":  ("US78409V1044", "880585"),
    "MCO":   ("US6153031088", "915246"),
}


# ── Finnhub helper ────────────────────────────────────────────────────────────
def get_key():
    key = os.environ.get("FINNHUB_KEY", "").strip()
    if not key:
        raise click.ClickException(
            "Finnhub API key not set.\n"
            "  1. Get a free key at https://finnhub.io/register\n"
            "  2. export FINNHUB_KEY=your_key"
        )
    return key


def fh_get(endpoint, params, key):
    time.sleep(THROTTLE)
    r = requests.get(
        f"{FH_BASE}/{endpoint}",
        params={**params, "token": key},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


# ── ISIN / WKN lookup ─────────────────────────────────────────────────────────
def lookup_ids(symbols):
    """Returns {SYM: (isin, wkn)} from the static table."""
    return {sym: ISIN_WKN.get(sym, ("—", "—")) for sym in symbols}


# ── Output helpers ────────────────────────────────────────────────────────────
def pct_color(val):
    if val is None:
        return "—"
    s = f"{val:+.2f}%"
    return (fg(220, 40, 40) if val < 0 else fg(40, 180, 80)) + s + fg.rs


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

    data  = fh_get("calendar/earnings", {"from": frm, "to": to}, key)
    items = data.get("earningsCalendar", [])
    if not items:
        print_table([], [], "earnings catalyst  (±1 day)")
        return

    # Fetch quotes for all entries
    rows_raw = []
    for item in items:
        sym     = item.get("symbol", "")
        eps_est = item.get("epsEstimate")
        eps_act = item.get("epsActual")
        dt      = item.get("date", "")
        try:
            q     = fh_get("quote", {"symbol": sym}, key)
            price = q.get("c")
            pct   = q.get("dp")
        except requests.RequestException:
            price, pct = None, None
        rows_raw.append((sym, dt, price, pct, eps_est, eps_act))

    priced = [r[0] for r in rows_raw if r[2]]
    ids = lookup_ids(priced)

    rows = []
    for sym, dt, price, pct, eps_est, eps_act in rows_raw:
        isin, wkn = ids.get(sym, ("—", "—"))
        surprise  = ""
        if eps_est is not None and eps_act is not None:
            diff     = eps_act - eps_est
            surprise = (fg(40, 180, 80) if diff >= 0 else fg(220, 40, 40)) \
                     + f"{diff:+.2f}" + fg.rs
        rows.append([
            sym_fmt(sym), isin, wkn, dt,
            f"${price:.2f}" if price else "—",
            pct_color(pct),
            f"{eps_est:.2f}" if eps_est is not None else "—",
            f"{eps_act:.2f}" if eps_act is not None else "—",
            surprise,
        ])

    headers = ["SYM", "ISIN", "WKN", "DATE", "PRICE", "%", "EPS EST", "EPS ACT", "SURPRISE"]
    print_table(headers, rows, "earnings catalyst  (±1 day)")


# ── B: Momentum Movers ────────────────────────────────────────────────────────
def run_movers(key):
    ids = lookup_ids(WATCHLIST)

    results = []
    click.echo(f"\n{fg(200,200,200)}// movers — fetching {len(WATCHLIST)} quotes…{fg.rs}")
    for sym in WATCHLIST:
        try:
            q      = fh_get("quote", {"symbol": sym}, key)
            c, dp  = q.get("c"), q.get("dp")
            h, l   = q.get("h"), q.get("l")
            if not c:
                continue
            metric = fh_get("stock/metric", {"symbol": sym, "metric": "all"}, key)
            m      = metric.get("metric", {})
            w52h, w52l = m.get("52WeekHigh"), m.get("52WeekLow")
            pos52  = ((c - w52l) / (w52h - w52l) * 100) \
                     if (w52h and w52l and w52h != w52l) else None
            results.append((sym, c, dp, h, l, pos52))
        except requests.RequestException:
            continue

    results.sort(key=lambda x: x[2] or 0, reverse=True)

    def make_rows(items):
        return [[
            sym_fmt(sym),
            *ids.get(sym, ("—", "—")),
            f"{price:.2f}",
            f"{h:.2f}" if h else "—",
            f"{l:.2f}" if l else "—",
            pct_color(dp),
            f"{pos52:.0f}%" if pos52 is not None else "—",
        ] for sym, price, dp, h, l, pos52 in items]

    headers = ["SYM", "ISIN", "WKN", "PRICE", "HIGH", "LOW", "%", "52W POS"]
    print_table(headers, make_rows(results[:5]),       "top gainers")
    print_table(headers, make_rows(results[-5:][::-1]), "top losers")


# ── C: Analyst Conviction ─────────────────────────────────────────────────────
def run_conviction(key):
    ids = lookup_ids(WATCHLIST)

    results = []
    click.echo(f"\n{fg(200,200,200)}// conviction — fetching recommendations…{fg.rs}")
    for sym in WATCHLIST:
        try:
            recs = fh_get("stock/recommendation", {"symbol": sym}, key)
            if not recs:
                continue
            lat        = recs[0]
            strong_buy = lat.get("strongBuy", 0)
            buy        = lat.get("buy", 0)
            hold       = lat.get("hold", 0)
            sell       = lat.get("sell", 0) + lat.get("strongSell", 0)
            total      = strong_buy + buy + hold + sell
            if not total:
                continue
            buy_pct = (strong_buy + buy) / total * 100

            q     = fh_get("quote", {"symbol": sym}, key)
            price = q.get("c")
            if not price:
                continue

            metric = fh_get("stock/metric", {"symbol": sym, "metric": "all"}, key)
            w52h   = metric.get("metric", {}).get("52WeekHigh")
            disc   = ((w52h - price) / w52h * 100) if w52h else None
            score  = buy_pct * (disc or 0) / 100
            results.append((sym, price, buy_pct,
                            hold / total * 100, sell / total * 100, disc, score))
        except requests.RequestException:
            continue

    results.sort(key=lambda x: x[6], reverse=True)

    rows = []
    for sym, price, bp, hp, sp, disc, score in results[:10]:
        isin, wkn = ids.get(sym, ("—", "—"))
        rows.append([
            sym_fmt(sym), isin, wkn,
            f"{price:.2f}",
            fg(40, 180, 80)  + f"{bp:.0f}%" + fg.rs,
            f"{hp:.0f}%",
            fg(220, 40, 40)  + f"{sp:.0f}%" + fg.rs,
            f"{disc:.1f}%" if disc is not None else "—",
            f"{score:.1f}",
        ])

    headers = ["SYM", "ISIN", "WKN", "PRICE", "BUY%", "HOLD%", "SELL%", "↓52W", "SCORE"]
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
