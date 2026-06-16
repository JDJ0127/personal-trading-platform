from datetime import date
from unittest import TestCase

from trading_platform.data.tushare_provider import TushareClient, TushareDataProvider, TushareError


class TushareProviderTest(TestCase):
    def test_load_daily_bars_merges_adj_factor(self) -> None:
        def transport(payload: dict) -> dict:
            if payload["api_name"] == "daily":
                return {
                    "code": 0,
                    "msg": "",
                    "data": {
                        "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "pct_chg", "vol", "amount"],
                        "items": [["600030.SH", "20260601", 20.0, 20.5, 19.8, 20.2, 19.9, 1.51, 5000.0, 101000.0]],
                    },
                }
            if payload["api_name"] == "adj_factor":
                return {
                    "code": 0,
                    "msg": "",
                    "data": {
                        "fields": ["ts_code", "trade_date", "adj_factor"],
                        "items": [["600030.SH", "20260601", 1.234]],
                    },
                }
            raise AssertionError(payload["api_name"])

        provider = TushareDataProvider(TushareClient("test-token", transport=transport))

        bars = provider.load_daily_bars(date(2026, 6, 1), date(2026, 6, 1), "600030.SH")

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].ts_code, "600030.SH")
        self.assertEqual(bars[0].trade_date, date(2026, 6, 1))
        self.assertEqual(bars[0].adj_factor, 1.234)

    def test_client_raises_on_tushare_error(self) -> None:
        def transport(_payload: dict) -> dict:
            return {"code": -2001, "msg": "permission denied"}

        client = TushareClient("test-token", transport=transport)

        with self.assertRaises(TushareError):
            client.query("daily")

    def test_load_trade_calendar(self) -> None:
        def transport(payload: dict) -> dict:
            self.assertEqual(payload["api_name"], "trade_cal")
            return {
                "code": 0,
                "msg": "",
                "data": {
                    "fields": ["exchange", "cal_date", "is_open", "pretrade_date"],
                    "items": [["SSE", "20260601", 1, "20260529"], ["SSE", "20260602", 0, "20260601"]],
                },
            }

        provider = TushareDataProvider(TushareClient("test-token", transport=transport))

        calendar = provider.load_trade_calendar(date(2026, 6, 1), date(2026, 6, 2))

        self.assertEqual(len(calendar), 2)
        self.assertTrue(calendar[0].is_open)
        self.assertFalse(calendar[1].is_open)
        self.assertEqual(calendar[0].pretrade_date, date(2026, 5, 29))
