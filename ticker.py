import os
import click
import requests
from sty import fg
from tabulate import tabulate


def get_api_key():
    key = os.environ.get('FINNHUB_KEY', '').strip()
    if not key:
        raise click.ClickException(
            "Finnhub API key not set.\n"
            "  1. Get a free key at https://finnhub.io/register\n"
            "  2. export FINNHUB_KEY=your_key"
        )
    return key


def fetch_quote(sym, key):
    resp = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": sym, "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@click.command(help=(
    "Display live quotes for one or more stock ticker symbols.\n\n"
    "Requires a free Finnhub API key: https://finnhub.io/register\n\n"
    "Set it with:  export FINNHUB_KEY=your_key\n\n"
    "Examples:  ticker.py AAPL GOOG MSFT TSLA\n"
    "           ticker.py OANDA:EUR_USD  (forex)"
))
@click.argument('symbols', nargs=-1, metavar='SYMBOL...')
def ticker(symbols):
    if not symbols:
        click.echo("Provide at least one symbol, e.g.: ticker.py AAPL GOOG MSFT")
        return

    key = get_api_key()

    headers = ['SYM', 'PRICE', 'HIGH', 'LOW', 'CHG', '%']
    rows = []

    for sym in symbols:
        try:
            q = fetch_quote(sym, key)
            price  = q.get('c')
            change = q.get('d')
            pct    = q.get('dp')
            high   = q.get('h')
            low    = q.get('l')

            if not price:
                rows.append([sym.upper(), 'N/A', '—', '—', '—', '—'])
                continue

            sym_str   = fg(255, 140, 20) + sym.upper() + fg.rs
            price_str = f"{price:.2f}"
            high_str  = f"{high:.2f}" if high else '—'
            low_str   = f"{low:.2f}" if low else '—'

            if change is not None and change < 0:
                chg_str = fg(220, 40, 40) + f"▼ {change:+.2f}" + fg.rs
                pct_str = fg(220, 40, 40) + f"{pct:+.2f}%" + fg.rs
            elif change is not None:
                chg_str = fg(40, 180, 80) + f"▲ {change:+.2f}" + fg.rs
                pct_str = fg(40, 180, 80) + f"{pct:+.2f}%" + fg.rs
            else:
                chg_str = '—'
                pct_str = '—'

            rows.append([sym_str, price_str, high_str, low_str, chg_str, pct_str])

        except requests.RequestException as e:
            rows.append([sym.upper(), f"error: {e}", '—', '—', '—', '—'])

    click.echo(tabulate([headers] + rows, headers='firstrow', tablefmt='github'))


if __name__ == '__main__':
    ticker()
