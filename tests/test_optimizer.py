import unittest
from datetime import date
from decimal import Decimal

from tax_optimizer.optimizer import build_optimization_report
from tax_optimizer.models import Trade


def trade(d, side, qty, price, instrument="X", **kwargs):
    return Trade(
        trade_date=date.fromisoformat(d),
        instrument=instrument,
        side=side,
        quantity=Decimal(qty),
        price=Decimal(price),
        currency=kwargs.pop("currency", "KZT"),
        **kwargs,
    )


class OptimizerTests(unittest.TestCase):
    def test_harvest_suggested_for_position_below_cost(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100", instrument="LOSER"),
            trade("2024-01-01", "BUY", "10", "100", instrument="WINNER"),
            trade("2024-06-01", "SELL", "10", "200", instrument="WINNER"),
        ]
        prices = {"LOSER": Decimal("50")}
        report = build_optimization_report(trades, [], prices)

        self.assertEqual(len(report.harvest_suggestions), 1)
        self.assertEqual(report.harvest_suggestions[0].instrument, "LOSER")
        self.assertEqual(report.harvest_suggestions[0].unrealized_loss_kzt, Decimal("500"))
        # 1000 realized gain on WINNER minus 500 harvestable loss on LOSER
        self.assertEqual(report.remaining_taxable_gain_after_harvest_kzt, Decimal("500"))

    def test_no_harvest_when_no_losers(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100", instrument="WINNER"),
        ]
        prices = {"WINNER": Decimal("150")}
        report = build_optimization_report(trades, [], prices)
        self.assertEqual(report.harvest_suggestions, [])

    def test_kase_exempt_position_excluded_from_harvest_and_reminders(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100", instrument="KZTK", kase_official_list=True),
        ]
        prices = {"KZTK": Decimal("50")}
        report = build_optimization_report(trades, [], prices)
        self.assertEqual(report.harvest_suggestions, [])
        self.assertEqual(report.exemption_reminders, [])

    def test_exemption_reminder_for_non_flagged_open_position(self):
        trades = [trade("2024-01-01", "BUY", "10", "100", instrument="AAPL")]
        report = build_optimization_report(trades, [], {})
        self.assertEqual(len(report.exemption_reminders), 1)
        self.assertIn("AAPL", report.exemption_reminders[0])

    def test_method_comparison_present_for_all_three_methods(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100"),
            trade("2024-02-01", "BUY", "10", "200"),
            trade("2024-03-01", "SELL", "10", "250"),
        ]
        report = build_optimization_report(trades, [], {})
        self.assertEqual(set(report.method_comparison_kzt), {"FIFO", "LIFO", "HIFO"})
        self.assertEqual(report.method_comparison_kzt["FIFO"], Decimal("1500"))
        self.assertEqual(report.method_comparison_kzt["LIFO"], Decimal("500"))
        self.assertEqual(report.method_comparison_kzt["HIFO"], Decimal("500"))


if __name__ == "__main__":
    unittest.main()
