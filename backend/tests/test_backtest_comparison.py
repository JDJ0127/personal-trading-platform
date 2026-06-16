from unittest import TestCase

from trading_platform.backtest.comparison import build_strategy_comparison


class BacktestComparisonTest(TestCase):
    def test_build_strategy_comparison_marks_improvements(self) -> None:
        baseline = {
            "strategy": "simple",
            "period": {"start": "2024-01-01", "end": "2024-12-31", "tradingDays": 242},
            "summary": {
                "cumulativeReturn": -0.07,
                "maxDrawdown": 0.13,
                "winRate": 0.32,
                "monthlyWinRate": 0.33,
                "fillCount": 500,
                "maxConsecutiveLosingMonths": 3,
            },
        }
        optimized = {
            "strategy": "optimized",
            "period": {"start": "2024-01-01", "end": "2024-12-31", "tradingDays": 242},
            "summary": {
                "cumulativeReturn": 0.05,
                "maxDrawdown": 0.10,
                "winRate": 0.30,
                "monthlyWinRate": 0.58,
                "fillCount": 150,
                "maxConsecutiveLosingMonths": 2,
            },
        }

        report = build_strategy_comparison(baseline, optimized)

        self.assertEqual(report["verdict"], "优化有效，进入更大样本验证")
        self.assertTrue(report["metrics"][0]["improved"])
        self.assertTrue(report["metrics"][1]["improved"])
