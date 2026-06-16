from datetime import date, datetime
from unittest import TestCase

from trading_platform.backtest.portfolio_report import build_portfolio_report
from trading_platform.models import BacktestResult, DailyBar, Fill, PortfolioSnapshot, Side, StockBasic


class PortfolioReportTest(TestCase):
    def test_build_portfolio_report_replays_open_positions(self) -> None:
        result = BacktestResult(
            strategy_name="test",
            started_at=datetime(2026, 1, 1),
            ended_at=datetime(2026, 1, 3),
            initial_cash=100_000,
            final_asset=101_000,
            cumulative_return=0.01,
            max_drawdown=0.02,
            win_rate=0,
            order_count=1,
            fill_count=1,
            snapshots=[
                PortfolioSnapshot(date(2026, 1, 3), 101_000, 89_995, 11_005, 0.01, 0.01, 0, 0.02, 1, 0.10896)
            ],
            orders=[],
            fills=[Fill(date(2026, 1, 2), "600030.SH", Side.BUY, 500, 20.0, 5.0, 0.0, 0.0)],
            realized_pnls=[],
        )
        bars = [
            DailyBar(date(2026, 1, 2), "600030.SH", 20, 21, 19, 20, 19.8, 1000, 20_000),
            DailyBar(date(2026, 1, 3), "600030.SH", 21, 22, 20, 22, 20, 1000, 22_000),
        ]
        stocks = [StockBasic("600030.SH", "600030", "中信证券", "SSE", "非银金融", date(2003, 1, 6))]

        report = build_portfolio_report(result, bars, stocks)

        self.assertEqual(report["account"]["positionCount"], 1)
        self.assertEqual(report["positions"][0]["name"], "中信证券")
        self.assertEqual(report["positions"][0]["quantity"], 500)
        self.assertGreater(report["positions"][0]["unrealizedPnl"], 0)
        self.assertEqual(report["industryExposure"][0]["industry"], "现金")
