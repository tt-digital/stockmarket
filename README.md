# ticker.py

CLI tool for live stock quotes. Displays current price, daily high/low, change, and percent change for one or more symbols.

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

## Usage

```bash
python3 ticker.py SYMBOL...
```

Pass one or more ticker symbols as arguments.

```bash
python3 ticker.py AAPL GOOG MSFT TSLA
```

## Output

```
| SYM  | PRICE  | HIGH   | LOW    | CHG    | %       |
|------|--------|--------|--------|--------|---------|
| AAPL | 189.30 | 190.45 | 188.12 | ▲ +1.20 | +0.64% |
| GOOG | 175.82 | 176.90 | 174.33 | ▼ -0.55 | -0.31% |
```

Gains are shown in green, losses in red, with ▲/▼ indicators.
