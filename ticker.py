import click
import requests
from sty import fg
from tabulate import tabulate


def fetch_quotes(symbols):
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    params = {"symbols": ",".join(symbols)}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return {r["symbol"]: r for r in resp.json()["quoteResponse"]["result"]}


@click.command(help="Display live quotes for one or more stock ticker symbols.")
@click.argument('symbols', nargs=-1, metavar='SYMBOL...')
def ticker(symbols):
    if not symbols:
        click.echo("Provide at least one symbol. Example: ticker.py AAPL GOOG EURUSD=X")
        return

    try:
        quotes = fetch_quotes(symbols)
    except requests.RequestException as e:
        click.echo(f"Network error: {e}", err=True)
        return

    headers = ['SYM', 'PRICE', 'CCY', 'CHG', '%', 'STATE', 'TYPE']
    rows = []

    for sym in symbols:
        q = quotes.get(sym.upper()) or quotes.get(sym)
        if q is None:
            rows.append([sym.upper(), 'N/A', '—', '—', '—', '—', 'symbol not found'])
            continue

        price  = q.get('regularMarketPrice')
        change = q.get('regularMarketChange')
        pct    = q.get('regularMarketChangePercent')

        sym_str   = fg(255, 140, 20) + sym.upper() + fg.rs
        price_str = f"{price:.2f}" if price is not None else '—'

        if change is not None and change < 0:
            chg_str = fg(220, 40, 40) + f"▼ {change:+.2f}" + fg.rs
            pct_str = fg(220, 40, 40) + f"{pct:+.2f}%" + fg.rs
        elif change is not None:
            chg_str = fg(40, 180, 80) + f"▲ {change:+.2f}" + fg.rs
            pct_str = fg(40, 180, 80) + f"{pct:+.2f}%" + fg.rs
        else:
            chg_str = '—'
            pct_str = '—'

        rows.append([
            sym_str,
            price_str,
            q.get('currency', '—'),
            chg_str,
            pct_str,
            q.get('marketState', '—'),
            q.get('quoteType', '—'),
        ])

    click.echo(tabulate([headers] + rows, headers='firstrow', tablefmt='github'))


if __name__ == '__main__':
    ticker()
