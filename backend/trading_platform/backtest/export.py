from __future__ import annotations

from math import sqrt
from typing import Any

from trading_platform.config import TradingConfig
from trading_platform.models import BacktestResult, Fill, Order, PortfolioSnapshot


def build_frontend_backtest_report(result: BacktestResult, config: TradingConfig) -> dict[str, Any]:
    annualized_return = _annualized_return(result.snapshots)
    sharpe_ratio = _sharpe_ratio(result.snapshots)
    calmar_ratio = annualized_return / result.max_drawdown if result.max_drawdown > 0 else None
    total_fee = sum(fill.fee for fill in result.fills)
    turnover = sum(fill.quantity * fill.price for fill in result.fills)
    trading_cost_ratio = total_fee / turnover if turnover > 0 else 0.0
    profit_loss_ratio = _profit_loss_ratio(result.realized_pnls)
    max_consecutive_losses = _max_consecutive_losses(result.realized_pnls)

    return {
        "schemaVersion": 1,
        "generatedAt": result.ended_at.isoformat(timespec="seconds"),
        "strategy": {
            "name": result.strategy_name,
            "startedAt": result.started_at.isoformat(timespec="seconds"),
            "endedAt": result.ended_at.isoformat(timespec="seconds"),
        },
        "parameters": {
            "initialCash": config.initial_cash,
            "maxDrawdownLimit": config.max_drawdown_limit,
            "maxPositions": config.max_positions,
            "minPositionWeight": config.min_position_weight,
            "maxPositionWeight": config.max_position_weight,
            "maxPortfolioWeight": config.max_portfolio_weight,
            "lotSize": config.lot_size,
            "commissionRate": config.commission_rate,
            "minCommission": config.min_commission,
            "stampTaxRate": config.stamp_tax_rate,
            "transferFeeRate": config.transfer_fee_rate,
            "slippageBps": config.slippage_bps,
        },
        "metrics": {
            "initialCash": _round_money(result.initial_cash),
            "finalAsset": _round_money(result.final_asset),
            "cumulativeReturn": _round_ratio(result.cumulative_return),
            "annualizedReturn": _round_ratio(annualized_return),
            "maxDrawdown": _round_ratio(result.max_drawdown),
            "sharpeRatio": _round_optional(sharpe_ratio),
            "calmarRatio": _round_optional(calmar_ratio),
            "winRate": _round_ratio(result.win_rate),
            "orderCount": result.order_count,
            "fillCount": result.fill_count,
            "totalFee": _round_money(total_fee),
            "turnover": _round_money(turnover),
            "tradingCostRatio": _round_ratio(trading_cost_ratio),
            "averageTradePnl": _round_money(sum(result.realized_pnls) / len(result.realized_pnls)) if result.realized_pnls else 0,
            "profitLossRatio": _round_optional(profit_loss_ratio),
            "maxConsecutiveLosses": max_consecutive_losses,
        },
        "cards": [
            _card("累计收益", _format_pct(result.cumulative_return), "up" if result.cumulative_return >= 0 else "down"),
            _card("年化收益", _format_optional_pct(annualized_return), "up" if annualized_return >= 0 else "down"),
            _card("最大回撤", _format_pct(result.max_drawdown), "down"),
            _card("夏普比率", _format_optional_number(sharpe_ratio), "flat"),
            _card("卡玛比率", _format_optional_number(calmar_ratio), "flat"),
            _card("胜率", _format_pct(result.win_rate), "flat"),
            _card("盈亏比", _format_optional_number(profit_loss_ratio), "flat"),
            _card("交易成本占比", _format_pct(trading_cost_ratio), "flat"),
            _card("订单/成交", f"{result.order_count}/{result.fill_count}", "flat"),
        ],
        "equityCurve": [_snapshot_to_equity_point(item, result.initial_cash) for item in result.snapshots],
        "drawdownCurve": [
            {"date": item.trade_date.isoformat(), "drawdown": _round_ratio(item.drawdown)}
            for item in result.snapshots
        ],
        "orders": [_order_to_dict(item) for item in result.orders],
        "fills": [_fill_to_dict(item) for item in result.fills],
        "realizedPnls": [_round_money(item) for item in result.realized_pnls],
    }


def _annualized_return(snapshots: list[PortfolioSnapshot]) -> float:
    if len(snapshots) < 2:
        return 0.0
    first = snapshots[0]
    last = snapshots[-1]
    trading_days = max(1, len(snapshots) - 1)
    if first.total_asset <= 0:
        return 0.0
    return (last.total_asset / first.total_asset) ** (252 / trading_days) - 1


def _sharpe_ratio(snapshots: list[PortfolioSnapshot]) -> float | None:
    returns = [item.daily_return for item in snapshots[1:]]
    if len(returns) < 2:
        return None
    average = sum(returns) / len(returns)
    variance = sum((item - average) ** 2 for item in returns) / (len(returns) - 1)
    stddev = variance ** 0.5
    if stddev == 0:
        return None
    return average / stddev * sqrt(252)


def _profit_loss_ratio(pnls: list[float]) -> float | None:
    wins = [item for item in pnls if item > 0]
    losses = [abs(item) for item in pnls if item < 0]
    if not wins or not losses:
        return None
    return (sum(wins) / len(wins)) / (sum(losses) / len(losses))


def _max_consecutive_losses(pnls: list[float]) -> int:
    longest = 0
    current = 0
    for pnl in pnls:
        if pnl < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _snapshot_to_equity_point(snapshot: PortfolioSnapshot, initial_cash: float) -> dict[str, Any]:
    net_value = snapshot.total_asset / initial_cash if initial_cash > 0 else 0.0
    return {
        "date": snapshot.trade_date.isoformat(),
        "strategyNetValue": round(net_value, 6),
        "totalAsset": _round_money(snapshot.total_asset),
        "cash": _round_money(snapshot.cash),
        "marketValue": _round_money(snapshot.market_value),
        "dailyReturn": _round_ratio(snapshot.daily_return),
        "cumulativeReturn": _round_ratio(snapshot.cumulative_return),
        "positionCount": snapshot.position_count,
        "totalWeight": _round_ratio(snapshot.total_weight),
    }


def _order_to_dict(order: Order) -> dict[str, Any]:
    return {
        "orderId": order.order_id,
        "tradeDate": order.trade_date.isoformat(),
        "tsCode": order.ts_code,
        "side": order.side.value,
        "orderPrice": _round_money(order.order_price),
        "orderQuantity": order.order_quantity,
        "filledQuantity": order.filled_quantity,
        "avgFillPrice": _round_money(order.avg_fill_price),
        "status": order.status.value,
        "rejectReason": order.reject_reason,
    }


def _fill_to_dict(fill: Fill) -> dict[str, Any]:
    return {
        "tradeDate": fill.trade_date.isoformat(),
        "tsCode": fill.ts_code,
        "side": fill.side.value,
        "quantity": fill.quantity,
        "price": _round_money(fill.price),
        "commission": _round_money(fill.commission),
        "stampTax": _round_money(fill.stamp_tax),
        "transferFee": _round_money(fill.transfer_fee),
        "fee": _round_money(fill.fee),
    }


def _card(label: str, value: str, tone: str) -> dict[str, str]:
    return {"label": label, "value": value, "tone": tone}


def _round_money(value: float) -> float:
    return round(value, 2)


def _round_ratio(value: float) -> float:
    return round(value, 6)


def _round_optional(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_optional_pct(value: float | None) -> str:
    return _format_pct(value) if value is not None else "--"


def _format_optional_number(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "--"
