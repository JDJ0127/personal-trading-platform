from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.data.status import build_data_status_report
from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import DailyBar, StockBasic, TradeCalendar


class DataStatusTest(TestCase):
    def test_build_data_status_report(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "test.sqlite")
            store.initialize()
            store.upsert_stock_basic(
                [
                    StockBasic(
                        ts_code="600030.SH",
                        symbol="600030",
                        name="中信证券",
                        exchange="SSE",
                        market="主板",
                        list_date=date(2003, 1, 6),
                    )
                ]
            )
            store.upsert_trade_calendar(
                [TradeCalendar(cal_date=date(2026, 6, 1), exchange="SSE", is_open=True)]
            )
            store.upsert_daily_bars(
                [
                    DailyBar(
                        trade_date=date(2026, 6, 1),
                        ts_code="600030.SH",
                        open=20,
                        high=20.5,
                        low=19.8,
                        close=20.2,
                        pre_close=19.9,
                        volume=5000,
                        amount=101000,
                    )
                ]
            )

            report = build_data_status_report(store, source_name="BaoStock")

        self.assertEqual(report["summary"]["latestTradeDate"], "2026-06-01")
        self.assertEqual(report["summary"]["latestCalendarDate"], "2026-06-01")
        self.assertEqual(report["summary"]["qualityIssueCount"], 0)
        self.assertGreaterEqual(report["summary"]["totalRecords"], 3)
        self.assertEqual(report["summary"]["stockCount"], 1)
        self.assertEqual(report["summary"]["barStockCount"], 1)
        self.assertEqual(report["summary"]["barTradeDayCount"], 1)
        self.assertEqual(report["summary"]["coverageRate"], 1.0)
        self.assertEqual(report["coverage"]["missingBarCount"], 0)
        sources = {table["table"]: table["source"] for table in report["tables"]}
        self.assertEqual(sources["daily_bar"], "BaoStock")

    def test_build_data_status_report_tracks_missing_daily_bar_coverage(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "test.sqlite")
            store.initialize()
            store.upsert_stock_basic(
                [
                    StockBasic("600030.SH", "600030", "中信证券", "SSE", "主板", date(2003, 1, 6)),
                    StockBasic("000001.SZ", "000001", "平安银行", "SZSE", "主板", date(1991, 4, 3)),
                ]
            )
            store.upsert_trade_calendar(
                [
                    TradeCalendar(cal_date=date(2026, 6, 1), exchange="SSE", is_open=True),
                    TradeCalendar(cal_date=date(2026, 6, 2), exchange="SSE", is_open=True),
                ]
            )
            store.upsert_daily_bars(
                [
                    DailyBar(date(2026, 6, 1), "600030.SH", 20, 20.5, 19.8, 20.2, 19.9, 5000, 101000),
                    DailyBar(date(2026, 6, 1), "000001.SZ", 10, 10.2, 9.8, 10.1, 10, 5000, 51000),
                    DailyBar(date(2026, 6, 2), "600030.SH", 20.2, 20.5, 20, 20.4, 20.2, 5000, 102000),
                ]
            )

            report = build_data_status_report(store, source_name="BaoStock")

        self.assertEqual(report["coverage"]["expectedBarCount"], 4)
        self.assertEqual(report["coverage"]["actualBarCount"], 3)
        self.assertEqual(report["coverage"]["missingBarCount"], 1)
        self.assertEqual(report["coverage"]["coverageRate"], 0.75)
        self.assertEqual(report["coverage"]["missingByDate"][0]["tradeDate"], "2026-06-02")
        self.assertEqual(report["coverage"]["missingByDate"][0]["missingCodes"], ["000001.SZ"])
        self.assertEqual(report["coverage"]["missingByStock"][0]["tsCode"], "000001.SZ")
