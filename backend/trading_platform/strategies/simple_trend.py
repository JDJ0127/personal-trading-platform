from __future__ import annotations

from datetime import date

from trading_platform.backtest.portfolio import Portfolio
from trading_platform.models import DailyBar, Signal, SignalType


class SimpleTrendStrategy:
    """Small MVP strategy used to prove the backtest pipeline works."""

    name = "simple_trend_v0"

    def __init__(self, lookback: int = 3, target_weight: float = 0.12, max_positions: int = 5) -> None:
        self.lookback = lookback
        self.target_weight = target_weight
        self.max_positions = max_positions

    def generate_signals(
        self,
        trade_date: date,
        bars_by_code: dict[str, DailyBar],
        history_by_code: dict[str, list[DailyBar]],
        portfolio: Portfolio,
    ) -> list[Signal]:
        signals: list[Signal] = []

        for ts_code, position in list(portfolio.positions.items()):
            history = history_by_code.get(ts_code, [])
            bar = bars_by_code.get(ts_code)
            if not bar or len(history) < self.lookback:
                continue
            moving_average = sum(item.close for item in history[-self.lookback:]) / self.lookback
            if bar.close < moving_average:
                signals.append(
                    Signal(
                        signal_date=trade_date,
                        trade_date=trade_date,
                        ts_code=ts_code,
                        signal_type=SignalType.SELL,
                        score=0,
                        target_weight=0,
                        reason=f"close below {self.lookback} day moving average",
                    )
                )

        open_slots = max(0, self.max_positions - len(portfolio.positions))
        if open_slots == 0:
            return signals

        ranked: list[tuple[float, str, DailyBar]] = []
        for ts_code, bar in bars_by_code.items():
            if ts_code in portfolio.positions:
                continue
            history = history_by_code.get(ts_code, [])
            if len(history) < self.lookback:
                continue
            previous_close = history[-1].close
            moving_average = sum(item.close for item in history[-self.lookback:]) / self.lookback
            momentum = bar.close / previous_close - 1
            if bar.close > moving_average and momentum > 0:
                ranked.append((momentum, ts_code, bar))

        for momentum, ts_code, _bar in sorted(ranked, reverse=True)[:open_slots]:
            score = min(100.0, 70.0 + momentum * 1000)
            signals.append(
                Signal(
                    signal_date=trade_date,
                    trade_date=trade_date,
                    ts_code=ts_code,
                    signal_type=SignalType.BUY,
                    score=score,
                    target_weight=self.target_weight,
                    reason=f"price above {self.lookback} day moving average with positive momentum",
                )
            )

        return signals

