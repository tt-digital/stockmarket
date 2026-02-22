import click
import yfinance as yf
from sty import fg
from tabulate import tabulate


@click.command(help="Display live quotes for one or more stock ticker symbols.")
@click.argument('symbols', nargs=-1, metavar='SYMBOL...')
def ticker(symbols):
    if not symbols:
        click.echo("Provide at least one symbol. Example: ticker.py AAPL GOOG EURUSD=X")
        return

    headers = ['SYM', 'PRICE', 'CCY', 'CHG', '%', 'STATE', 'TYPE']
    rows = []

    for sym in symbols:
        try:
            t  = yf.Ticker(sym)
            fi = t.fast_info

            price  = fi.last_price
            prev   = fi.previous_close
            change = round(price - prev, 4) if price and prev else None
            pct    = round((change / prev) * 100, 4) if change and prev else None

            currency     = fi.currency or '—'
            info         = t.info
            market_state = info.get('marketState', '—')
            quote_type   = info.get('quoteType', '—')

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

            rows.append([sym_str, price_str, currency, chg_str, pct_str, market_state, quote_type])

        except Exception as e:
            error_label = fg(180, 180, 180) + sym.upper() + fg.rs
            rows.append([error_label, 'N/A', '—', '—', '—', '—', f"error: {e}"])

    click.echo(tabulate([headers] + rows, headers='firstrow', tablefmt='github'))


if __name__ == '__main__':
    ticker()
