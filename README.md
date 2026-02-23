# stockmarket

Two Python CLI tools for live quotes and daily stock analysis, powered by the [Finnhub](https://finnhub.io) free API.

## Setup

**1. Get a free API key**

Register at https://finnhub.io/register — no credit card required.

**2. Set the key as an environment variable**

```bash
export FINNHUB_KEY=your_key_here
```

Add it to your `~/.zshrc` or `~/.bashrc` to make it permanent.

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## ticker.py — live quotes

```bash
python3 ticker.py SYMBOL...
```

```bash
python3 ticker.py AAPL GOOG MSFT TSLA
```

```
| SYM  | PRICE  | HIGH   | LOW    | CHG      | %       |
|------|--------|--------|--------|----------|---------|
| AAPL | 189.30 | 190.45 | 188.12 | ▲ +1.20  | +0.64%  |
| GOOG | 175.82 | 176.90 | 174.33 | ▼ -0.55  | -0.31%  |
```

---

## scan.py — daily stock scanner

Three strategies for finding interesting stocks, all within the Finnhub free tier (~60 calls/min).

```bash
python3 scan.py COMMAND
```

| Command | What it does | API calls |
|---|---|---|
| `earnings` | Stocks reporting earnings today ±1 day — shows EPS estimate vs actual and post-move | ~5–20 |
| `movers` | Top 5 gainers and top 5 losers from a 50-stock watchlist, with 52-week position | ~100 |
| `conviction` | Ranks watchlist by analyst buy-rating × discount from 52W high — surfaces stocks analysts like that are off their highs | ~150 |
| `all` | Runs all three in sequence | ~275 |

### Examples

```bash
python3 scan.py earnings
python3 scan.py movers
python3 scan.py conviction
python3 scan.py all
```

### conviction output

```
// analyst conviction  (top 10)
| SYM  | PRICE  | BUY% | HOLD% | SELL% | ↓52W   | SCORE |
|------|--------|------|-------|-------|--------|-------|
| NVDA | 124.50 | 91%  | 7%    | 2%    | 18.3%  | 16.7  |
| META | 558.20 | 88%  | 10%   | 2%    | 12.1%  | 10.7  |
```

`SCORE = buy% × discount_from_52W_high` — highest score means strong analyst consensus on a stock that has pulled back.

### Watchlist

The default watchlist is 50 liquid S&P 100 names (AAPL, MSFT, NVDA, …). Edit `WATCHLIST` in `scan.py` to customise.
