"""Data structures for the short-term liquidity portfolio calculator.

Mirrors the structure of the "Калькулятор короткой ликвидности (РК) —
конструктор портфеля" spreadsheet: a client places a lump sum for a fixed
term across REPO, National Bank notes/government securities, and short
corporate bonds (plus whatever share is left in cash), and a broker trader
supplies the base annual yield and term-coefficient assumptions per
instrument. The result is the after-tax (КПН — corporate income tax) net
income and annualized equivalent yield.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

REPO = "REPO"
NOTES = "NOTES"
CORP_BONDS = "CORP_BONDS"

INSTRUMENTS = (REPO, NOTES, CORP_BONDS)

INSTRUMENT_LABELS = {
    REPO: "РЕПО",
    NOTES: "Ноты НБРК / ГЦБ",
    CORP_BONDS: "Краткосрочные корпоративные облигации",
}


@dataclass
class PortfolioInput:
    amount_kzt: Decimal
    term_days: Decimal
    kpn_rate_percent: Decimal
    shares_percent: dict[str, Decimal]  # instrument -> % of amount_kzt, need not fill CORP_BONDS etc if 0

    def __post_init__(self) -> None:
        if self.amount_kzt < 0:
            raise ValueError("Сумма размещения не может быть отрицательной")
        if self.term_days <= 0:
            raise ValueError("Срок должен быть больше нуля дней")
        total = sum(self.shares_percent.get(i, Decimal("0")) for i in INSTRUMENTS)
        if total > 100:
            raise ValueError(
                f"Сумма долей портфеля составляет {total}%, что больше 100%. "
                "Уменьшите доли инструментов."
            )

    @property
    def cash_share_percent(self) -> Decimal:
        return Decimal("100") - sum(self.shares_percent.get(i, Decimal("0")) for i in INSTRUMENTS)


@dataclass
class TermCoefficientTable:
    """Boundaries and per-instrument multipliers, ascending by boundary.

    Mirrors Excel's ``LOOKUP(term, boundaries, coefficients)``: the applied
    coefficient is the one at the largest boundary that is <= the requested
    term. A term shorter than the smallest boundary has no defined
    coefficient (Excel would return #N/A).
    """

    boundaries_days: list[Decimal]
    coefficients: dict[str, list[Decimal]]  # instrument -> list aligned with boundaries_days

    def coefficient_for(self, instrument: str, term_days: Decimal) -> Decimal:
        if term_days < self.boundaries_days[0]:
            raise ValueError(
                f"Срок {term_days} дн. короче минимальной границы таблицы коэффициентов "
                f"({self.boundaries_days[0]} дн.) — коэффициент не определён."
            )
        chosen = self.boundaries_days[0]
        chosen_index = 0
        for i, boundary in enumerate(self.boundaries_days):
            if boundary <= term_days:
                chosen = boundary
                chosen_index = i
            else:
                break
        return self.coefficients[instrument][chosen_index]


@dataclass
class TraderParams:
    base_annual_yield_percent: dict[str, Decimal]  # instrument -> % per annum
    term_coefficients: TermCoefficientTable


DEFAULT_TERM_BOUNDARIES = [Decimal(x) for x in (1, 7, 30, 90, 180, 365)]

DEFAULT_TRADER_PARAMS = TraderParams(
    base_annual_yield_percent={
        REPO: Decimal("14"),
        NOTES: Decimal("13"),
        CORP_BONDS: Decimal("17"),
    },
    term_coefficients=TermCoefficientTable(
        boundaries_days=DEFAULT_TERM_BOUNDARIES,
        coefficients={
            REPO: [Decimal(x) for x in ("1", "1", "0.95", "0.85", "0.7", "0.6")],
            NOTES: [Decimal(x) for x in ("0.6", "0.85", "1", "0.95", "0.8", "0.7")],
            CORP_BONDS: [Decimal(x) for x in ("0.3", "0.5", "0.7", "0.85", "1", "1")],
        },
    ),
)


@dataclass
class InstrumentResult:
    instrument: str
    share_percent: Decimal
    amount_kzt: Decimal
    base_yield_percent: Decimal
    term_coefficient: Decimal
    effective_annual_rate_percent: Decimal
    net_income_kzt: Decimal


@dataclass
class PortfolioResult:
    term_years: Decimal
    instruments: list[InstrumentResult]
    cash_amount_kzt: Decimal
    total_net_income_kzt: Decimal
    final_amount_kzt: Decimal
    period_return_after_tax: Decimal  # fraction, e.g. 0.004 = 0.4%
    annualized_return_after_tax: Decimal  # fraction
    notes: list[str] = field(default_factory=list)
