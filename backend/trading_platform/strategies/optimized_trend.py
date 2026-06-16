from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from trading_platform.backtest.portfolio import Portfolio
from trading_platform.models import DailyBar, Signal, SignalType


@dataclass(frozen=True)
class TrendCandidate:
    ts_code: str
    score: float
    momentum_5d: float
    trend_gap: float


class OptimizedTrendStrategy:
    """Cost-aware trend strategy used for real-data validation."""

    name = "optimized_trend_v1"

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        target_weight: float = 0.10,
        max_positions: int = 5,
        stop_loss: float = 0.08,
        trailing_stop: float = 0.10,
        profit_trigger: float = 0.12,
        market_breadth_min: float = 0.45,
        min_momentum_5d: float = 0.01,
        max_daily_chase: float = 0.055,
        cooldown_days: int = 5,
    ) -> None:
        self.short_window = short_window
        self.long_window = long_window
        self.target_weight = target_weight
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop
        self.profit_trigger = profit_trigger
        self.market_breadth_min = market_breadth_min
        self.min_momentum_5d = min_momentum_5d
        self.max_daily_chase = max_daily_chase
        self.cooldown_days = cooldown_days
        self.cooldowns: dict[str, int] = {}

    def generate_signals(
        self,
        trade_date: date,
        bars_by_code: dict[str, DailyBar],
        history_by_code: dict[str, list[DailyBar]],
        portfolio: Portfolio,
    ) -> list[Signal]:
        self._decay_cooldowns()
        signals: list[Signal] = []
        market_breadth = self._market_breadth(bars_by_code, history_by_code)
        allow_new_buy = market_breadth >= self.market_breadth_min

        for ts_code, position in list(portfolio.positions.items()):
            history = history_by_code.get(ts_code, [])
            bar = bars_by_code.get(ts_code)
            if not bar or len(history) < self.long_window:
                continue

            close_history = [item.close for item in history]
            ma_short = _average(close_history[-self.short_window :])
            ma_long = _average(close_history[-self.long_window :])
            highest_recent = max(close_history[-self.long_window :])
            pnl = bar.close / position.cost_price - 1
            drawdown_from_high = bar.close / highest_recent - 1 if highest_recent > 0 else 0
            sell_reason = ""

            if pnl <= -self.stop_loss:
                sell_reason = f"stop loss {pnl:.2%}"
            elif pnl >= self.profit_trigger and drawdown_from_high <= -self.trailing_stop:
                sell_reason = f"profit protection drawdown {drawdown_from_high:.2%}"
            elif bar.close < ma_long:
                sell_reason = f"close below {self.long_window} day moving average"
            elif not allow_new_buy and bar.close < ma_short:
                sell_reason = "market weak and close below short moving average"

            if sell_reason:
                self.cooldowns[ts_code] = self.cooldown_days
                signals.append(
                    Signal(
                        signal_date=trade_date,
                        trade_date=trade_date,
                        ts_code=ts_code,
                        signal_type=SignalType.SELL,
                        score=0,
                        target_weight=0,
                        reason=sell_reason,
                    )
                )

        open_slots = max(0, self.max_positions - len(portfolio.positions))
        if open_slots == 0 or not allow_new_buy:
            return signals

        candidates = self._rank_candidates(bars_by_code, history_by_code, portfolio)
        for candidate in candidates[:open_slots]:
            signals.append(
                Signal(
                    signal_date=trade_date,
                    trade_date=trade_date,
                    ts_code=candidate.ts_code,
                    signal_type=SignalType.BUY,
                    score=candidate.score,
                    target_weight=self.target_weight,
                    reason=(
                        f"trend confirmed; breadth {market_breadth:.0%}; "
                        f"5d momentum {candidate.momentum_5d:.2%}"
                    ),
                )
            )

        return signals

    def _rank_candidates(
        self,
        bars_by_code: dict[str, DailyBar],
        history_by_code: dict[str, list[DailyBar]],
        portfolio: Portfolio,
    ) -> list[TrendCandidate]:
        candidates: list[TrendCandidate] = []
        for ts_code, bar in bars_by_code.items():
            if ts_code in portfolio.positions or self.cooldowns.get(ts_code, 0) > 0:
                continue
            history = history_by_code.get(ts_code, [])
            if len(history) < self.long_window:
                continue

            closes = [item.close for item in history]
            ma_short = _average(closes[-self.short_window :])
            ma_long = _average(closes[-self.long_window :])
            momentum_5d = bar.close / closes[-self.short_window] - 1
            daily_change = bar.close / bar.pre_close - 1 if bar.pre_close > 0 else 0
            recent_high = max(closes[-self.long_window :])

            if not (bar.close > ma_short > ma_long):
                continue
            if momentum_5d < self.min_momentum_5d:
                continue
            if daily_change > self.max_daily_chase:
                continue
            if bar.close < recent_high * 0.96:
                continue

            trend_gap = ma_short / ma_long - 1 if ma_long > 0 else 0
            score = min(100.0, 70 + momentum_5d * 450 + trend_gap * 300)
            candidates.append(TrendCandidate(ts_code, score, momentum_5d, trend_gap))

        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def _market_breadth(self, bars_by_code: dict[str, DailyBar], history_by_code: dict[str, list[DailyBar]]) -> float:
        tradable = 0
        passed = 0
        for ts_code, bar in bars_by_code.items():
            history = history_by_code.get(ts_code, [])
            if len(history) < self.long_window:
                continue
            ma_long = _average([item.close for item in history[-self.long_window :]])
            tradable += 1
            if bar.close > ma_long:
                passed += 1
        return passed / tradable if tradable else 0.0

    def _decay_cooldowns(self) -> None:
        for ts_code in list(self.cooldowns):
            self.cooldowns[ts_code] -= 1
            if self.cooldowns[ts_code] <= 0:
                del self.cooldowns[ts_code]


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
