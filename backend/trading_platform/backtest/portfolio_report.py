from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_platform.models import BacktestResult, DailyBar, Fill, Side, StockBasic


def build_portfolio_report(result: BacktestResult, bars: list[DailyBar], stock_basic: list[StockBasic]) -> dict[str, Any]:
    latest_date = max((bar.trade_date for bar in bars), default=None)
    latest_prices = {bar.ts_code: bar.close for bar in bars if bar.trade_date == latest_date}
    history_by_code: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in bars:
        history_by_code[bar.ts_code].append(bar)

    stock_lookup = {stock.ts_code: stock for stock in stock_basic}
    positions, cash = _replay_positions(result.initial_cash, result.fills)
    rows = []
    for ts_code, position in sorted(positions.items()):
        quantity = int(position["quantity"])
        if quantity <= 0:
            continue
        cost_price = position["cost"] / quantity
        market_price = latest_prices.get(ts_code, cost_price)
        market_value = quantity * market_price
        pnl = (market_price - cost_price) * quantity
        stock = stock_lookup.get(ts_code)
        rows.append(
            {
                "tsCode": ts_code,
                "name": stock.name if stock else ts_code,
                "industry": stock.market if stock else "--",
                "quantity": quantity,
                "availableQuantity": quantity,
                "costPrice": round(cost_price, 4),
                "marketPrice": round(market_price, 4),
                "marketValue": round(market_value, 2),
                "weight": 0.0,
                "unrealizedPnl": round(pnl, 2),
                "unrealizedPnlPct": round(market_price / cost_price - 1, 6) if cost_price > 0 else 0,
                "holdingDays": _holding_days(history_by_code.get(ts_code, []), position["first_date"]),
                "stopPrice": round(cost_price * 0.92, 4),
                "atrVolatility": round(_average_range_pct(history_by_code.get(ts_code, [])[-20:]), 6),
            }
        )

    latest_snapshot = result.snapshots[-1] if result.snapshots else None
    total_asset = latest_snapshot.total_asset if latest_snapshot else cash + sum(row["marketValue"] for row in rows)
    market_value = sum(row["marketValue"] for row in rows)
    for row in rows:
        row["weight"] = round(row["marketValue"] / total_asset, 6) if total_asset > 0 else 0

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tradeDate": latest_date.isoformat() if latest_date else "--",
        "account": {
            "initialCash": round(result.initial_cash, 2),
            "totalAsset": round(total_asset, 2),
            "cash": round(cash, 2),
            "marketValue": round(market_value, 2),
            "dailyReturn": round(latest_snapshot.daily_return, 6) if latest_snapshot else 0,
            "cumulativeReturn": round(result.cumulative_return, 6),
            "currentDrawdown": round(latest_snapshot.drawdown, 6) if latest_snapshot else result.max_drawdown,
            "maxDrawdown": round(result.max_drawdown, 6),
            "totalWeight": round(market_value / total_asset, 6) if total_asset > 0 else 0,
            "positionCount": len(rows),
        },
        "positions": rows,
        "industryExposure": _industry_exposure(rows, total_asset),
    }


def write_portfolio_report(result: BacktestResult, bars: list[DailyBar], stock_basic: list[StockBasic], output: str | Path) -> dict[str, Any]:
    report = build_portfolio_report(result, bars, stock_basic)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _replay_positions(initial_cash: float, fills: list[Fill]) -> tuple[dict[str, dict[str, Any]], float]:
    positions: dict[str, dict[str, Any]] = {}
    cash = initial_cash
    for fill in fills:
        gross = fill.quantity * fill.price
        if fill.side == Side.BUY:
            cash -= gross + fill.fee
            current = positions.setdefault(fill.ts_code, {"quantity": 0, "cost": 0.0, "first_date": fill.trade_date})
            current["quantity"] += fill.quantity
            current["cost"] += gross + fill.fee
            current["first_date"] = min(current["first_date"], fill.trade_date)
            continue

        cash += gross - fill.fee
        current = positions.get(fill.ts_code)
        if not current:
            continue
        sell_quantity = min(fill.quantity, current["quantity"])
        average_cost = current["cost"] / current["quantity"] if current["quantity"] else 0
        current["quantity"] -= sell_quantity
        current["cost"] -= average_cost * sell_quantity
        if current["quantity"] <= 0:
            del positions[fill.ts_code]
    return positions, cash


def _holding_days(history: list[DailyBar], first_date: Any) -> int:
    return sum(1 for bar in history if bar.trade_date >= first_date)


def _average_range_pct(history: list[DailyBar]) -> float:
    values = [(bar.high - bar.low) / bar.close for bar in history if bar.close > 0]
    return sum(values) / len(values) if values else 0.0


def _industry_exposure(positions: list[dict[str, Any]], total_asset: float) -> list[dict[str, Any]]:
    exposure: dict[str, dict[str, Any]] = defaultdict(lambda: {"marketValue": 0.0, "count": 0})
    for position in positions:
        item = exposure[position["industry"]]
        item["marketValue"] += position["marketValue"]
        item["count"] += 1
    rows = [
        {
            "industry": industry,
            "weight": round(item["marketValue"] / total_asset, 6) if total_asset > 0 else 0,
            "count": item["count"],
        }
        for industry, item in exposure.items()
    ]
    cash_weight = max(0.0, 1 - sum(row["weight"] for row in rows))
    rows.append({"industry": "现金", "weight": round(cash_weight, 6), "count": 0})
    return sorted(rows, key=lambda row: row["weight"], reverse=True)
