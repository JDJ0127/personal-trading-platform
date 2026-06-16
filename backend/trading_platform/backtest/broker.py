from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from trading_platform.config import TradingConfig
from trading_platform.models import DailyBar, Fill, LimitPrice, Order, OrderStatus, Side


class SimulatedBroker:
    def __init__(
        self,
        config: TradingConfig,
        limit_prices: dict[tuple[object, str], LimitPrice] | None = None,
        suspended: set[tuple[object, str]] | None = None,
    ) -> None:
        self.config = config
        self.limit_prices = limit_prices or {}
        self.suspended = suspended or set()

    def create_order(self, trade_date: object, ts_code: str, side: Side, price: float, quantity: int) -> Order:
        return Order(
            order_id=uuid4().hex,
            trade_date=trade_date,  # type: ignore[arg-type]
            ts_code=ts_code,
            side=side,
            order_price=price,
            order_quantity=quantity,
        )

    def execute(self, order: Order, bar: DailyBar, available_cash: float, available_quantity: int) -> tuple[Order, Fill | None]:
        reject_reason = self._reject_reason(order, bar, available_cash, available_quantity)
        if reject_reason:
            return replace(order, status=OrderStatus.REJECTED, reject_reason=reject_reason), None

        fill_price = self._fill_price(order.side, bar.open)
        quantity = order.order_quantity
        fill = Fill(
            trade_date=bar.trade_date,
            ts_code=order.ts_code,
            side=order.side,
            quantity=quantity,
            price=fill_price,
            commission=self._commission(fill_price, quantity),
            stamp_tax=self._stamp_tax(order.side, fill_price, quantity),
            transfer_fee=self._transfer_fee(fill_price, quantity),
        )
        filled_order = replace(
            order,
            filled_quantity=quantity,
            avg_fill_price=fill_price,
            status=OrderStatus.FILLED,
        )
        return filled_order, fill

    def _reject_reason(self, order: Order, bar: DailyBar, available_cash: float, available_quantity: int) -> str:
        key = (bar.trade_date, order.ts_code)
        if key in self.suspended:
            return "suspended"
        if order.order_quantity <= 0:
            return "invalid quantity"
        if order.side == Side.BUY and order.order_quantity % self.config.lot_size != 0:
            return "buy quantity must be a board lot"

        limit = self.limit_prices.get(key)
        if limit and order.side == Side.BUY and bar.open >= limit.up_limit:
            return "up limit cannot buy"
        if limit and order.side == Side.SELL and bar.open <= limit.down_limit:
            return "down limit cannot sell"

        fill_price = self._fill_price(order.side, bar.open)
        estimated_fee = self._commission(fill_price, order.order_quantity) + self._transfer_fee(fill_price, order.order_quantity)
        if order.side == Side.BUY:
            required_cash = fill_price * order.order_quantity + estimated_fee
            if required_cash > available_cash:
                return "insufficient cash"
        if order.side == Side.SELL and order.order_quantity > available_quantity:
            return "T+1 available quantity exceeded"
        return ""

    def _fill_price(self, side: Side, base_price: float) -> float:
        slippage = self.config.slippage_bps / 10_000
        return base_price * (1 + slippage if side == Side.BUY else 1 - slippage)

    def _commission(self, price: float, quantity: int) -> float:
        return max(self.config.min_commission, price * quantity * self.config.commission_rate)

    def _stamp_tax(self, side: Side, price: float, quantity: int) -> float:
        if side != Side.SELL:
            return 0.0
        return price * quantity * self.config.stamp_tax_rate

    def _transfer_fee(self, price: float, quantity: int) -> float:
        return price * quantity * self.config.transfer_fee_rate

