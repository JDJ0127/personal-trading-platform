from datetime import date
from unittest import TestCase

from trading_platform.backtest.broker import SimulatedBroker
from trading_platform.config import TradingConfig
from trading_platform.models import DailyBar, LimitPrice, Side


class BrokerTest(TestCase):
    def test_broker_rejects_buy_at_up_limit(self) -> None:
        trade_date = date(2026, 6, 1)
        broker = SimulatedBroker(
            TradingConfig(),
            limit_prices={
                (trade_date, "300308.SZ"): LimitPrice(
                    trade_date=trade_date,
                    ts_code="300308.SZ",
                    up_limit=10.0,
                    down_limit=8.0,
                )
            },
        )
        bar = DailyBar(
            trade_date=trade_date,
            ts_code="300308.SZ",
            open=10.0,
            high=10.0,
            low=9.5,
            close=9.8,
            pre_close=9.0,
            volume=1000,
            amount=9800,
        )
        order = broker.create_order(trade_date, "300308.SZ", Side.BUY, 10.0, 100)

        result, fill = broker.execute(order, bar, available_cash=100_000, available_quantity=0)

        self.assertEqual(result.reject_reason, "up limit cannot buy")
        self.assertIsNone(fill)


    def test_broker_rejects_non_board_lot_buy(self) -> None:
        trade_date = date(2026, 6, 1)
        broker = SimulatedBroker(TradingConfig())
        bar = DailyBar(
            trade_date=trade_date,
            ts_code="300308.SZ",
            open=10.0,
            high=10.2,
            low=9.5,
            close=9.8,
            pre_close=9.0,
            volume=1000,
            amount=9800,
        )
        order = broker.create_order(trade_date, "300308.SZ", Side.BUY, 10.0, 50)

        result, fill = broker.execute(order, bar, available_cash=100_000, available_quantity=0)

        self.assertEqual(result.reject_reason, "buy quantity must be a board lot")
        self.assertIsNone(fill)
