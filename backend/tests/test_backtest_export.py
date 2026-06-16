from pathlib import Path
from unittest import TestCase

from trading_platform.backtest.engine import BacktestEngine
from trading_platform.backtest.export import build_frontend_backtest_report
from trading_platform.config import DEFAULT_CONFIG
from trading_platform.data.csv_provider import CsvDataProvider
from trading_platform.strategies.simple_trend import SimpleTrendStrategy


class BacktestExportTest(TestCase):
    def test_frontend_report_contains_required_sections(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "sample_data"
        bars = CsvDataProvider(data_dir).load_daily_bars()
        result = BacktestEngine(bars, SimpleTrendStrategy()).run()

        report = build_frontend_backtest_report(result, DEFAULT_CONFIG)

        self.assertEqual(report["schemaVersion"], 1)
        self.assertIn("cards", report)
        self.assertIn("equityCurve", report)
        self.assertIn("drawdownCurve", report)
        self.assertEqual(len(report["equityCurve"]), len(result.snapshots))
        self.assertEqual(report["metrics"]["fillCount"], result.fill_count)
