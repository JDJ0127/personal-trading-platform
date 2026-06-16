from pathlib import Path
from unittest import TestCase

from trading_platform.backtest.engine import BacktestEngine
from trading_platform.data.csv_provider import CsvDataProvider
from trading_platform.strategies.simple_trend import SimpleTrendStrategy


class BacktestEngineTest(TestCase):
    def test_backtest_engine_runs_sample_data(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "sample_data"
        bars = CsvDataProvider(data_dir).load_daily_bars()
        engine = BacktestEngine(bars, SimpleTrendStrategy())

        result = engine.run()

        self.assertTrue(result.snapshots)
        self.assertEqual(result.initial_cash, 500_000)
        self.assertGreater(result.final_asset, 0)
        self.assertGreaterEqual(result.order_count, result.fill_count)
