from datetime import date, datetime
from unittest import TestCase

from trading_platform.backtest.stability import build_stability_report
from trading_platform.models import BacktestResult, PortfolioSnapshot


class BacktestStabilityTest(TestCase):
    def test_build_stability_report_groups_months_and_years(self) -> None:
        result = BacktestResult(
            strategy_name="test_strategy",
            started_at=datetime(2026, 1, 1),
            ended_at=datetime(2026, 3, 1),
            initial_cash=100_000,
            final_asset=102_000,
            cumulative_return=0.02,
            max_drawdown=0.03,
            win_rate=0.5,
            order_count=12,
            fill_count=12,
            snapshots=[
                PortfolioSnapshot(date(2026, 1, 2), 100_000, 100_000, 0, 0, 0, 0, 0, 0, 0),
                PortfolioSnapshot(date(2026, 1, 31), 103_000, 80_000, 23_000, 0.03, 0.03, 0, 0, 1, 0.23),
                PortfolioSnapshot(date(2026, 2, 28), 102_000, 90_000, 12_000, -0.0097, 0.02, 0.03, 0.03, 1, 0.12),
            ],
            orders=[],
            fills=[],
            realized_pnls=[],
        )

        report = build_stability_report(result)

        self.assertEqual(report["schemaVersion"], 1)
        self.assertEqual(report["period"]["tradingDays"], 3)
        self.assertEqual(len(report["monthlyReturns"]), 2)
        self.assertEqual(len(report["yearlyReturns"]), 1)
        self.assertEqual(report["summary"]["winningMonthCount"], 1)
        self.assertEqual(report["summary"]["losingMonthCount"], 1)
        self.assertEqual(report["summary"]["maxConsecutiveLosingMonths"], 1)
        self.assertTrue(report["checks"][1]["passed"])
