import unittest
from datetime import date
from decimal import Decimal

from tax_optimizer.kz_tax_rules import compute_tax
from tax_optimizer.models import Dividend, RealizedGain


def gain(amount, kase=False):
    return RealizedGain(
        close_date=date(2024, 1, 1),
        instrument="X",
        quantity=Decimal("1"),
        proceeds_kzt=Decimal(amount),
        cost_basis_kzt=Decimal("0"),
        kase_official_list=kase,
    )


class KzTaxRulesTests(unittest.TestCase):
    def test_flat_rate_on_taxable_gain(self):
        report = compute_tax([gain("1000")], [])
        self.assertEqual(report.taxable_gain_kzt, Decimal("1000"))
        self.assertEqual(report.gain_tax_kzt, Decimal("100.00"))

    def test_kase_listed_gain_is_exempt(self):
        report = compute_tax([gain("1000", kase=True)], [])
        self.assertEqual(report.taxable_gain_kzt, Decimal("0"))
        self.assertEqual(report.exempt_gain_kzt, Decimal("1000"))
        self.assertEqual(report.gain_tax_kzt, Decimal("0.00"))

    def test_net_loss_floors_at_zero_and_notes(self):
        report = compute_tax([gain("-500")], [])
        self.assertEqual(report.taxable_gain_kzt, Decimal("0"))
        self.assertEqual(report.gain_tax_kzt, Decimal("0.00"))
        self.assertTrue(any("cannot carry" in n for n in report.notes))

    def test_gains_and_losses_net_within_taxable_category(self):
        report = compute_tax([gain("1000"), gain("-400")], [])
        self.assertEqual(report.taxable_gain_kzt, Decimal("600"))
        self.assertEqual(report.gain_tax_kzt, Decimal("60.00"))

    def test_dividend_taxed_at_flat_rate(self):
        div = Dividend(
            payment_date=date(2024, 1, 1),
            instrument="AAPL",
            amount=Decimal("100"),
            currency="USD",
            fx_rate_to_kzt=Decimal("1"),
        )
        report = compute_tax([], [div])
        self.assertEqual(report.taxable_dividend_kzt, Decimal("100"))
        self.assertEqual(report.dividend_tax_kzt, Decimal("10.00"))

    def test_foreign_tax_credit_reduces_dividend_tax(self):
        div = Dividend(
            payment_date=date(2024, 1, 1),
            instrument="AAPL",
            amount=Decimal("100"),
            currency="USD",
            fx_rate_to_kzt=Decimal("1"),
            foreign_tax_withheld=Decimal("3"),
        )
        report = compute_tax([], [div])
        self.assertEqual(report.foreign_tax_credit_kzt, Decimal("3.00"))
        self.assertEqual(report.dividend_tax_kzt, Decimal("7.00"))

    def test_excess_foreign_withholding_capped_and_noted(self):
        div = Dividend(
            payment_date=date(2024, 1, 1),
            instrument="AAPL",
            amount=Decimal("100"),
            currency="USD",
            fx_rate_to_kzt=Decimal("1"),
            foreign_tax_withheld=Decimal("30"),
        )
        report = compute_tax([], [div])
        self.assertEqual(report.foreign_tax_credit_kzt, Decimal("10.00"))
        self.assertEqual(report.dividend_tax_kzt, Decimal("0.00"))
        self.assertTrue(any("exceeds the KZ tax" in n for n in report.notes))

    def test_dividend_exempt_after_three_years_holding(self):
        div = Dividend(
            payment_date=date(2024, 1, 1),
            instrument="KZTK",
            amount=Decimal("100"),
            currency="KZT",
            holding_period_years=Decimal("3"),
        )
        report = compute_tax([], [div])
        self.assertEqual(report.exempt_dividend_kzt, Decimal("100"))
        self.assertEqual(report.dividend_tax_kzt, Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()
