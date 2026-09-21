# Tax optimization calculator (Kazakhstan, broker investments)

A CLI calculator that takes an individual investor's trade and dividend
history from a broker, computes Kazakhstan individual income tax (ИПН) on
realized gains and dividends, and suggests legal tax-optimization moves
(tax-loss harvesting, KASE listing-exemption reminders, cost-basis method
comparison).

**Not certified tax advice.** See `docs/TAX_RULES_KZ.md` for the exact rules
and assumptions this tool encodes, and confirm results with your broker's tax
desk or a licensed tax consultant before filing anything.

## Quick start (CLI)

```bash
python3 -m tax_optimizer report \
  --trades data/sample_trades.csv \
  --dividends data/sample_dividends.csv \
  --prices data/sample_prices.csv
```

Only `--trades` is required; `--dividends` and `--prices` are optional
(`--prices` unlocks the optimization suggestions section, since harvesting
needs current market values).

## Web UI

```bash
pip install -r requirements.txt
python3 -m webapp.app
```

Open http://127.0.0.1:5000/. You can either fill in trades/dividends/prices
row by row (with add/remove-row buttons) or upload the same CSV files the CLI
uses — a file, if selected, takes priority over that section's manual rows.
The web app calls the exact same `tax_optimizer` package as the CLI; no
calculation logic is duplicated in `webapp/`.

## Input format

See the docstring in `tax_optimizer/io_csv.py` for the exact CSV columns.
In short:

- `trades.csv`: one row per BUY/SELL, with quantity, price, currency, an
  optional commission, the KZT exchange rate on the trade date
  (`fx_rate_to_kzt`), and whether the instrument was on the KASE official
  list at that date (`kase_official_list`).
- `dividends.csv`: one row per dividend payment, with amount, currency,
  exchange rate, any foreign tax withheld, KASE-listing flag, and holding
  period in years.
- `prices.csv`: current price **in KZT** per instrument, used only for the
  optimizer's tax-loss-harvesting suggestions.

## What it computes

1. **FIFO cost-basis matching** (`tax_optimizer/fifo_engine.py`) turns your
   trade history into realized gains/losses and remaining open positions.
2. **Tax calculation** (`tax_optimizer/kz_tax_rules.py`) applies the flat 10%
   ИПН rate, the KASE-listing capital-gains exemption, the 3-year/KASE
   dividend exemption, and foreign tax credit for dividends.
3. **Optimization suggestions** (`tax_optimizer/optimizer.py`):
   - which open positions to sell to harvest a loss against this year's
     taxable gain (since losses cannot be carried forward or offset other
     income types for individuals);
   - reminders to verify KASE listing status before selling a position that
     isn't yet flagged as exempt;
   - a side-by-side comparison of the tax impact of FIFO vs LIFO vs HIFO cost
     basis, useful context when discussing lot selection with your broker.

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

No third-party dependencies are required -- everything uses the Python
standard library (`csv`, `dataclasses`, `decimal`, `argparse`).
