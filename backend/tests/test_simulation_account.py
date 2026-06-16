from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import BacktestResult, DailyBar, Fill, Order, PortfolioSnapshot, Side, Signal, SignalType, StockBasic
from trading_platform.simulation.account import persist_backtest_account, run_daily_simulation, write_simulation_account_report


class SimulationAccountTest(TestCase):
    def test_persist_backtest_account_writes_snapshot_tables_and_json(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "simulation.sqlite")
            result = BacktestResult(
                strategy_name="test_strategy",
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
                    PortfolioSnapshot(date(2026, 1, 2), 99_995, 89_995, 10_000, -0.00005, -0.00005, 0.00005, 0.00005, 1, 0.1),
                    PortfolioSnapshot(date(2026, 1, 3), 101_000, 89_995, 11_005, 0.01005, 0.01, 0, 0.02, 1, 0.10896),
                ],
                orders=[Order("order-1", date(2026, 1, 2), "600030.SH", Side.BUY, 20.0, 500, 500, 20.0)],
                fills=[Fill(date(2026, 1, 2), "600030.SH", Side.BUY, 500, 20.0, 5.0, 0.0, 0.0)],
                realized_pnls=[],
            )
            bars = [
                DailyBar(date(2026, 1, 2), "600030.SH", 20, 21, 19, 20, 19.8, 1000, 20_000),
                DailyBar(date(2026, 1, 3), "600030.SH", 21, 22, 20, 22, 20, 1000, 22_000),
            ]
            stocks = [StockBasic("600030.SH", "600030", "中信证券", "SSE", "非银金融", date(2003, 1, 6))]

            report = persist_backtest_account(store, result, bars, stocks)
            output = Path(tmpdir) / "simulationAccount.json"
            exported = write_simulation_account_report(store, "paper-main", output)

            self.assertEqual(report["account"]["accountId"], "paper-main")
            self.assertEqual(report["account"]["strategyName"], "test_strategy")
            self.assertEqual(report["summary"]["positionCount"], 1)
            self.assertEqual(report["summary"]["fillCount"], 1)
            self.assertEqual(report["summary"]["equityPointCount"], 2)
            self.assertEqual(report["positions"][0]["name"], "中信证券")
            self.assertTrue(output.exists())
            self.assertEqual(exported["orders"][0]["orderId"], "order-1")

    def test_run_daily_simulation_executes_signal_and_updates_account(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "daily.sqlite")
            store.initialize()
            store.upsert_stock_basic([StockBasic("600030.SH", "600030", "中信证券", "SSE", "非银金融", date(2003, 1, 6))])
            store.upsert_daily_bars(
                [
                    DailyBar(date(2026, 1, 5), "600030.SH", 20, 21, 19, 20.5, 20, 1000, 20_500),
                ]
            )
            store.upsert_signals(
                [
                    Signal(
                        signal_date=date(2026, 1, 5),
                        trade_date=date(2026, 1, 5),
                        ts_code="600030.SH",
                        signal_type=SignalType.BUY,
                        score=70,
                        target_weight=0.1,
                        reason="测试买入",
                    )
                ]
            )

            report = run_daily_simulation(store, date(2026, 1, 5), output=Path(tmpdir) / "account.json")

            self.assertEqual(report["account"]["lastTradeDate"], "2026-01-05")
            self.assertEqual(report["summary"]["orderCount"], 1)
            self.assertEqual(report["summary"]["fillCount"], 1)
            self.assertEqual(report["summary"]["positionCount"], 1)
            self.assertEqual(report["summary"]["equityPointCount"], 1)
            self.assertEqual(report["positions"][0]["tsCode"], "600030.SH")
            self.assertGreater(report["positions"][0]["quantity"], 0)

    def test_run_daily_simulation_does_not_execute_buy_when_risk_pauses_buying(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "daily.sqlite")
            store.initialize()
            store.upsert_stock_basic([StockBasic("600030.SH", "600030", "中信证券", "SSE", "非银金融", date(2003, 1, 6))])
            store.upsert_daily_bars(
                [
                    DailyBar(date(2026, 1, 5), "600030.SH", 20, 20, 18, 18, 20, 1000, 18_000),
                    DailyBar(date(2026, 1, 5), "300308.SZ", 100, 100, 90, 90, 100, 1000, 90_000),
                ]
            )
            store.upsert_signals(
                [
                    Signal(
                        signal_date=date(2026, 1, 5),
                        trade_date=date(2026, 1, 5),
                        ts_code="600030.SH",
                        signal_type=SignalType.BUY,
                        score=70,
                        target_weight=0.1,
                        reason="测试买入",
                    )
                ]
            )

            report = run_daily_simulation(store, date(2026, 1, 5), output=Path(tmpdir) / "account.json")

            self.assertEqual(report["summary"]["orderCount"], 0)
            self.assertEqual(report["summary"]["fillCount"], 0)
            self.assertEqual(report["summary"]["positionCount"], 0)
            self.assertEqual(report["account"]["totalAsset"], 500_000)

    def test_run_daily_simulation_executes_protective_stop_sell(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "daily.sqlite")
            store.initialize()
            with store.connect() as conn:
                conn.execute(
                    """
                    insert into simulation_account values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "paper-main",
                        "模拟盘主账户",
                        "paper",
                        "manual_signal",
                        100_000,
                        100_000,
                        90_000,
                        10_000,
                        0,
                        0,
                        1,
                        "2026-01-04",
                        "active",
                        "2026-01-04T15:00:00",
                        "2026-01-04T15:00:00",
                    ),
                )
                conn.execute(
                    """
                    insert into simulation_position values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "paper-main",
                        "2026-01-04",
                        "600030.SH",
                        "中信证券",
                        "非银金融",
                        500,
                        500,
                        20.0,
                        20.0,
                        10_000,
                        0.1,
                        0.0,
                        0.0,
                        18.4,
                        3,
                    ),
                )
            store.upsert_daily_bars([DailyBar(date(2026, 1, 5), "600030.SH", 18, 18.2, 17.8, 18.0, 20, 1000, 18_000)])

            report = run_daily_simulation(store, date(2026, 1, 5), output=Path(tmpdir) / "account.json")

            self.assertEqual(report["summary"]["fillCount"], 1)
            self.assertEqual(report["summary"]["positionCount"], 0)
            self.assertEqual(report["fills"][0]["side"], "sell")
