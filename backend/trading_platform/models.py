from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class StrEnum(str, Enum):
    pass


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class SignalType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class StockBasic:
    ts_code: str
    symbol: str
    name: str
    exchange: str
    market: str
    list_date: date
    delist_date: date | None = None
    is_hs: str = ""
    status: str = "L"


@dataclass(frozen=True)
class DailyBar:
    trade_date: date
    ts_code: str
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    volume: float
    amount: float
    pct_chg: float = 0.0
    adj_factor: float = 1.0


@dataclass(frozen=True)
class LimitPrice:
    trade_date: date
    ts_code: str
    up_limit: float
    down_limit: float
    limit_type: str = "normal"


@dataclass(frozen=True)
class Suspension:
    trade_date: date
    ts_code: str
    suspend_type: str
    reason: str = ""


@dataclass(frozen=True)
class TradeCalendar:
    cal_date: date
    exchange: str
    is_open: bool
    pretrade_date: date | None = None


@dataclass(frozen=True)
class StockPoolEntry:
    trade_date: date
    ts_code: str
    name: str
    industry: str
    is_pass: bool
    filter_reasons: tuple[str, ...]
    listed_days: int
    close: float | None = None
    amount: float | None = None
    avg_amount: float | None = None


@dataclass(frozen=True)
class FactorValue:
    trade_date: date
    ts_code: str
    factor_name: str
    factor_value: float
    factor_score: float


@dataclass(frozen=True)
class Signal:
    signal_date: date
    trade_date: date
    ts_code: str
    signal_type: SignalType
    score: float
    target_weight: float
    reason: str


@dataclass(frozen=True)
class Order:
    order_id: str
    trade_date: date
    ts_code: str
    side: Side
    order_price: float
    order_quantity: int
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    status: OrderStatus = OrderStatus.SUBMITTED
    reject_reason: str = ""


@dataclass(frozen=True)
class Fill:
    trade_date: date
    ts_code: str
    side: Side
    quantity: int
    price: float
    commission: float
    stamp_tax: float
    transfer_fee: float

    @property
    def fee(self) -> float:
        return self.commission + self.stamp_tax + self.transfer_fee


@dataclass
class Position:
    ts_code: str
    quantity: int
    available_quantity: int
    cost_price: float
    market_price: float
    holding_days: int = 0

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.market_price - self.cost_price) * self.quantity


@dataclass(frozen=True)
class PortfolioSnapshot:
    trade_date: date
    total_asset: float
    cash: float
    market_value: float
    daily_return: float
    cumulative_return: float
    drawdown: float
    max_drawdown: float
    position_count: int
    total_weight: float


@dataclass(frozen=True)
class BacktestResult:
    strategy_name: str
    started_at: datetime
    ended_at: datetime
    initial_cash: float
    final_asset: float
    cumulative_return: float
    max_drawdown: float
    win_rate: float
    order_count: int
    fill_count: int
    snapshots: list[PortfolioSnapshot]
    orders: list[Order]
    fills: list[Fill]
    realized_pnls: list[float]
