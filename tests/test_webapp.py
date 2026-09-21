import unittest

from webapp.app import app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_index_loads(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Калькулятор налоговой оптимизации".encode(), resp.data)

    def test_report_from_manual_rows(self):
        form = {
            "trade_date": ["2024-01-01", "2024-06-01"],
            "trade_instrument": ["KZTK", "KZTK"],
            "trade_side": ["BUY", "SELL"],
            "trade_quantity": ["10", "10"],
            "trade_price": ["100", "150"],
            "trade_currency": ["KZT", "KZT"],
            "trade_commission": ["0", "0"],
            "trade_fx": ["1", "1"],
            "trade_kase": ["false", "false"],
        }
        resp = self.client.post("/report", data=form)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("500.00 KZT".encode(), resp.data)  # gain
        self.assertIn("50.00 KZT".encode(), resp.data)  # tax at 10%

    def test_report_rejects_overselling_with_friendly_error(self):
        form = {
            "trade_date": ["2024-01-01"],
            "trade_instrument": ["X"],
            "trade_side": ["SELL"],
            "trade_quantity": ["5"],
            "trade_price": ["100"],
            "trade_currency": ["KZT"],
            "trade_commission": ["0"],
            "trade_fx": ["1"],
            "trade_kase": ["false"],
        }
        resp = self.client.post("/report", data=form)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("exceeds open quantity".encode(), resp.data)

    def test_report_requires_at_least_one_trade(self):
        resp = self.client.post("/report", data={})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Добавьте хотя бы одну сделку".encode(), resp.data)

    def test_invalid_number_gives_friendly_error(self):
        form = {
            "trade_date": ["2024-01-01"],
            "trade_instrument": ["X"],
            "trade_side": ["BUY"],
            "trade_quantity": ["not-a-number"],
            "trade_price": ["100"],
            "trade_currency": ["KZT"],
        }
        resp = self.client.post("/report", data=form)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("некорректное число".encode(), resp.data)

    def test_report_with_csv_upload(self):
        import io

        csv_content = (
            "date,instrument,side,quantity,price,currency,commission,fx_rate_to_kzt,kase_official_list\n"
            "2024-01-01,X,BUY,10,100,KZT,0,1,FALSE\n"
            "2024-06-01,X,SELL,10,200,KZT,0,1,FALSE\n"
        )
        data = {
            "trades_file": (io.BytesIO(csv_content.encode()), "trades.csv"),
        }
        resp = self.client.post("/report", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("1000.00 KZT".encode(), resp.data)  # gain
        self.assertIn("100.00 KZT".encode(), resp.data)  # tax


if __name__ == "__main__":
    unittest.main()
