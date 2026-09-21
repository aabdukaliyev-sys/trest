"""Command-line entry point.

Usage:
    python -m tax_optimizer report --trades trades.csv [--dividends dividends.csv] \
        [--prices prices.csv]
"""

from __future__ import annotations

import argparse
from decimal import Decimal

from .fifo_engine import METHOD_FIFO, match_trades
from .io_csv import load_dividends, load_prices, load_trades
from .kz_tax_rules import compute_tax
from .optimizer import build_optimization_report


def _print_report(trades_path: str, dividends_path: str | None, prices_path: str | None) -> None:
    trades = load_trades(trades_path)
    dividends = load_dividends(dividends_path) if dividends_path else []
    prices = load_prices(prices_path) if prices_path else {}

    realized, open_positions = match_trades(trades, method=METHOD_FIFO)
    tax_report = compute_tax(realized, dividends)

    print("=== Realized gains/losses (FIFO) ===")
    for g in sorted(realized, key=lambda g: g.close_date):
        flag = " [KASE-exempt]" if g.kase_official_list else ""
        print(
            f"{g.close_date} {g.instrument}: qty={g.quantity} "
            f"gain={g.gain_kzt:.2f} KZT{flag}"
        )

    print("\n=== Open positions ===")
    for instrument, pos in open_positions.items():
        flag = " [KASE-exempt]" if pos.kase_official_list else ""
        print(f"{instrument}: qty={pos.quantity} cost_basis={pos.cost_basis_kzt:.2f} KZT{flag}")

    print("\n=== Tax summary (ИПН, 10%) ===")
    print(f"Taxable gain: {tax_report.taxable_gain_kzt:.2f} KZT -> tax {tax_report.gain_tax_kzt:.2f} KZT")
    print(f"Exempt gain (KASE listed): {tax_report.exempt_gain_kzt:.2f} KZT")
    print(
        f"Taxable dividends: {tax_report.taxable_dividend_kzt:.2f} KZT -> "
        f"tax {tax_report.dividend_tax_kzt:.2f} KZT "
        f"(foreign tax credit applied: {tax_report.foreign_tax_credit_kzt:.2f} KZT)"
    )
    print(f"Exempt dividends: {tax_report.exempt_dividend_kzt:.2f} KZT")
    print(f"TOTAL TAX DUE: {tax_report.total_tax_kzt:.2f} KZT")

    if tax_report.notes:
        print("\n--- Notes ---")
        for note in tax_report.notes:
            print(f"* {note}")

    if prices:
        opt = build_optimization_report(trades, dividends, prices)
        print("\n=== Optimization suggestions ===")
        if opt.harvest_suggestions:
            print("Tax-loss harvesting candidates (sell to offset this year's taxable gain):")
            for h in opt.harvest_suggestions:
                print(
                    f"  - {h.instrument}: sell {h.quantity} @ {h.current_price} "
                    f"-> realize loss {h.unrealized_loss_kzt:.2f} KZT"
                )
            print(
                f"  Remaining taxable gain after harvesting: "
                f"{opt.remaining_taxable_gain_after_harvest_kzt:.2f} KZT"
            )
        else:
            print("No open positions currently below cost -- nothing to harvest.")

        if opt.unused_loss_positions:
            print(
                "\nPositions below cost with no current tax benefit "
                "(no taxable gain left to offset this year; losses are not carried forward):"
            )
            for h in opt.unused_loss_positions:
                print(
                    f"  - {h.instrument}: unrealized loss {h.unrealized_loss_kzt:.2f} KZT "
                    f"at current price {h.current_price}"
                )

        if opt.exemption_reminders:
            print("\nKASE listing-exemption reminders:")
            for r in opt.exemption_reminders:
                print(f"  - {r}")

        print("\nCost-basis method comparison (taxable gain if realized this way):")
        for method, amount in opt.method_comparison_kzt.items():
            print(f"  {method}: {amount:.2f} KZT")

    print(
        "\nDISCLAIMER: figures are estimates based on a simplified reading of the "
        "Kazakhstan Tax Code (see docs/TAX_RULES_KZ.md) and are not certified tax "
        "advice. Confirm final figures and filing obligations with your broker's "
        "tax desk or a licensed tax consultant before relying on them."
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="tax_optimizer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Compute tax and optimization report")
    report_parser.add_argument("--trades", required=True, help="Path to trades CSV")
    report_parser.add_argument("--dividends", help="Path to dividends CSV")
    report_parser.add_argument("--prices", help="Path to current prices CSV (enables optimizer)")

    args = parser.parse_args()

    if args.command == "report":
        _print_report(args.trades, args.dividends, args.prices)


if __name__ == "__main__":
    main()
