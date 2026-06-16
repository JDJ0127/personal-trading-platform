from __future__ import annotations

from trading_platform.models import Fill, Position, Side


class Portfolio:
    def __init__(self, initial_cash: float) -> None:
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.realized_pnls: list[float] = []

    def mark_to_market(self, prices: dict[str, float]) -> None:
        for ts_code, price in prices.items():
            if ts_code in self.positions:
                self.positions[ts_code].market_price = price

    @property
    def market_value(self) -> float:
        return sum(position.market_value for position in self.positions.values())

    @property
    def total_asset(self) -> float:
        return self.cash + self.market_value

    @property
    def total_weight(self) -> float:
        total = self.total_asset
        if total <= 0:
            return 0.0
        return self.market_value / total

    def start_new_day(self) -> None:
        for position in self.positions.values():
            position.available_quantity = position.quantity
            position.holding_days += 1

    def apply_fill(self, fill: Fill) -> None:
        gross = fill.quantity * fill.price
        if fill.side == Side.BUY:
            self.cash -= gross + fill.fee
            existing = self.positions.get(fill.ts_code)
            if existing:
                new_quantity = existing.quantity + fill.quantity
                new_cost = ((existing.cost_price * existing.quantity) + gross + fill.fee) / new_quantity
                existing.quantity = new_quantity
                existing.cost_price = new_cost
                existing.market_price = fill.price
            else:
                self.positions[fill.ts_code] = Position(
                    ts_code=fill.ts_code,
                    quantity=fill.quantity,
                    available_quantity=0,
                    cost_price=(gross + fill.fee) / fill.quantity,
                    market_price=fill.price,
                    holding_days=0,
                )
            return

        position = self.positions[fill.ts_code]
        sell_quantity = min(fill.quantity, position.quantity)
        realized = (fill.price - position.cost_price) * sell_quantity - fill.fee
        self.realized_pnls.append(realized)
        self.cash += gross - fill.fee
        position.quantity -= sell_quantity
        position.available_quantity = max(0, position.available_quantity - sell_quantity)
        position.market_price = fill.price
        if position.quantity == 0:
            del self.positions[fill.ts_code]

