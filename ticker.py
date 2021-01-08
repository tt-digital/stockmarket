import urllib.request
import click
import json
import numpy as np
from sty import fg, bg, ef, rs
from tabulate import tabulate

@click.command()
@click.argument('symbols', nargs=-1)

def ticker(symbols):
    urlData = "https://query2.finance.yahoo.com/v7/finance/quote?symbols="+','.join(symbols)
    webUrl = urllib.request.urlopen(urlData)
    data = webUrl.read()
    tickerData = json.loads(data)
    result = ()
    b = np.array([['SYM', 'PR', 'CCY', 'CHG', '%', 'STATE', 'TYPE']])	
    for i in enumerate(symbols):
        stringSymbol = fg(255, 100, 10) + i[1] + fg.rs        
        stringregularMarketPrice = (tickerData["quoteResponse"]["result"][i[0]]["regularMarketPrice"])
        stringregularMarketCurrency = (tickerData["quoteResponse"]["result"][i[0]]["currency"])
        stringmarketState = (tickerData["quoteResponse"]["result"][i[0]]["marketState"])
        stringquoteType = (tickerData["quoteResponse"]["result"][i[0]]["quoteType"])
        if tickerData["quoteResponse"]["result"][i[0]]["regularMarketChange"] < 0:
            stringregularMarketChange = fg(255, 10, 10) + str(tickerData["quoteResponse"]["result"][i[0]]["regularMarketChange"]) + fg.rs
            stringregularMarketChangePercent = fg(255, 10, 10) + str(tickerData["quoteResponse"]["result"][i[0]]["regularMarketChangePercent"]) + '' + fg.rs
        else:
            stringregularMarketChange = fg.green + str(tickerData["quoteResponse"]["result"][i[0]]["regularMarketChange"]) + fg.rs
            stringregularMarketChangePercent = fg.green + str(tickerData["quoteResponse"]["result"][i[0]]["regularMarketChangePercent"]) + '' + fg.rs
        b = np.append(b, [[stringSymbol, stringregularMarketPrice, stringregularMarketCurrency, stringregularMarketChange, stringregularMarketChangePercent, stringmarketState, stringquoteType]], axis = 0)
    click.echo(tabulate(b, headers='firstrow', tablefmt='github',  floatfmt=".2f"))

    return result

if __name__ == '__main__':
    ticker()
