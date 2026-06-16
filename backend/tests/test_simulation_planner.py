from datetime import date
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import DailyBar, LimitPrice, Signal, SignalType, Suspension
from trading_platform.simulation.planner import build_order_plan, build_simulation_report


class SimulationPlannerTest(TestCase):
    def test_build_simulation_report_blocks_untradable_orders(self) -> None:
        trade_date = date(2026, 6, 4)
        signal_date = date(2026, 6, 3)
        with TemporaryDirectory() as temp_dir:
            store = SQLiteStore(f"{temp_dir}/simulation.sqlite")
            store.initialize()
            store.upsert_daily_bars(
                [
                    DailyBar(trade_date, "000001.SZ", 10, 10, 10, 10, 9, 100, 100_000_000),
                    DailyBar(trade_date, "000002.SZ", 11, 11, 11, 11, 10, 100, 100_000_000),
                    DailyBar(trade_date, "000003.SZ", 9, 9, 9, 9, 10, 100, 100_000_000),
                    DailyBar(trade_date, "000004.SZ", 8, 8, 8, 8, 8, 100, 100_000_000),
                ]
            )
            store.upsert_limit_prices(
                [
                    LimitPrice(trade_date, "000002.SZ", up_limit=11, down_limit=9),
                    LimitPrice(trade_date, "000003.SZ", up_limit=11, down_limit=9),
                ]
            )
            store.upsert_suspensions([Suspension(trade_date, "000004.SZ", "suspend", "停牌")])
            store.upsert_signals(
                [
                    Signal(signal_date, trade_date, "000001.SZ", SignalType.BUY, 72, 0.1, "buy"),
                    Signal(signal_date, trade_date, "000002.SZ", SignalType.BUY, 71, 0.1, "buy"),
                    Signal(signal_date, trade_date, "000003.SZ", SignalType.SELL, 70, 0, "sell"),
                    Signal(signal_date, trade_date, "000004.SZ", SignalType.BUY, 69, 0.1, "buy"),
                    Signal(signal_date, trade_date, "000005.SZ", SignalType.HOLD, 55, 0, "watch"),
                ]
            )

            report = build_simulation_report(store)

            by_code = {order["tsCode"]: order for order in report["orders"]}
            self.assertEqual(by_code["000001.SZ"]["status"], "planned")
            self.assertEqual(by_code["000002.SZ"]["blockReason"], "涨停无法买入")
            self.assertEqual(by_code["000003.SZ"]["blockReason"], "跌停无法卖出")
            self.assertEqual(by_code["000004.SZ"]["blockReason"], "停牌无法交易")
            self.assertEqual(by_code["000005.SZ"]["status"], "watch")
            self.assertEqual(report["summary"]["plannedOrderCount"], 1)
            self.assertEqual(report["summary"]["blockedOrderCount"], 3)

    def test_build_order_plan_blocks_buys_but_allows_sells_when_risk_pauses_buying(self) -> None:
        trade_date = date(2026, 6, 4)
        with TemporaryDirectory() as temp_dir:
            store = SQLiteStore(f"{temp_dir}/simulation.sqlite")
            store.initialize()
            store.upsert_daily_bars(
                [
                    DailyBar(trade_date, "000001.SZ", 10, 10, 9, 9, 10, 100, 100_000_000),
                    DailyBar(trade_date, "000002.SZ", 10, 10, 9, 9, 10, 100, 100_000_000),
                ]
            )
            store.upsert_signals(
                [
                    Signal(trade_date, trade_date, "000001.SZ", SignalType.BUY, 72, 0.1, "buy"),
                    Signal(trade_date, trade_date, "000002.SZ", SignalType.SELL, 70, 0, "sell"),
                ]
            )

            report = build_order_plan(
                store,
                trade_date,
                {
                    "cash": 90_000,
                    "marketValue": 10_000,
                    "totalAsset": 100_000,
                    "positions": {"000002.SZ": {"quantity": 1000, "availableQuantity": 1000, "marketValue": 10_000}},
                },
            )

            by_code = {order["tsCode"]: order for order in report["orders"]}
            self.assertEqual(report["risk"]["state"], "PauseBuy")
            self.assertEqual(by_code["000001.SZ"]["status"], "blocked")
            self.assertEqual(by_code["000001.SZ"]["blockReason"], "风控状态暂停新增买入")
            self.assertEqual(by_code["000002.SZ"]["status"], "planned")
            self.assertEqual(by_code["000002.SZ"]["orderQuantity"], 1000)

    def test_build_order_plan_adds_protective_stop_sell(self) -> None:
        trade_date = date(2026, 6, 4)
        with TemporaryDirectory() as temp_dir:
            store = SQLiteStore(f"{temp_dir}/simulation.sqlite")
            store.initialize()
            store.upsert_daily_bars([DailyBar(trade_date, "000001.SZ", 9, 9, 8.8, 8.9, 9.5, 100, 100_000_000)])

            report = build_order_plan(
                store,
                trade_date,
                {
                    "cash": 90_000,
                    "marketValue": 8_900,
                    "totalAsset": 98_900,
                    "positions": {
                        "000001.SZ": {
                            "quantity": 1000,
                            "availableQuantity": 1000,
                            "marketValue": 8_900,
                            "stopPrice": 9.2,
                            "unrealizedPnlPct": -0.11,
                        }
                    },
                },
            )

            self.assertEqual(len(report["orders"]), 1)
            self.assertEqual(report["orders"][0]["source"], "protective_stop")
            self.assertEqual(report["orders"][0]["status"], "planned")
            self.assertEqual(report["orders"][0]["side"], "sell")
            self.assertEqual(report["orders"][0]["orderQuantity"], 1000)
