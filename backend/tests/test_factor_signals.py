from datetime import date
from unittest import TestCase

from trading_platform.models import DailyBar, StockPoolEntry
from trading_platform.strategies.factor_signals import generate_factor_values, generate_signals


class FactorSignalsTest(TestCase):
    def test_generate_factor_values_and_signals(self) -> None:
        trade_date = date(2026, 6, 3)
        entries = [
            StockPoolEntry(
                trade_date=trade_date,
                ts_code="300308.SZ",
                name="中际旭创",
                industry="创业板",
                is_pass=True,
                filter_reasons=(),
                listed_days=1000,
                close=110,
                amount=150_000_000,
                avg_amount=120_000_000,
            )
        ]
        bars = [
            DailyBar(date(2026, 6, 1), "300308.SZ", 100, 103, 99, 102, 100, 100, 110_000_000, pct_chg=2),
            DailyBar(date(2026, 6, 2), "300308.SZ", 102, 106, 101, 105, 102, 100, 120_000_000, pct_chg=3),
            DailyBar(trade_date, "300308.SZ", 105, 112, 104, 110, 105, 100, 150_000_000, pct_chg=4),
        ]

        factors = generate_factor_values(entries, bars, trade_date)
        signals = generate_signals(entries, factors, trade_date)

        self.assertEqual(len(factors), 4)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].ts_code, "300308.SZ")
        self.assertGreaterEqual(signals[0].score, 50)
