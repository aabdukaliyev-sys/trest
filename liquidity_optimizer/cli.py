"""Command-line entry point for the short-term liquidity portfolio calculator.

Usage:
    python3 -m liquidity_optimizer report --amount 100000000 --term-days 14 \
        --kpn-rate 20 --repo 70 --notes 30 --corp-bonds 0
"""

from __future__ import annotations

import argparse
from decimal import Decimal

from .calculator import compute_portfolio, instrument_label
from .models import CORP_BONDS, DEFAULT_TRADER_PARAMS, NOTES, REPO, PortfolioInput


def _print_report(amount, term_days, kpn_rate, repo, notes, corp_bonds) -> None:
    portfolio = PortfolioInput(
        amount_kzt=Decimal(str(amount)),
        term_days=Decimal(str(term_days)),
        kpn_rate_percent=Decimal(str(kpn_rate)),
        shares_percent={
            REPO: Decimal(str(repo)),
            NOTES: Decimal(str(notes)),
            CORP_BONDS: Decimal(str(corp_bonds)),
        },
    )
    result = compute_portfolio(portfolio, DEFAULT_TRADER_PARAMS)

    print(f"Сумма размещения: {portfolio.amount_kzt:.2f} KZT, срок {portfolio.term_days} дн., КПН {portfolio.kpn_rate_percent}%")
    print(f"Неразмещённый остаток (кэш): {portfolio.cash_share_percent}% = {result.cash_amount_kzt:.2f} KZT\n")

    print("=== По инструментам ===")
    for r in result.instruments:
        print(
            f"{instrument_label(r.instrument)}: доля {r.share_percent}%, сумма {r.amount_kzt:.2f} KZT, "
            f"база {r.base_yield_percent}% x коэф. {r.term_coefficient} = "
            f"эфф. ставка {r.effective_annual_rate_percent}% годовых -> "
            f"чистый доход {r.net_income_kzt:.2f} KZT"
        )

    print("\n=== Итого ===")
    print(f"Чистый доход: {result.total_net_income_kzt:.2f} KZT")
    print(f"Итоговая сумма: {result.final_amount_kzt:.2f} KZT")
    print(f"Доходность за период (after-tax): {result.period_return_after_tax * 100:.4f}%")
    print(f"Годовая эквивалентная доходность (after-tax): {result.annualized_return_after_tax * 100:.4f}%")

    if result.notes:
        print("\n--- Примечания ---")
        for n in result.notes:
            print(f"* {n}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="liquidity_optimizer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Compute the portfolio after-tax result")
    report_parser.add_argument("--amount", required=True, type=str, help="Сумма размещения, KZT")
    report_parser.add_argument("--term-days", required=True, type=str, help="Срок, дней")
    report_parser.add_argument("--kpn-rate", required=True, type=str, help="Ставка КПН, %")
    report_parser.add_argument("--repo", default="0", type=str, help="Доля РЕПО, %")
    report_parser.add_argument("--notes", default="0", type=str, help="Доля нот НБРК/ГЦБ, %")
    report_parser.add_argument("--corp-bonds", default="0", type=str, help="Доля корп. облигаций, %")

    args = parser.parse_args()
    if args.command == "report":
        _print_report(args.amount, args.term_days, args.kpn_rate, args.repo, args.notes, args.corp_bonds)


if __name__ == "__main__":
    main()
