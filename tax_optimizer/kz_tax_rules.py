"""Individual income tax (ИПН) rules for investment income in Kazakhstan.

This module encodes a simplified, documented reading of the Kazakhstan Tax
Code as it applies to a resident individual trading through a broker. It is
NOT certified tax advice -- rates, thresholds and exemption conditions change
over time and depend on facts the calculator cannot verify (e.g. whether an
issuer's assets are more than 50% attributable to subsoil users, which is a
condition for the KASE listed-share exemption). Always confirm current rules
and your specific facts with your broker's tax desk or a licensed tax
consultant before filing. See docs/TAX_RULES_KZ.md for the assumptions and
source articles this module is based on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .models import Dividend, RealizedGain

IPN_RATE = Decimal("0.10")
DIVIDEND_EXEMPTION_HOLDING_YEARS = Decimal("3")


@dataclass
class TaxReport:
    taxable_gain_kzt: Decimal = Decimal("0")
    exempt_gain_kzt: Decimal = Decimal("0")
    taxable_dividend_kzt: Decimal = Decimal("0")
    exempt_dividend_kzt: Decimal = Decimal("0")
    foreign_tax_credit_kzt: Decimal = Decimal("0")
    gain_tax_kzt: Decimal = Decimal("0")
    dividend_tax_kzt: Decimal = Decimal("0")
    notes: list[str] = field(default_factory=list)

    @property
    def total_tax_kzt(self) -> Decimal:
        return self.gain_tax_kzt + self.dividend_tax_kzt


def compute_tax(realized_gains: list[RealizedGain], dividends: list[Dividend]) -> TaxReport:
    report = TaxReport()

    taxable_lots = [g for g in realized_gains if not g.kase_official_list]
    exempt_lots = [g for g in realized_gains if g.kase_official_list]

    report.exempt_gain_kzt = sum((g.gain_kzt for g in exempt_lots), Decimal("0"))

    net_taxable_gain = sum((g.gain_kzt for g in taxable_lots), Decimal("0"))
    if net_taxable_gain < 0:
        report.notes.append(
            "Net loss on non-exempt securities is %.2f KZT. Individuals cannot "
            "carry this loss forward or offset it against other income types; "
            "the taxable base for gains is floored at zero." % net_taxable_gain
        )
        net_taxable_gain = Decimal("0")
    report.taxable_gain_kzt = net_taxable_gain
    report.gain_tax_kzt = (report.taxable_gain_kzt * IPN_RATE).quantize(Decimal("0.01"))

    for d in dividends:
        exempt = d.kase_official_list or d.holding_period_years >= DIVIDEND_EXEMPTION_HOLDING_YEARS
        if exempt:
            report.exempt_dividend_kzt += d.amount_kzt
            continue
        report.taxable_dividend_kzt += d.amount_kzt
        tax_before_credit = (d.amount_kzt * IPN_RATE).quantize(Decimal("0.01"))
        credit = min(d.foreign_tax_withheld_kzt, tax_before_credit)
        report.foreign_tax_credit_kzt += credit
        report.dividend_tax_kzt += tax_before_credit - credit
        if d.foreign_tax_withheld_kzt > tax_before_credit:
            report.notes.append(
                f"{d.instrument}: foreign tax withheld ({d.foreign_tax_withheld_kzt:.2f} KZT) "
                f"exceeds the KZ tax on this dividend ({tax_before_credit:.2f} KZT); the excess "
                "is not refundable and requires Form 240.00 with supporting withholding "
                "documents from the broker to claim the credit that is usable."
            )

    if report.taxable_dividend_kzt > 0 or report.taxable_gain_kzt > 0:
        report.notes.append(
            "Foreign-source gains/dividends are generally self-declared on Form 240.00 "
            "(due 31 March of the following year, tax payable by 10 April); KZT-source "
            "income via a licensed KZ broker may already be withheld at source -- confirm "
            "with your broker which amounts they have already remitted."
        )

    return report
