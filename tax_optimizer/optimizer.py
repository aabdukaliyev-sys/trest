"""Optimization suggestions layered on top of the FIFO engine and KZ tax rules.

Everything here is a suggestion to evaluate with a broker/tax advisor, not an
instruction the calculator executes. Two techniques are covered for the MVP:

1. Tax-loss harvesting: open positions currently trading below cost could be
   sold to realize a loss that offsets already-realized taxable gains in the
   same tax period (Kazakhstan does not let individuals carry investment
   losses to future years or offset other income types, so unused loss
   capacity above this year's taxable gains has no tax value).
2. KASE-listing exemption reminder: flags open positions that are NOT marked
   as being on the official list of a KZ stock exchange, where selling via
   that listing would make the gain exempt from ИПН (Tax Code Art. 341).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .fifo_engine import METHOD_FIFO, METHOD_HIFO, METHOD_LIFO, match_trades
from .kz_tax_rules import compute_tax
from .models import Dividend, OpenPosition, Trade


@dataclass
class HarvestSuggestion:
    instrument: str
    quantity: Decimal
    unrealized_loss_kzt: Decimal
    current_price: Decimal


@dataclass
class OptimizationReport:
    harvest_suggestions: list[HarvestSuggestion]
    remaining_taxable_gain_after_harvest_kzt: Decimal
    unused_loss_positions: list[HarvestSuggestion]
    exemption_reminders: list[str]
    method_comparison_kzt: dict  # method name -> taxable gain under that method


def suggest_tax_loss_harvesting(
    open_positions: dict[str, OpenPosition],
    current_prices: dict[str, Decimal],
    taxable_gain_kzt: Decimal,
) -> tuple[list[HarvestSuggestion], Decimal, list[HarvestSuggestion]]:
    """Rank open lots with an unrealized loss and suggest harvesting up to
    the amount of already-realized taxable gain (beyond that, the loss has
    no offsetting value this tax period, since individuals cannot carry
    investment losses forward or use them against other income).

    Returns (selected_for_harvest, remaining_taxable_gain, unused_loss_positions).
    ``unused_loss_positions`` lists positions that are below cost but would
    have no tax benefit this year given the current taxable gain -- worth
    knowing about, but not worth selling purely for tax reasons right now.
    """
    candidates: list[HarvestSuggestion] = []
    for instrument, position in open_positions.items():
        price = current_prices.get(instrument)
        if price is None or position.kase_official_list:
            continue
        market_value = position.quantity * price
        if market_value >= position.cost_basis_kzt:
            continue
        candidates.append(
            HarvestSuggestion(
                instrument=instrument,
                quantity=position.quantity,
                unrealized_loss_kzt=position.cost_basis_kzt - market_value,
                current_price=price,
            )
        )

    candidates.sort(key=lambda c: c.unrealized_loss_kzt, reverse=True)

    selected: list[HarvestSuggestion] = []
    unused: list[HarvestSuggestion] = []
    remaining_gain = taxable_gain_kzt
    for c in candidates:
        if remaining_gain <= 0:
            unused.append(c)
            continue
        selected.append(c)
        remaining_gain -= c.unrealized_loss_kzt

    remaining_gain = max(remaining_gain, Decimal("0"))
    return selected, remaining_gain, unused


def exemption_reminders(open_positions: dict[str, OpenPosition]) -> list[str]:
    reminders = []
    for instrument, position in open_positions.items():
        if not position.kase_official_list:
            reminders.append(
                f"{instrument}: not flagged as KASE official-list. If it is (or becomes) "
                "listed there before you sell, the gain on sale may be exempt from ИПН "
                "(Tax Code Art. 341) -- verify listing status with your broker before "
                "the trade, since the exemption is tested at the sale date."
            )
    return reminders


def compare_cost_basis_methods(trades: list[Trade]) -> dict:
    results = {}
    for method in (METHOD_FIFO, METHOD_LIFO, METHOD_HIFO):
        realized, _ = match_trades(trades, method=method)
        taxable = sum((g.gain_kzt for g in realized if not g.kase_official_list), Decimal("0"))
        results[method] = max(taxable, Decimal("0"))
    return results


def build_optimization_report(
    trades: list[Trade],
    dividends: list[Dividend],
    current_prices: dict[str, Decimal],
) -> OptimizationReport:
    realized, open_positions = match_trades(trades, method=METHOD_FIFO)
    tax_report = compute_tax(realized, dividends)

    harvest, remaining, unused = suggest_tax_loss_harvesting(
        open_positions, current_prices, tax_report.taxable_gain_kzt
    )
    reminders = exemption_reminders(open_positions)
    method_comparison = compare_cost_basis_methods(trades)

    return OptimizationReport(
        harvest_suggestions=harvest,
        remaining_taxable_gain_after_harvest_kzt=remaining,
        unused_loss_positions=unused,
        exemption_reminders=reminders,
        method_comparison_kzt=method_comparison,
    )
