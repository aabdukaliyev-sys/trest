"""Flask web UI for the Kazakhstan investor tax optimization calculator.

Run with:
    python3 -m webapp.app
and open http://127.0.0.1:5000/

Wraps the same tax_optimizer package the CLI uses -- no calculation logic
lives here, only form parsing/rendering.
"""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request

from tax_optimizer.fifo_engine import METHOD_FIFO, match_trades
from tax_optimizer.io_csv import parse_dividends, parse_prices, parse_trades
from tax_optimizer.kz_tax_rules import compute_tax
from tax_optimizer.models import Dividend, Trade
from tax_optimizer.optimizer import build_optimization_report

app = Flask(__name__)

TRADE_FIELDS = ["date", "instrument", "side", "quantity", "price", "currency", "commission", "fx", "kase"]
DIVIDEND_FIELDS = ["date", "instrument", "amount", "currency", "fx", "foreign_tax", "kase", "holding_years"]
PRICE_FIELDS = ["instrument", "value"]


def _extract_rows(form, prefix: str, fields: list[str]) -> list[dict]:
    lists = {f: form.getlist(f"{prefix}_{f}") for f in fields}
    count = max((len(v) for v in lists.values()), default=0)
    rows = []
    for i in range(count):
        row = {f: (lists[f][i] if i < len(lists[f]) else "").strip() for f in fields}
        if any(row.values()):
            rows.append(row)
    return rows


def _decimal(value: str, field: str, row_label: str) -> Decimal:
    value = (value or "").strip()
    if not value:
        return Decimal("0")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError(f"{row_label}: некорректное число в поле «{field}»: {value!r}") from None


def _date(value: str, row_label: str):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{row_label}: некорректная дата «{value}», ожидается ГГГГ-ММ-ДД") from None


def _bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes", "да")


def _trade_from_row(row: dict, index: int) -> Trade:
    label = f"Сделка {index + 1}"
    side = row["side"].strip().upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"{label}: поле «сторона» должно быть BUY или SELL")
    quantity = _decimal(row["quantity"], "количество", label)
    if quantity <= 0:
        raise ValueError(f"{label}: количество должно быть больше нуля")
    return Trade(
        trade_date=_date(row["date"], label),
        instrument=row["instrument"].strip(),
        side=side,
        quantity=quantity,
        price=_decimal(row["price"], "цена", label),
        currency=row["currency"].strip().upper() or "KZT",
        commission=_decimal(row["commission"], "комиссия", label),
        fx_rate_to_kzt=_decimal(row["fx"], "курс к KZT", label) or Decimal("1"),
        kase_official_list=_bool(row["kase"]),
    )


def _dividend_from_row(row: dict, index: int) -> Dividend:
    label = f"Дивиденд {index + 1}"
    return Dividend(
        payment_date=_date(row["date"], label),
        instrument=row["instrument"].strip(),
        amount=_decimal(row["amount"], "сумма", label),
        currency=row["currency"].strip().upper() or "KZT",
        fx_rate_to_kzt=_decimal(row["fx"], "курс к KZT", label) or Decimal("1"),
        foreign_tax_withheld=_decimal(row["foreign_tax"], "удержанный налог", label),
        kase_official_list=_bool(row["kase"]),
        holding_period_years=_decimal(row["holding_years"], "лет владения", label),
    )


def _price_from_row(row: dict, index: int) -> tuple[str, Decimal]:
    label = f"Цена {index + 1}"
    instrument = row["instrument"].strip()
    if not instrument:
        raise ValueError(f"{label}: не указан инструмент")
    return instrument, _decimal(row["value"], "цена", label)


def _read_upload(file_storage) -> io.StringIO | None:
    if not file_storage or not file_storage.filename:
        return None
    return io.StringIO(file_storage.read().decode("utf-8-sig"))


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", trade_rows=[{}], div_rows=[{}], price_rows=[{}])


@app.route("/report", methods=["POST"])
def report():
    errors: list[str] = []
    trades: list[Trade] = []
    dividends: list[Dividend] = []
    prices: dict[str, Decimal] = {}

    trade_rows = _extract_rows(request.form, "trade", TRADE_FIELDS)
    div_rows = _extract_rows(request.form, "div", DIVIDEND_FIELDS)
    price_rows = _extract_rows(request.form, "price", PRICE_FIELDS)

    trades_upload = _read_upload(request.files.get("trades_file"))
    dividends_upload = _read_upload(request.files.get("dividends_file"))
    prices_upload = _read_upload(request.files.get("prices_file"))

    try:
        if trades_upload is not None:
            trades = parse_trades(trades_upload)
        else:
            trades = [_trade_from_row(row, i) for i, row in enumerate(trade_rows)]
    except (ValueError, KeyError) as e:
        errors.append(str(e) if isinstance(e, ValueError) else f"В файле сделок не хватает столбца {e}")

    try:
        if dividends_upload is not None:
            dividends = parse_dividends(dividends_upload)
        else:
            dividends = [_dividend_from_row(row, i) for i, row in enumerate(div_rows)]
    except (ValueError, KeyError) as e:
        errors.append(str(e) if isinstance(e, ValueError) else f"В файле дивидендов не хватает столбца {e}")

    try:
        if prices_upload is not None:
            prices = parse_prices(prices_upload)
        else:
            for i, row in enumerate(price_rows):
                instrument, value = _price_from_row(row, i)
                prices[instrument] = value
    except (ValueError, KeyError) as e:
        errors.append(str(e) if isinstance(e, ValueError) else f"В файле цен не хватает столбца {e}")

    if not trades and not errors:
        errors.append("Добавьте хотя бы одну сделку или загрузите CSV со сделками.")

    realized = open_positions = tax_report = opt = None
    if not errors:
        try:
            realized, open_positions = match_trades(trades, method=METHOD_FIFO)
            tax_report = compute_tax(realized, dividends)
            opt = build_optimization_report(trades, dividends, prices) if prices else None
        except ValueError as e:
            errors.append(str(e))

    if errors:
        return render_template(
            "index.html",
            errors=errors,
            trade_rows=trade_rows or [{}],
            div_rows=div_rows or [{}],
            price_rows=price_rows or [{}],
        )

    return render_template(
        "report.html",
        realized=sorted(realized, key=lambda g: g.close_date),
        open_positions=open_positions,
        tax_report=tax_report,
        opt=opt,
    )


if __name__ == "__main__":
    app.run(debug=True)
