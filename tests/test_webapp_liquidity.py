import unittest

from webapp.app import app


class LiquidityWebAppTests(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_liquidity_index_loads(self):
        resp = self.client.get("/liquidity")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Конструктор портфеля короткой ликвидности".encode(), resp.data)
        # defaults pre-filled from the spreadsheet example
        self.assertIn(b'value="100000000"', resp.data)

    def test_liquidity_report_matches_spreadsheet_example(self):
        form = {
            "amount": "100000000",
            "term_days": "14",
            "kpn_rate": "20",
            "share_repo": "70",
            "share_notes": "30",
            "share_corp": "0",
            "base_repo": "14",
            "base_notes": "13",
            "base_corp": "17",
            "boundary": ["1", "7", "30", "90", "180", "365"],
            "coef_repo": ["1", "1", "0.95", "0.85", "0.7", "0.6"],
            "coef_notes": ["0.6", "0.85", "1", "0.95", "0.8", "0.7"],
            "coef_corp": ["0.3", "0.5", "0.7", "0.85", "1", "1"],
        }
        resp = self.client.post("/liquidity/report", data=form)
        self.assertEqual(resp.status_code, 200)
        # ~402,432.88 KZT net income and ~11.04% annualized, per the calculator's own test
        self.assertIn("402432.88".encode(), resp.data)
        self.assertIn("11.03".encode(), resp.data)

    def test_liquidity_report_rejects_shares_over_100(self):
        form = {
            "amount": "1000000",
            "term_days": "30",
            "kpn_rate": "20",
            "share_repo": "70",
            "share_notes": "40",
            "share_corp": "0",
            "base_repo": "14",
            "base_notes": "13",
            "base_corp": "17",
            "boundary": ["1", "7", "30", "90", "180", "365"],
            "coef_repo": ["1", "1", "0.95", "0.85", "0.7", "0.6"],
            "coef_notes": ["0.6", "0.85", "1", "0.95", "0.8", "0.7"],
            "coef_corp": ["0.3", "0.5", "0.7", "0.85", "1", "1"],
        }
        resp = self.client.post("/liquidity/report", data=form)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("больше 100%".encode(), resp.data)


if __name__ == "__main__":
    unittest.main()
