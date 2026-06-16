from __future__ import annotations

from collections import defaultdict
from typing import Protocol
from datetime import datetime

from trading_platform.backtest.broker import SimulatedBroker
from trading_platform.backtest.portfolio import Portfolio
from trading_platform.config import DEFAULT_CONFIG, TradingConfig
from trading_platform.models import BacktestResult, DailyBar, Fill, Order, PortfolioSnapshot, Signal, SignalType, Side


class Strategy(Protocol):
    name: str

    def generate_signals(
        self,
        trade_date: object,
        bars_by_code: dict[str, DailyBar],
        history_by_code: dict[str, list[DailyBar]],
        portfolio: Portfolio,
    ) -> list[Signal]:
        ...


class BacktestEngine:
    def __init__(
        self,
        bars: list[DailyBar],
        strategy: Strategy,
        broker: SimulatedBroker | None = None,
        config: TradingConfig = DEFAULT_CONFIG,
    ) -> None:
        self.bars = sorted(bars, key=lambda item: (item.trade_date, item.ts_code))
        self.strategy = strategy
        self.config = config
        self.broker = broker or SimulatedBroker(config)

    def run(self) -> BacktestResult:
        started_at = datetime.now()
        portfolio = Portfolio(self.config.initial_cash)
        snapshots: list[PortfolioSnapshot] = []
        orders: list[Order] = []
        fills: list[Fill] = []
        equity_peak = self.config.initial_cash
        max_drawdown = 0.0
        previous_asset = self.config.initial_cash
        history_by_code: dict[str, list[DailyBar]] = defaultdict(list)
        pending_signals: list[Signal] = []

        for trade_date, day_bars in self._group_by_date().items():
            bars_by_code = {bar.ts_code: bar for bar in day_bars}
            portfolio.start_new_day()
            portfolio.mark_to_market({code: bar.open for code, bar in bars_by_code.items()})

            for signal in pending_signals:
                bar = bars_by_code.get(signal.ts_code)
                if not bar:
                    continue
                order = self._signal_to_order(signal, bar, portfolio, trade_date)
                if not order:
                    continue
                available_qty = portfolio.positions.get(order.ts_code).available_quantity if order.ts_code in portfolio.positions else 0
                order, fill = self.broker.execute(order, bar, portfolio.cash, available_qty)
                orders.append(order)
                if fill:
                    portfolio.apply_fill(fill)
                    fills.append(fill)

            portfolio.mark_to_market({code: bar.close for code, bar in bars_by_code.items()})
            pending_signals = self.strategy.generate_signals(trade_date, bars_by_code, history_by_code, portfolio)
            equity_peak = max(equity_peak, portfolio.total_asset)
            drawdown = 0.0 if equity_peak == 0 else (equity_peak - portfolio.total_asset) / equity_peak
            max_drawdown = max(max_drawdown, drawdown)
            daily_return = 0.0 if previous_asset == 0 else portfolio.total_asset / previous_asset - 1
            previous_asset = portfolio.total_asset
            snapshots.append(
                PortfolioSnapshot(
                    trade_date=trade_date,  # type: ignore[arg-type]
                    total_asset=portfolio.total_asset,
                    cash=portfolio.cash,
                    market_value=portfolio.market_value,
                    daily_return=daily_return,
                    cumulative_return=portfolio.total_asset / self.config.initial_cash - 1,
                    drawdown=drawdown,
                    max_drawdown=max_drawdown,
                    position_count=len(portfolio.positions),
                    total_weight=portfolio.total_weight,
                )
            )

            for bar in day_bars:
                history_by_code[bar.ts_code].append(bar)

        final_asset = snapshots[-1].total_asset if snapshots else self.config.initial_cash
        winning_trades = sum(1 for pnl in portfolio.realized_pnls if pnl > 0)
        win_rate = winning_trades / len(portfolio.realized_pnls) if portfolio.realized_pnls else 0.0
        return BacktestResult(
            strategy_name=self.strategy.name,
            started_at=started_at,
            ended_at=datetime.now(),
            initial_cash=self.config.initial_cash,
            final_asset=final_asset,
            cumulative_return=final_asset / self.config.initial_cash - 1,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            order_count=len(orders),
            fill_count=len(fills),
            snapshots=snapshots,
            orders=orders,
            fills=fills,
            realized_pnls=portfolio.realized_pnls,
        )

    def _signal_to_order(self, signal: Signal, bar: DailyBar, portfolio: Portfolio, execution_date: object) -> Order | None:
        if signal.signal_type == SignalType.HOLD:
            return None
        if signal.signal_type == SignalType.SELL:
            position = portfolio.positions.get(signal.ts_code)
            if not position:
                return None
            return self.broker.create_order(execution_date, signal.ts_code, Side.SELL, bar.open, position.available_quantity)

        target_value = min(signal.target_weight, self.config.max_position_weight) * portfolio.total_asset
        current_value = portfolio.positions.get(signal.ts_code).market_value if signal.ts_code in portfolio.positions else 0.0
        buy_value = max(0.0, target_value - current_value)
        if buy_value <= 0:
            return None
        quantity = int(buy_value / bar.open / self.config.lot_size) * self.config.lot_size
        return self.broker.create_order(execution_date, signal.ts_code, Side.BUY, bar.open, quantity)

    def _group_by_date(self) -> dict[object, list[DailyBar]]:
        grouped: dict[object, list[DailyBar]] = {}
        for bar in self.bars:
            grouped.setdefault(bar.trade_date, []).append(bar)
        return grouped
