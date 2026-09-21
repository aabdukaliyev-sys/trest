"""CSV readers for trades, dividends and current-price lookups.

Expected columns (header row required, order does not matter):

trades.csv:
    date, instrument, side, quantity, price, currency, commission,
    fx_rate_to_kzt, kase_official_list
    - date: YYYY-MM-DD
    - side: BUY or SELL
    - commission, fx_rate_to_kzt: optional, default to 0 and 1
    - kase_official_list: optional, TRUE/FALSE, default FALSE

dividends.csv:
    date, instrument, amount, currency, fx_rate_to_kzt,
    foreign_tax_withheld, kase_official_list, holding_period_years
    - all columns except date, instrument, amount are optional

prices.csv:
    instrument, price
    - price must already be expressed in KZT (convert foreign-currency quotes
      using the current NBK rate before writing this file), since it is
      compared directly against KZT cost bases from the trades file.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal

from .models import Dividend, Trade


def _bool(value: str | None) -> bool:
    return str(value).strip().upper() in ("TRUE", "1", "YES", "Y")


def _decimal(value: str | None, default: str = "0") -> Decimal:
    value = (value or "").strip()
    return Decimal(value) if value else Decimal(default)


def _date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def load_trades(path: str) -> list[Trade]:
    trades = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            trades.append(
                Trade(
                    trade_date=_date(row["date"]),
                    instrument=row["instrument"].strip(),
                    side=row["side"].strip().upper(),
                    quantity=_decimal(row["quantity"]),
                    price=_decimal(row["price"]),
                    currency=row["currency"].strip().upper(),
                    commission=_decimal(row.get("commission")),
                    fx_rate_to_kzt=_decimal(row.get("fx_rate_to_kzt"), default="1"),
                    kase_official_list=_bool(row.get("kase_official_list")),
                )
            )
    return trades


def load_dividends(path: str) -> list[Dividend]:
    dividends = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dividends.append(
                Dividend(
                    payment_date=_date(row["date"]),
                    instrument=row["instrument"].strip(),
                    amount=_decimal(row["amount"]),
                    currency=row["currency"].strip().upper(),
                    fx_rate_to_kzt=_decimal(row.get("fx_rate_to_kzt"), default="1"),
                    foreign_tax_withheld=_decimal(row.get("foreign_tax_withheld")),
                    kase_official_list=_bool(row.get("kase_official_list")),
                    holding_period_years=_decimal(row.get("holding_period_years")),
                )
            )
    return dividends


def load_prices(path: str) -> dict[str, Decimal]:
    prices = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            prices[row["instrument"].strip()] = _decimal(row["price"])
    return prices
