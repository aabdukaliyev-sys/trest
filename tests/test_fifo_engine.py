import unittest
from datetime import date
from decimal import Decimal

from tax_optimizer.fifo_engine import METHOD_FIFO, METHOD_HIFO, METHOD_LIFO, match_trades
from tax_optimizer.models import Trade


def trade(d, side, qty, price, **kwargs):
    return Trade(
        trade_date=date.fromisoformat(d),
        instrument=kwargs.pop("instrument", "X"),
        side=side,
        quantity=Decimal(qty),
        price=Decimal(price),
        currency=kwargs.pop("currency", "KZT"),
        **kwargs,
    )


class FifoEngineTests(unittest.TestCase):
    def test_simple_fifo_gain(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100"),
            trade("2024-02-01", "SELL", "10", "150"),
        ]
        realized, open_positions = match_trades(trades)
        self.assertEqual(len(realized), 1)
        self.assertEqual(realized[0].gain_kzt, Decimal("500"))
        self.assertEqual(open_positions, {})

    def test_fifo_matches_oldest_lot_first(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100"),
            trade("2024-02-01", "BUY", "10", "200"),
            trade("2024-03-01", "SELL", "10", "250"),
        ]
        realized, open_positions = match_trades(trades, method=METHOD_FIFO)
        self.assertEqual(len(realized), 1)
        self.assertEqual(realized[0].cost_basis_kzt, Decimal("1000"))
        self.assertIn("X", open_positions)
        self.assertEqual(open_positions["X"].quantity, Decimal("10"))
        self.assertEqual(open_positions["X"].cost_basis_kzt, Decimal("2000"))

    def test_lifo_matches_newest_lot_first(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100"),
            trade("2024-02-01", "BUY", "10", "200"),
            trade("2024-03-01", "SELL", "10", "250"),
        ]
        realized, _ = match_trades(trades, method=METHOD_LIFO)
        self.assertEqual(realized[0].cost_basis_kzt, Decimal("2000"))

    def test_hifo_picks_highest_cost_lot(self):
        trades = [
            trade("2024-02-01", "BUY", "10", "200"),
            trade("2024-01-01", "BUY", "10", "100"),
            trade("2024-03-01", "SELL", "10", "250"),
        ]
        realized, _ = match_trades(trades, method=METHOD_HIFO)
        self.assertEqual(realized[0].cost_basis_kzt, Decimal("2000"))

    def test_sell_across_two_lots(self):
        trades = [
            trade("2024-01-01", "BUY", "5", "100"),
            trade("2024-02-01", "BUY", "5", "200"),
            trade("2024-03-01", "SELL", "8", "300"),
        ]
        realized, open_positions = match_trades(trades)
        self.assertEqual(len(realized), 2)
        self.assertEqual(realized[0].cost_basis_kzt, Decimal("500"))
        self.assertEqual(realized[1].cost_basis_kzt, Decimal("600"))
        self.assertEqual(open_positions["X"].quantity, Decimal("2"))

    def test_overselling_raises(self):
        trades = [
            trade("2024-01-01", "BUY", "5", "100"),
            trade("2024-02-01", "SELL", "10", "150"),
        ]
        with self.assertRaises(ValueError):
            match_trades(trades)

    def test_commission_reduces_gain(self):
        trades = [
            trade("2024-01-01", "BUY", "10", "100", commission=Decimal("50")),
            trade("2024-02-01", "SELL", "10", "150", commission=Decimal("20")),
        ]
        realized, _ = match_trades(trades)
        # cost basis = 1000 + 50 = 1050; proceeds = 1500 - 20 = 1480
        self.assertEqual(realized[0].cost_basis_kzt, Decimal("1050"))
        self.assertEqual(realized[0].proceeds_kzt, Decimal("1480"))

    def test_fx_conversion_applied(self):
        trades = [
            trade(
                "2024-01-01", "BUY", "10", "100", currency="USD",
                fx_rate_to_kzt=Decimal("450"),
            ),
            trade(
                "2024-02-01", "SELL", "10", "120", currency="USD",
                fx_rate_to_kzt=Decimal("470"),
            ),
        ]
        realized, _ = match_trades(trades)
        self.assertEqual(realized[0].cost_basis_kzt, Decimal("450000"))
        self.assertEqual(realized[0].proceeds_kzt, Decimal("564000"))


if __name__ == "__main__":
    unittest.main()
