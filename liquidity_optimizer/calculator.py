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
    DepositComparison,
    InstrumentResult,
    PortfolioInput,
    PortfolioResult,
    TraderParams,
)

DAYS_PER_YEAR = Decimal("365")


def _annualized_return(final_amount: Decimal, amount: Decimal, term_years: Decimal) -> Decimal:
    if amount > 0 and term_years > 0:
        return (final_amount / amount) ** (Decimal("1") / term_years) - Decimal("1")
    return Decimal("0")


def _compute_deposit(
    amount: Decimal, term_years: Decimal, kpn_fraction: Decimal, deposit_rate_percent: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Same lump sum, same term, placed in an ordinary bank deposit instead.

    Deposit interest is treated as ordinary income taxed at the same КПН
    rate as the portfolio's income -- a simplifying assumption; some deposit
    or government-instrument interest may qualify for a different regime,
    so confirm with your bank/tax advisor for your specific instrument.
    """
    net_income = amount * (deposit_rate_percent / Decimal("100")) * term_years * (Decimal("1") - kpn_fraction)
    final_amount = amount + net_income
    annualized_return = _annualized_return(final_amount, amount, term_years)
    return net_income, final_amount, annualized_return


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
    annualized_return = _annualized_return(final_amount, portfolio.amount_kzt, term_years)

    notes = [
        "Это сценарная модель для демонстрации. Доходности не гарантируются и зависят "
        "от рынка и доступности инструментов у брокера.",
    ]
    if portfolio.cash_share_percent > 0:
        notes.append(
            f"{portfolio.cash_share_percent}% суммы остаётся неразмещённым (кэш) и не приносит дохода."
        )

    deposit = None
    if portfolio.deposit_rate_percent is not None:
        deposit_income, deposit_final, deposit_annualized = _compute_deposit(
            portfolio.amount_kzt, term_years, kpn_fraction, portfolio.deposit_rate_percent
        )
        deposit = DepositComparison(
            deposit_rate_percent=portfolio.deposit_rate_percent,
            net_income_kzt=deposit_income,
            final_amount_kzt=deposit_final,
            annualized_return_after_tax=deposit_annualized,
            advantage_net_income_kzt=total_net_income - deposit_income,
            advantage_annualized_pp=annualized_return - deposit_annualized,
        )
        notes.append(
            "Сравнение с депозитом предполагает ту же ставку КПН на процентный доход по "
            "депозиту — уточните у банка, применяется ли к вашему вкладу другой налоговый режим."
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
        deposit=deposit,
    )


def instrument_label(instrument: str) -> str:
    return INSTRUMENT_LABELS[instrument]
