# Tax optimization calculators (Kazakhstan, broker services)

Two independent calculators for tax-aware use of a broker in Kazakhstan:

1. **`tax_optimizer/`** — an individual investor's ИПН (personal income tax)
   on capital gains and dividends from trading securities through a broker.
2. **`liquidity_optimizer/`** — a legal entity's after-tax (КПН — corporate
   income tax) return on placing short-term cash through a broker across
   REPO, National Bank notes/government securities, and short corporate
   bonds, given trader-supplied yield assumptions.

Each has its own CLI and its own page in the shared Flask web UI (see
`webapp/`) — pick whichever matches your situation.

**Not certified tax or investment advice.** See `docs/TAX_RULES_KZ.md` for
the ИПН assumptions, and confirm any result with your broker's desk or a
licensed tax consultant before acting on it.

## Investor tax calculator — quick start (CLI)

```bash
python3 -m tax_optimizer report \
  --trades data/sample_trades.csv \
  --dividends data/sample_dividends.csv \
  --prices data/sample_prices.csv
```

Only `--trades` is required; `--dividends` and `--prices` are optional
(`--prices` unlocks the optimization suggestions section, since harvesting
needs current market values).

## Liquidity portfolio calculator — quick start (CLI)

```bash
python3 -m liquidity_optimizer report \
  --amount 100000000 --term-days 14 --kpn-rate 20 --repo 70 --notes 30
```

Defaults for trader parameters (base yields and term coefficients) live in
`liquidity_optimizer/models.py::DEFAULT_TRADER_PARAMS`; the web UI lets a
trader override them per calculation instead of editing code.

## Web UI

```bash
pip install -r requirements.txt
python3 -m webapp.app
```

Open http://127.0.0.1:5000/ for the investor ИПН calculator, or
http://127.0.0.1:5000/liquidity for the liquidity portfolio calculator (a nav
link at the top of each page switches between them).

On the investor calculator you can either fill in trades/dividends/prices row
by row (with add/remove-row buttons) or upload the same CSV files the CLI
uses — a file, if selected, takes priority over that section's manual rows.
The web app calls the exact same `tax_optimizer` / `liquidity_optimizer`
packages as their CLIs; no calculation logic is duplicated in `webapp/`.

## Input format (investor ИПН calculator)

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

## What the investor calculator computes

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

## What the liquidity calculator computes (`liquidity_optimizer/calculator.py`)

For each instrument: `amount = total × share%`, `effective annual rate =
base yield% × term coefficient`, `net income = amount × (effective rate /
100) × (term_days / 365) × (1 − KPN% / 100)`. The term coefficient is looked
up the same way Excel's `LOOKUP` does it: the coefficient at the largest
table boundary that is ≤ the requested term. Totals give the after-tax net
income, final amount, and annualized equivalent yield.

Optionally pass a bank deposit rate (`--deposit-rate` on the CLI, or the
"Ставка депозита банка" field in the web UI) to compare against: the same
lump sum and term, taxed at the same КПН rate, gives a baseline net income,
final amount and annualized yield, plus the broker portfolio's advantage
(or disadvantage) over it in both KZT and annualized percentage points.
This is a simplifying assumption -- some deposit or government-instrument
interest may carry a different tax treatment, so confirm with your bank/tax
advisor for your specific instrument.

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

The calculators themselves use only the Python standard library (`csv`,
`dataclasses`, `decimal`, `argparse`); `flask` (see `requirements.txt`) is
needed only to run the web UI.
