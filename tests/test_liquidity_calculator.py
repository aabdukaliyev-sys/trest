import unittest
from decimal import Decimal

from liquidity_optimizer.calculator import compute_portfolio
from liquidity_optimizer.models import (
    CORP_BONDS,
    DEFAULT_TERM_BOUNDARIES,
    DEFAULT_TRADER_PARAMS,
    NOTES,
    REPO,
    PortfolioInput,
    TermCoefficientTable,
    TraderParams,
)


def D(x):
    return Decimal(str(x))


class LiquidityCalculatorTests(unittest.TestCase):
    def test_matches_spreadsheet_example(self):
        """Reproduces the exact scenario from the source spreadsheet:
        100,000,000 KZT, 14-day term, 20% KPN, 70% REPO / 30% notes."""
        portfolio = PortfolioInput(
            amount_kzt=D(100_000_000),
            term_days=D(14),
            kpn_rate_percent=D(20),
            shares_percent={REPO: D(70), NOTES: D(30), CORP_BONDS: D(0)},
        )
        result = compute_portfolio(portfolio, DEFAULT_TRADER_PARAMS)

        repo = next(r for r in result.instruments if r.instrument == REPO)
        notes = next(r for r in result.instruments if r.instrument == NOTES)
        corp = next(r for r in result.instruments if r.instrument == CORP_BONDS)

        # Term 14 days -> last boundary <= 14 is 7, coefficients: REPO=1, NOTES=0.85
        self.assertEqual(repo.term_coefficient, D("1"))
        self.assertEqual(notes.term_coefficient, D("0.85"))
        self.assertEqual(repo.effective_annual_rate_percent, D("14"))
        self.assertEqual(notes.effective_annual_rate_percent, D("11.05"))

        self.assertEqual(repo.amount_kzt, D(70_000_000))
        self.assertEqual(notes.amount_kzt, D(30_000_000))
        self.assertEqual(corp.amount_kzt, D(0))
        self.assertEqual(corp.net_income_kzt, D(0))

        # net income = amount * (rate/100) * term_years * (1 - kpn/100)
        expected_repo_income = D(70_000_000) * D("0.14") * (D(14) / D(365)) * D("0.8")
        expected_notes_income = D(30_000_000) * D("0.1105") * (D(14) / D(365)) * D("0.8")
        self.assertAlmostEqual(float(repo.net_income_kzt), float(expected_repo_income), places=6)
        self.assertAlmostEqual(float(notes.net_income_kzt), float(expected_notes_income), places=6)

        expected_total = expected_repo_income + expected_notes_income
        self.assertAlmostEqual(float(result.total_net_income_kzt), float(expected_total), places=6)
        self.assertAlmostEqual(
            float(result.final_amount_kzt), float(D(100_000_000) + expected_total), places=6
        )

        expected_annualized = (result.final_amount_kzt / D(100_000_000)) ** (D(365) / D(14)) - 1
        self.assertAlmostEqual(
            float(result.annualized_return_after_tax), float(expected_annualized), places=8
        )
        # sanity: annualized after-tax yield should land near 10-11% given ~13-14% base yields
        self.assertGreater(result.annualized_return_after_tax, D("0.08"))
        self.assertLess(result.annualized_return_after_tax, D("0.13"))

    def test_cash_share_computed_automatically(self):
        portfolio = PortfolioInput(
            amount_kzt=D(1_000_000),
            term_days=D(30),
            kpn_rate_percent=D(20),
            shares_percent={REPO: D(50)},
        )
        self.assertEqual(portfolio.cash_share_percent, D(50))
        result = compute_portfolio(portfolio, DEFAULT_TRADER_PARAMS)
        self.assertEqual(result.cash_amount_kzt, D(500_000))

    def test_shares_over_100_percent_rejected(self):
        with self.assertRaises(ValueError):
            PortfolioInput(
                amount_kzt=D(1_000_000),
                term_days=D(30),
                kpn_rate_percent=D(20),
                shares_percent={REPO: D(70), NOTES: D(40)},
            )

    def test_zero_amount_yields_zero_return(self):
        portfolio = PortfolioInput(
            amount_kzt=D(0),
            term_days=D(30),
            kpn_rate_percent=D(20),
            shares_percent={REPO: D(100)},
        )
        result = compute_portfolio(portfolio, DEFAULT_TRADER_PARAMS)
        self.assertEqual(result.period_return_after_tax, D(0))
        self.assertEqual(result.annualized_return_after_tax, D(0))

    def test_term_shorter_than_smallest_boundary_raises(self):
        table = TermCoefficientTable(
            boundaries_days=[D(x) for x in DEFAULT_TERM_BOUNDARIES],
            coefficients=DEFAULT_TRADER_PARAMS.term_coefficients.coefficients,
        )
        with self.assertRaises(ValueError):
            table.coefficient_for(REPO, D("0.5"))

    def test_coefficient_lookup_picks_largest_boundary_leq_term(self):
        table = DEFAULT_TRADER_PARAMS.term_coefficients
        self.assertEqual(table.coefficient_for(REPO, D(1)), D("1"))
        self.assertEqual(table.coefficient_for(REPO, D(6)), D("1"))
        self.assertEqual(table.coefficient_for(REPO, D(7)), D("1"))
        self.assertEqual(table.coefficient_for(REPO, D(29)), D("1"))
        self.assertEqual(table.coefficient_for(REPO, D(30)), D("0.95"))
        self.assertEqual(table.coefficient_for(REPO, D(1000)), D("0.6"))

    def test_custom_trader_params_are_used(self):
        custom = TraderParams(
            base_annual_yield_percent={REPO: D(20), NOTES: D(10), CORP_BONDS: D(15)},
            term_coefficients=DEFAULT_TRADER_PARAMS.term_coefficients,
        )
        portfolio = PortfolioInput(
            amount_kzt=D(1_000_000),
            term_days=D(30),
            kpn_rate_percent=D(0),
            shares_percent={REPO: D(100)},
        )
        result = compute_portfolio(portfolio, custom)
        repo = result.instruments[0]
        self.assertEqual(repo.base_yield_percent, D(20))


if __name__ == "__main__":
    unittest.main()
