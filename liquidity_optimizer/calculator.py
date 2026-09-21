"""Computes the after-tax result of a short-term liquidity portfolio.

Mirrors the "Расчёт" sheet of the source spreadsheet formula for formula:
for each instrument, amount = total * share%; effective annual rate =
base yield% * term coefficient; net income = amount * (effective rate / 100)
* term_years * (1 - KPN% / 100). Cash placed nowhere earns nothing.
"""

from __future__ import annotations

from decimal import Decimal

from .models import (
    INSTRUMENT_LABELS,
    INSTRUMENTS,
    InstrumentResult,
    PortfolioInput,
    PortfolioResult,
    TraderParams,
)

DAYS_PER_YEAR = Decimal("365")


def compute_portfolio(portfolio: PortfolioInput, trader: TraderParams) -> PortfolioResult:
    term_years = portfolio.term_days / DAYS_PER_YEAR
    kpn_fraction = portfolio.kpn_rate_percent / Decimal("100")

    results: list[InstrumentResult] = []
    for instrument in INSTRUMENTS:
        share = portfolio.shares_percent.get(instrument, Decimal("0"))
        amount = portfolio.amount_kzt * share / Decimal("100")
        base_yield = trader.base_annual_yield_percent[instrument]
        coefficient = trader.term_coefficients.coefficient_for(instrument, portfolio.term_days)
        effective_rate = base_yield * coefficient
        net_income = amount * (effective_rate / Decimal("100")) * term_years * (Decimal("1") - kpn_fraction)
        results.append(
            InstrumentResult(
                instrument=instrument,
                share_percent=share,
                amount_kzt=amount,
                base_yield_percent=base_yield,
                term_coefficient=coefficient,
                effective_annual_rate_percent=effective_rate,
                net_income_kzt=net_income,
            )
        )

    cash_amount = portfolio.amount_kzt * portfolio.cash_share_percent / Decimal("100")
    total_net_income = sum((r.net_income_kzt for r in results), Decimal("0"))
    final_amount = portfolio.amount_kzt + total_net_income

    period_return = (
        total_net_income / portfolio.amount_kzt if portfolio.amount_kzt > 0 else Decimal("0")
    )
    if portfolio.amount_kzt > 0 and term_years > 0:
        annualized_return = (final_amount / portfolio.amount_kzt) ** (Decimal("1") / term_years) - Decimal("1")
    else:
        annualized_return = Decimal("0")

    notes = [
        "Это сценарная модель для демонстрации. Доходности не гарантируются и зависят "
        "от рынка и доступности инструментов у брокера.",
    ]
    if portfolio.cash_share_percent > 0:
        notes.append(
            f"{portfolio.cash_share_percent}% суммы остаётся неразмещённым (кэш) и не приносит дохода."
        )

    return PortfolioResult(
        term_years=term_years,
        instruments=results,
        cash_amount_kzt=cash_amount,
        total_net_income_kzt=total_net_income,
        final_amount_kzt=final_amount,
        period_return_after_tax=period_return,
        annualized_return_after_tax=annualized_return,
        notes=notes,
    )


def instrument_label(instrument: str) -> str:
    return INSTRUMENT_LABELS[instrument]
