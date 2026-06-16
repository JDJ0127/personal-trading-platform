from datetime import date, timedelta
from unittest import TestCase

from trading_platform.backtest.portfolio import Portfolio
from trading_platform.models import DailyBar, Position, SignalType
from trading_platform.strategies.optimized_trend import OptimizedTrendStrategy


def make_history(ts_code: str, start_price: float, step: float, days: int = 25) -> list[DailyBar]:
    start = date(2026, 1, 1)
    rows = []
    previous = start_price
    for index in range(days):
        close = start_price + step * index
        rows.append(
            DailyBar(
                trade_date=start + timedelta(days=index),
                ts_code=ts_code,
                open=close,
                high=close,
                low=close,
                close=close,
                pre_close=previous,
                volume=1000,
                amount=1_000_000,
            )
        )
        previous = close
    return rows


class OptimizedTrendStrategyTest(TestCase):
    def test_does_not_buy_when_market_breadth_is_weak(self) -> None:
        strategy = OptimizedTrendStrategy(market_breadth_min=0.6)
        history_by_code = {
            "000001.SZ": make_history("000001.SZ", 20, -0.1),
            "000002.SZ": make_history("000002.SZ", 30, -0.1),
        }
        bars_by_code = {code: rows[-1] for code, rows in history_by_code.items()}

        signals = strategy.generate_signals(date(2026, 2, 1), bars_by_code, history_by_code, Portfolio(100_000))

        self.assertEqual(signals, [])

    def test_buys_confirmed_trend_candidate(self) -> None:
        strategy = OptimizedTrendStrategy(market_breadth_min=0.1)
        history_by_code = {"300308.SZ": make_history("300308.SZ", 10, 0.2)}
        bars_by_code = {"300308.SZ": history_by_code["300308.SZ"][-1]}

        signals = strategy.generate_signals(date(2026, 2, 1), bars_by_code, history_by_code, Portfolio(100_000))

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, SignalType.BUY)
        self.assertEqual(signals[0].ts_code, "300308.SZ")

    def test_sells_when_close_breaks_long_average(self) -> None:
        strategy = OptimizedTrendStrategy()
        history = make_history("600030.SH", 20, 0.1)
        weak_bar = DailyBar(date(2026, 2, 1), "600030.SH", 18, 18, 18, 18, 22, 1000, 1_000_000)
        portfolio = Portfolio(100_000)
        portfolio.positions["600030.SH"] = Position("600030.SH", 100, 100, 20, 18, holding_days=10)

        signals = strategy.generate_signals(date(2026, 2, 1), {"600030.SH": weak_bar}, {"600030.SH": history}, portfolio)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, SignalType.SELL)
