from datetime import date
from unittest import TestCase

from trading_platform.models import DailyBar, StockBasic
from trading_platform.universe.stock_pool import StockPoolConfig, build_stock_pool, build_stock_pool_report


class StockPoolTest(TestCase):
    def test_build_stock_pool_filters_basic_rules(self) -> None:
        trade_date = date(2026, 6, 8)
        stocks = [
            StockBasic("600030.SH", "600030", "中信证券", "SSE", "主板", date(2003, 1, 6)),
            StockBasic("000001.SZ", "000001", "平安银行", "SZSE", "主板", date(2026, 5, 20)),
            StockBasic("600001.SH", "600001", "ST样例", "SSE", "主板", date(2000, 1, 1)),
        ]
        bars = [
            DailyBar(date(2026, 6, 6), "600030.SH", 20, 20.5, 19.8, 20.2, 19.9, 100, 120_000_000),
            DailyBar(date(2026, 6, 7), "600030.SH", 20.2, 20.8, 20.1, 20.6, 20.2, 100, 130_000_000),
            DailyBar(trade_date, "600030.SH", 20.6, 21, 20.4, 20.8, 20.6, 100, 140_000_000),
            DailyBar(trade_date, "000001.SZ", 10, 10.2, 9.9, 10.1, 10, 100, 150_000_000),
            DailyBar(trade_date, "600001.SH", 8, 8.1, 7.9, 8, 8, 100, 150_000_000),
        ]

        entries = build_stock_pool(
            stock_basic=stocks,
            bars=bars,
            suspended={(trade_date, "600001.SH")},
            down_limits={},
            trade_date=trade_date,
            config=StockPoolConfig(min_listed_days=60, min_avg_amount=100_000_000, min_history_days=1),
        )

        by_code = {entry.ts_code: entry for entry in entries}
        self.assertTrue(by_code["600030.SH"].is_pass)
        self.assertFalse(by_code["000001.SZ"].is_pass)
        self.assertIn("上市不足60天", by_code["000001.SZ"].filter_reasons)
        self.assertFalse(by_code["600001.SH"].is_pass)
        self.assertIn("ST或退市风险", by_code["600001.SH"].filter_reasons)
        self.assertIn("当日停牌", by_code["600001.SH"].filter_reasons)

    def test_build_stock_pool_report_counts_reasons(self) -> None:
        trade_date = date(2026, 6, 8)
        entries = build_stock_pool(
            stock_basic=[StockBasic("000001.SZ", "000001", "平安银行", "SZSE", "主板", date(2026, 5, 20))],
            bars=[DailyBar(trade_date, "000001.SZ", 10, 10.2, 9.9, 10.1, 10, 100, 150_000_000)],
            suspended=set(),
            down_limits={},
            trade_date=trade_date,
            config=StockPoolConfig(min_listed_days=60, min_avg_amount=100_000_000, min_history_days=1),
        )

        report = build_stock_pool_report(entries)

        self.assertEqual(report["summary"]["total"], 1)
        self.assertEqual(report["summary"]["blocked"], 1)
        self.assertEqual(report["filters"][0]["reason"], "上市不足60天")
