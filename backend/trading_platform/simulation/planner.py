from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_platform.config import DEFAULT_CONFIG
from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import SignalType
from trading_platform.risk.market_risk import build_market_risk_report


def build_simulation_report(store: SQLiteStore, account_id: str = "paper-main", trade_date: Any | None = None) -> dict[str, Any]:
    plan = build_order_plan(store, trade_date, account=_load_account_state_from_store(store, account_id))
    latest_date = plan["tradeDate"]
    orders = plan["orders"]
    planned_count = sum(1 for order in orders if order["status"] == "planned")
    blocked_count = sum(1 for order in orders if order["status"] == "blocked")
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tradeDate": latest_date,
        "account": {
            "initialCash": DEFAULT_CONFIG.initial_cash,
            "maxPositions": DEFAULT_CONFIG.max_positions,
            "maxPortfolioWeight": DEFAULT_CONFIG.max_portfolio_weight,
            "currentTotalAsset": plan["account"]["totalAsset"],
            "currentCash": plan["account"]["cash"],
            "currentWeight": plan["account"]["totalWeight"],
        },
        "risk": plan["risk"],
        "summary": {
            "signalCount": len(orders),
            "plannedOrderCount": planned_count,
            "blockedOrderCount": blocked_count,
            "watchCount": sum(1 for order in orders if order["status"] == "watch"),
        },
        "orders": orders,
        "checks": [
            "停牌无法交易",
            "涨停无法买入",
            "跌停无法卖出",
            "买入按 100 股整数倍",
            "按市场风控状态限制新增买入",
            "按组合仓位上限限制新增买入",
            "按配置计入滑点和手续费",
        ],
    }


def build_order_plan(store: SQLiteStore, trade_date: Any | None = None, account: dict[str, Any] | None = None) -> dict[str, Any]:
    signals = store.load_signals()
    target_date = trade_date or max((signal.trade_date for signal in signals), default=None)
    latest_signals = [signal for signal in signals if signal.trade_date == target_date] if target_date else []
    limit_prices = store.load_limit_prices()
    suspended = store.load_suspensions()
    bars = {(bar.trade_date, bar.ts_code): bar for bar in store.load_daily_bars()}
    risk_report = build_market_risk_report(store, target_date)
    risk = risk_report["risk"]
    account_state = _normal_account_state(account)
    total_asset = account_state["totalAsset"]
    cash = account_state["cash"]
    current_market_value = account_state["marketValue"]
    current_positions = account_state["positions"]
    allowed_weight = min(DEFAULT_CONFIG.max_portfolio_weight, risk.get("allowedPositionWeight", DEFAULT_CONFIG.max_portfolio_weight))
    risk_state = risk.get("state", "Normal")
    new_buy_count = 0
    orders = []
    protected_sell_codes: set[str] = set()
    for order in _protective_sell_orders(target_date, bars, limit_prices, suspended, current_positions):
        orders.append(order)
        if order["status"] == "planned":
            protected_sell_codes.add(order["tsCode"])
            cash += order["estimatedAmount"]
            current_market_value = max(0.0, current_market_value - order["estimatedAmount"])
    for signal in latest_signals:
        if signal.ts_code in protected_sell_codes and signal.signal_type == SignalType.SELL:
            continue
        limit = limit_prices.get((signal.trade_date, signal.ts_code))
        bar = bars.get((signal.trade_date, signal.ts_code))
        if signal.signal_type == SignalType.HOLD:
            status = "watch"
            block_reason = "观察信号不生成模拟委托"
            quantity = 0
        elif (signal.trade_date, signal.ts_code) in suspended:
            status = "blocked"
            block_reason = "停牌无法交易"
            quantity = 0
        elif signal.signal_type == SignalType.BUY and risk_state in {"PauseBuy", "Stop"}:
            status = "blocked"
            block_reason = "风控状态暂停新增买入"
            quantity = 0
        elif signal.signal_type == SignalType.BUY and limit and bar and bar.close >= limit.up_limit:
            status = "blocked"
            block_reason = "涨停无法买入"
            quantity = 0
        elif signal.signal_type == SignalType.SELL and limit and bar and bar.close <= limit.down_limit:
            status = "blocked"
            block_reason = "跌停无法卖出"
            quantity = 0
        elif not bar:
            status = "blocked"
            block_reason = "缺少交易日行情"
            quantity = 0
        else:
            quantity, block_reason = _planned_quantity(
                signal=signal,
                bar=bar,
                cash=cash,
                total_asset=total_asset,
                current_market_value=current_market_value,
                current_positions=current_positions,
                allowed_weight=allowed_weight,
                risk_state=risk_state,
                new_buy_count=new_buy_count,
            )
            status = "planned" if quantity > 0 else "blocked"
            if status == "planned":
                estimated_value = quantity * bar.open
                if signal.signal_type == SignalType.BUY:
                    cash -= estimated_value
                    current_market_value += estimated_value
                    if signal.ts_code not in current_positions:
                        new_buy_count += 1
                else:
                    cash += estimated_value
                    current_market_value = max(0.0, current_market_value - estimated_value)
        estimated_amount = round(quantity * bar.open, 2) if bar else 0.0
        orders.append(
            {
                "tradeDate": signal.trade_date.isoformat(),
                "tsCode": signal.ts_code,
                "side": signal.signal_type.value,
                "targetWeight": signal.target_weight,
                "score": signal.score,
                "status": status,
                "blockReason": block_reason,
                "orderQuantity": quantity,
                "orderPrice": bar.open if bar else None,
                "estimatedAmount": estimated_amount,
                "upLimit": limit.up_limit if limit else None,
                "downLimit": limit.down_limit if limit else None,
            }
        )

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tradeDate": target_date.isoformat() if target_date else "--",
        "account": {
            "cash": round(account_state["cash"], 2),
            "marketValue": round(account_state["marketValue"], 2),
            "totalAsset": round(account_state["totalAsset"], 2),
            "totalWeight": round(account_state["totalWeight"], 6),
            "allowedWeight": round(allowed_weight, 6),
        },
        "risk": risk,
        "orders": orders,
    }


def write_simulation_report(
    store: SQLiteStore,
    output: str | Path,
    account_id: str = "paper-main",
    trade_date: Any | None = None,
) -> dict[str, Any]:
    report = build_simulation_report(store, account_id, trade_date)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _load_account_state_from_store(store: SQLiteStore, account_id: str) -> dict[str, Any] | None:
    store.initialize()
    with store.connect() as conn:
        account = conn.execute("select * from simulation_account where account_id = ?", (account_id,)).fetchone()
        if not account:
            return None
        positions = conn.execute("select * from simulation_position where account_id = ?", (account_id,)).fetchall()
    return {
        "cash": account["cash"],
        "marketValue": account["market_value"],
        "totalAsset": account["total_asset"],
        "positions": {
            row["ts_code"]: {
                "quantity": row["quantity"],
                "availableQuantity": row["available_quantity"],
                "marketValue": row["market_value"],
                "stopPrice": row["stop_price"],
                "unrealizedPnlPct": row["unrealized_pnl_pct"],
            }
            for row in positions
        },
    }


def _protective_sell_orders(
    trade_date: Any | None,
    bars: dict[tuple[Any, str], Any],
    limit_prices: dict[tuple[Any, str], Any],
    suspended: set[tuple[Any, str]],
    positions: dict[str, Any],
) -> list[dict[str, Any]]:
    if not trade_date:
        return []
    orders = []
    for ts_code, position in positions.items():
        bar = bars.get((trade_date, ts_code))
        if not bar:
            continue
        stop_price = float(position.get("stopPrice", 0.0))
        unrealized_pnl_pct = float(position.get("unrealizedPnlPct", 0.0))
        if not (stop_price > 0 and bar.close <= stop_price) and unrealized_pnl_pct > -0.08:
            continue
        limit = limit_prices.get((trade_date, ts_code))
        quantity = int(position.get("availableQuantity", position.get("quantity", 0)))
        block_reason = ""
        status = "planned"
        if (trade_date, ts_code) in suspended:
            status = "blocked"
            block_reason = "停牌无法执行保护性卖出"
            quantity = 0
        elif limit and bar.close <= limit.down_limit:
            status = "blocked"
            block_reason = "跌停无法执行保护性卖出"
            quantity = 0
        elif quantity <= 0:
            status = "blocked"
            block_reason = "无可卖持仓"
        reason = "触发止损价" if stop_price > 0 and bar.close <= stop_price else "单票亏损超过 8%"
        orders.append(
            {
                "tradeDate": trade_date.isoformat(),
                "tsCode": ts_code,
                "side": "sell",
                "targetWeight": 0.0,
                "score": 0.0,
                "status": status,
                "blockReason": block_reason,
                "orderQuantity": quantity,
                "orderPrice": bar.open,
                "estimatedAmount": round(quantity * bar.open, 2),
                "upLimit": limit.up_limit if limit else None,
                "downLimit": limit.down_limit if limit else None,
                "reason": reason,
                "source": "protective_stop",
            }
        )
    return orders


def _normal_account_state(account: dict[str, Any] | None) -> dict[str, Any]:
    if not account:
        return {
            "cash": DEFAULT_CONFIG.initial_cash,
            "marketValue": 0.0,
            "totalAsset": DEFAULT_CONFIG.initial_cash,
            "totalWeight": 0.0,
            "positions": {},
        }
    positions = account.get("positions", {})
    market_value = float(account.get("marketValue", 0.0))
    total_asset = float(account.get("totalAsset", DEFAULT_CONFIG.initial_cash))
    return {
        "cash": float(account.get("cash", DEFAULT_CONFIG.initial_cash)),
        "marketValue": market_value,
        "totalAsset": total_asset,
        "totalWeight": market_value / total_asset if total_asset > 0 else 0.0,
        "positions": positions,
    }


def _planned_quantity(
    signal: Any,
    bar: Any,
    cash: float,
    total_asset: float,
    current_market_value: float,
    current_positions: dict[str, Any],
    allowed_weight: float,
    risk_state: str,
    new_buy_count: int,
) -> tuple[int, str]:
    if signal.signal_type == SignalType.SELL:
        position = current_positions.get(signal.ts_code)
        quantity = int(position.get("availableQuantity", position.get("quantity", 0))) if position else 0
        return (quantity, "" if quantity > 0 else "无可卖持仓")

    if signal.signal_type != SignalType.BUY:
        return 0, "非交易信号"
    if signal.ts_code not in current_positions and len(current_positions) >= DEFAULT_CONFIG.max_positions:
        return 0, "达到最大持仓数量"
    if risk_state in {"Defensive", "Caution"} and new_buy_count >= 1 and signal.ts_code not in current_positions:
        return 0, "风控状态限制单日新增数量"

    current_value = float(current_positions.get(signal.ts_code, {}).get("marketValue", 0.0))
    target_weight = min(signal.target_weight, DEFAULT_CONFIG.max_position_weight)
    if risk_state == "Defensive":
        target_weight = min(target_weight, DEFAULT_CONFIG.min_position_weight)
    target_value = target_weight * total_asset
    room_value = max(0.0, allowed_weight * total_asset - current_market_value)
    buy_value = min(max(0.0, target_value - current_value), room_value, cash)
    quantity = int(buy_value / bar.open / DEFAULT_CONFIG.lot_size) * DEFAULT_CONFIG.lot_size
    if quantity <= 0:
        if room_value <= 0:
            return 0, "组合仓位已达到风控上限"
        if cash <= 0:
            return 0, "现金不足"
        return 0, "目标金额不足一手"
    return quantity, ""
