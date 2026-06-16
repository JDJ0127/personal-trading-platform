from datetime import date
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import DailyBar
from trading_platform.risk.market_risk import build_market_risk_report


class MarketRiskTest(TestCase):
    def test_build_market_risk_report_scores_latest_breadth(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = SQLiteStore(f"{temp_dir}/risk.sqlite")
            store.initialize()
            store.upsert_daily_bars(
                [
                    DailyBar(date(2026, 6, 1), "000001.SZ", 10, 10, 10, 10, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 2), "000001.SZ", 11, 11, 11, 11, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 3), "000001.SZ", 12, 12, 12, 12, 11, 100, 100_000_000),
                    DailyBar(date(2026, 6, 1), "000002.SZ", 20, 20, 20, 20, 20, 100, 100_000_000),
                    DailyBar(date(2026, 6, 2), "000002.SZ", 21, 21, 21, 21, 20, 100, 100_000_000),
                    DailyBar(date(2026, 6, 3), "000002.SZ", 22, 22, 22, 22, 21, 100, 100_000_000),
                    DailyBar(date(2026, 6, 1), "000003.SZ", 30, 30, 30, 30, 30, 100, 100_000_000),
                    DailyBar(date(2026, 6, 2), "000003.SZ", 29, 29, 29, 29, 30, 100, 100_000_000),
                    DailyBar(date(2026, 6, 3), "000003.SZ", 28, 28, 28, 28, 29, 100, 100_000_000),
                ]
            )

            report = build_market_risk_report(store)

            self.assertEqual(report["tradeDate"], "2026-06-03")
            self.assertEqual(report["market"]["score"], 5)
            self.assertEqual(report["market"]["state"], "强势")
            self.assertEqual(report["risk"]["state"], "Normal")

    def test_build_market_risk_report_uses_requested_trade_date_without_future_bars(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = SQLiteStore(f"{temp_dir}/risk.sqlite")
            store.initialize()
            store.upsert_daily_bars(
                [
                    DailyBar(date(2026, 6, 1), "000001.SZ", 10, 10, 10, 10, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 2), "000001.SZ", 9, 9, 9, 9, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 3), "000001.SZ", 20, 20, 20, 20, 9, 100, 100_000_000),
                    DailyBar(date(2026, 6, 1), "000002.SZ", 10, 10, 10, 10, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 2), "000002.SZ", 9, 9, 9, 9, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 3), "000002.SZ", 20, 20, 20, 20, 9, 100, 100_000_000),
                    DailyBar(date(2026, 6, 1), "000003.SZ", 10, 10, 10, 10, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 2), "000003.SZ", 9, 9, 9, 9, 10, 100, 100_000_000),
                    DailyBar(date(2026, 6, 3), "000003.SZ", 20, 20, 20, 20, 9, 100, 100_000_000),
                ]
            )

            report = build_market_risk_report(store, date(2026, 6, 2))

            self.assertEqual(report["tradeDate"], "2026-06-02")
            self.assertEqual(report["market"]["upCount"], 0)
            self.assertEqual(report["risk"]["state"], "PauseBuy")
