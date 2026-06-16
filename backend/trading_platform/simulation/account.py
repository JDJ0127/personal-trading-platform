from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_platform.backtest.broker import SimulatedBroker
from trading_platform.backtest.portfolio import Portfolio
from trading_platform.backtest.portfolio_report import build_portfolio_report
from trading_platform.config import DEFAULT_CONFIG
from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import BacktestResult, DailyBar, Order, PortfolioSnapshot, Position, SignalType, Side, StockBasic
from trading_platform.simulation.planner import build_order_plan


def persist_backtest_account(
    store: SQLiteStore,
    result: BacktestResult,
    bars: list[DailyBar],
    stock_basic: list[StockBasic],
    account_id: str = "paper-main",
    account_name: str = "模拟盘主账户",
) -> dict[str, Any]:
    store.initialize()
    report = build_portfolio_report(result, bars, stock_basic)
    now = datetime.now().isoformat(timespec="seconds")
    account = report["account"]
    trade_date = report["tradeDate"] if report["tradeDate"] != "--" else None

    with store.connect() as conn:
        existing = conn.execute(
            "select created_at from simulation_account where account_id = ?",
            (account_id,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        conn.execute("delete from simulation_order where account_id = ?", (account_id,))
        conn.execute("delete from simulation_fill where account_id = ?", (account_id,))
        conn.execute("delete from simulation_position where account_id = ?", (account_id,))
        conn.execute("delete from simulation_equity_curve where account_id = ?", (account_id,))
        conn.execute(
            """
            insert into simulation_account values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(account_id) do update set
              account_name=excluded.account_name,
              mode=excluded.mode,
              strategy_name=excluded.strategy_name,
              initial_cash=excluded.initial_cash,
              total_asset=excluded.total_asset,
              cash=excluded.cash,
              market_value=excluded.market_value,
              cumulative_return=excluded.cumulative_return,
              max_drawdown=excluded.max_drawdown,
              position_count=excluded.position_count,
              last_trade_date=excluded.last_trade_date,
              status=excluded.status,
              updated_at=excluded.updated_at
            """,
            (
                account_id,
                account_name,
                "paper",
                result.strategy_name,
                result.initial_cash,
                account["totalAsset"],
                account["cash"],
                account["marketValue"],
                account["cumulativeReturn"],
                account["maxDrawdown"],
                account["positionCount"],
                trade_date,
                "active",
                created_at,
                now,
            ),
        )
        conn.executemany(
            "insert into simulation_order values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    account_id,
                    order.order_id,
                    order.trade_date.isoformat(),
                    order.ts_code,
                    order.side.value,
                    order.order_price,
                    order.order_quantity,
                    order.filled_quantity,
                    order.avg_fill_price,
                    order.status.value,
                    order.reject_reason,
                )
                for order in result.orders
            ],
        )
        conn.executemany(
            "insert into simulation_fill values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    account_id,
                    _fill_id(index, fill.trade_date.isoformat(), fill.ts_code, fill.side.value),
                    fill.trade_date.isoformat(),
                    fill.ts_code,
                    fill.side.value,
                    fill.quantity,
                    fill.price,
                    fill.commission,
                    fill.stamp_tax,
                    fill.transfer_fee,
                )
                for index, fill in enumerate(result.fills, start=1)
            ],
        )
        conn.executemany(
            "insert into simulation_position values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    account_id,
                    trade_date,
                    position["tsCode"],
                    position["name"],
                    position["industry"],
                    position["quantity"],
                    position["availableQuantity"],
                    position["costPrice"],
                    position["marketPrice"],
                    position["marketValue"],
                    position["weight"],
                    position["unrealizedPnl"],
                    position["unrealizedPnlPct"],
                    position["stopPrice"],
                    position["holdingDays"],
                )
                for position in report["positions"]
                if trade_date
            ],
        )
        conn.executemany(
            "insert into simulation_equity_curve values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    account_id,
                    snapshot.trade_date.isoformat(),
                    snapshot.total_asset,
                    snapshot.cash,
                    snapshot.market_value,
                    snapshot.daily_return,
                    snapshot.cumulative_return,
                    snapshot.drawdown,
                    snapshot.max_drawdown,
                    snapshot.position_count,
                    snapshot.total_weight,
                )
                for snapshot in result.snapshots
            ],
        )

    return load_simulation_account_report(store, account_id)


def write_simulation_account_report(
    store: SQLiteStore,
    account_id: str,
    output: str | Path,
) -> dict[str, Any]:
    report = load_simulation_account_report(store, account_id)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def reset_simulation_account(store: SQLiteStore, account_id: str) -> None:
    store.initialize()
    with store.connect() as conn:
        conn.execute("delete from simulation_order where account_id = ?", (account_id,))
        conn.execute("delete from simulation_fill where account_id = ?", (account_id,))
        conn.execute("delete from simulation_position where account_id = ?", (account_id,))
        conn.execute("delete from simulation_equity_curve where account_id = ?", (account_id,))
        conn.execute("delete from simulation_account where account_id = ?", (account_id,))


def run_daily_simulation(
    store: SQLiteStore,
    trade_date: Any,
    account_id: str = "paper-main",
    account_name: str = "模拟盘主账户",
    output: str | Path | None = None,
) -> dict[str, Any]:
    store.initialize()
    account = _ensure_account(store, account_id, account_name)
    bars = {bar.ts_code: bar for bar in store.load_daily_bars(trade_date, trade_date)}
    if not bars:
        raise ValueError(f"no daily bars found for trade date: {trade_date}")

    portfolio = _load_portfolio_from_account(store, account_id, account)
    portfolio.mark_to_market({code: bar.open for code, bar in bars.items()})
    broker = SimulatedBroker(DEFAULT_CONFIG, store.load_limit_prices(), store.load_suspensions())
    plan = build_order_plan(store, trade_date, _portfolio_account_state(portfolio))
    planned_orders = [item for item in plan["orders"] if item["status"] == "planned"]

    orders: list[Order] = []
    fills = []
    for planned in planned_orders:
        bar = bars.get(planned["tsCode"])
        if not bar:
            continue
        side = Side(planned["side"])
        quantity = int(planned["orderQuantity"])
        if quantity <= 0:
            continue
        order = broker.create_order(trade_date, planned["tsCode"], side, bar.open, quantity)
        available_qty = portfolio.positions.get(order.ts_code).available_quantity if order.ts_code in portfolio.positions else 0
        filled_order, fill = broker.execute(order, bar, portfolio.cash, available_qty)
        orders.append(filled_order)
        if fill:
            portfolio.apply_fill(fill)
            fills.append(fill)

    portfolio.mark_to_market({code: bar.close for code, bar in bars.items()})
    previous_asset = _previous_total_asset(store, account_id, trade_date) or account["total_asset"]
    equity_peak = max(_equity_peak(store, account_id, trade_date), account["initial_cash"], portfolio.total_asset)
    drawdown = 0.0 if equity_peak == 0 else (equity_peak - portfolio.total_asset) / equity_peak
    previous_max_drawdown = account["max_drawdown"] or 0.0
    max_drawdown = max(previous_max_drawdown, drawdown)
    snapshot = PortfolioSnapshot(
        trade_date=trade_date,
        total_asset=portfolio.total_asset,
        cash=portfolio.cash,
        market_value=portfolio.market_value,
        daily_return=0.0 if previous_asset == 0 else portfolio.total_asset / previous_asset - 1,
        cumulative_return=0.0 if account["initial_cash"] == 0 else portfolio.total_asset / account["initial_cash"] - 1,
        drawdown=drawdown,
        max_drawdown=max_drawdown,
        position_count=len(portfolio.positions),
        total_weight=portfolio.total_weight,
    )
    _write_daily_state(store, account_id, account_name, account["strategy_name"], snapshot, portfolio, orders, fills)
    if output:
        return write_simulation_account_report(store, account_id, output)
    return load_simulation_account_report(store, account_id)


def load_simulation_account_report(store: SQLiteStore, account_id: str) -> dict[str, Any]:
    store.initialize()
    with store.connect() as conn:
        account = conn.execute(
            "select * from simulation_account where account_id = ?",
            (account_id,),
        ).fetchone()
        if account is None:
            raise ValueError(f"simulation account not found: {account_id}")
        positions = conn.execute(
            "select * from simulation_position where account_id = ? order by weight desc, ts_code",
            (account_id,),
        ).fetchall()
        equity_curve = conn.execute(
            "select * from simulation_equity_curve where account_id = ? order by trade_date",
            (account_id,),
        ).fetchall()
        orders = conn.execute(
            "select * from simulation_order where account_id = ? order by trade_date, order_id",
            (account_id,),
        ).fetchall()
        fills = conn.execute(
            "select * from simulation_fill where account_id = ? order by trade_date, fill_id",
            (account_id,),
        ).fetchall()

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "account": _account_row(account),
        "positions": [_position_row(row) for row in positions],
        "equityCurve": [_equity_row(row) for row in equity_curve],
        "orders": [_order_row(row) for row in orders],
        "fills": [_fill_row(row) for row in fills],
        "summary": {
            "orderCount": len(orders),
            "fillCount": len(fills),
            "positionCount": len(positions),
            "equityPointCount": len(equity_curve),
        },
    }


def _ensure_account(store: SQLiteStore, account_id: str, account_name: str) -> Any:
    with store.connect() as conn:
        row = conn.execute("select * from simulation_account where account_id = ?", (account_id,)).fetchone()
        if row:
            return row
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """
            insert into simulation_account values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                account_name,
                "paper",
                "manual_signal",
                DEFAULT_CONFIG.initial_cash,
                DEFAULT_CONFIG.initial_cash,
                DEFAULT_CONFIG.initial_cash,
                0.0,
                0.0,
                0.0,
                0,
                None,
                "active",
                now,
                now,
            ),
        )
    with store.connect() as conn:
        return conn.execute("select * from simulation_account where account_id = ?", (account_id,)).fetchone()


def _load_portfolio_from_account(store: SQLiteStore, account_id: str, account: Any) -> Portfolio:
    portfolio = Portfolio(account["initial_cash"])
    portfolio.cash = account["cash"]
    with store.connect() as conn:
        rows = conn.execute("select * from simulation_position where account_id = ?", (account_id,)).fetchall()
    for row in rows:
        portfolio.positions[row["ts_code"]] = Position(
            ts_code=row["ts_code"],
            quantity=row["quantity"],
            available_quantity=row["quantity"],
            cost_price=row["cost_price"],
            market_price=row["market_price"],
            holding_days=row["holding_days"],
        )
    return portfolio


def _portfolio_account_state(portfolio: Portfolio) -> dict[str, Any]:
    return {
        "cash": portfolio.cash,
        "marketValue": portfolio.market_value,
        "totalAsset": portfolio.total_asset,
        "positions": {
            code: {
                "quantity": position.quantity,
                "availableQuantity": position.available_quantity,
                "marketValue": position.market_value,
                "stopPrice": position.cost_price * 0.92,
                "unrealizedPnlPct": position.market_price / position.cost_price - 1 if position.cost_price > 0 else 0.0,
            }
            for code, position in portfolio.positions.items()
        },
    }


def _previous_total_asset(store: SQLiteStore, account_id: str, trade_date: Any) -> float | None:
    with store.connect() as conn:
        row = conn.execute(
            """
            select total_asset from simulation_equity_curve
            where account_id = ? and trade_date < ?
            order by trade_date desc
            limit 1
            """,
            (account_id, trade_date.isoformat()),
        ).fetchone()
    return row["total_asset"] if row else None


def _equity_peak(store: SQLiteStore, account_id: str, trade_date: Any) -> float:
    with store.connect() as conn:
        row = conn.execute(
            "select max(total_asset) as peak from simulation_equity_curve where account_id = ? and trade_date < ?",
            (account_id, trade_date.isoformat()),
        ).fetchone()
    return row["peak"] or 0.0


def _write_daily_state(
    store: SQLiteStore,
    account_id: str,
    account_name: str,
    strategy_name: str,
    snapshot: PortfolioSnapshot,
    portfolio: Portfolio,
    orders: list[Order],
    fills: list[Any],
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    stock_lookup = {stock.ts_code: stock for stock in store.load_stock_basic()}
    trade_date = snapshot.trade_date.isoformat()
    with store.connect() as conn:
        conn.execute("delete from simulation_order where account_id = ? and trade_date = ?", (account_id, trade_date))
        conn.execute("delete from simulation_fill where account_id = ? and trade_date = ?", (account_id, trade_date))
        conn.execute("delete from simulation_equity_curve where account_id = ? and trade_date = ?", (account_id, trade_date))
        conn.execute("delete from simulation_position where account_id = ?", (account_id,))
        conn.execute(
            """
            update simulation_account
            set account_name = ?, total_asset = ?, cash = ?, market_value = ?, cumulative_return = ?,
                max_drawdown = ?, position_count = ?, last_trade_date = ?, status = ?, updated_at = ?
            where account_id = ?
            """,
            (
                account_name,
                snapshot.total_asset,
                snapshot.cash,
                snapshot.market_value,
                snapshot.cumulative_return,
                snapshot.max_drawdown,
                snapshot.position_count,
                trade_date,
                "active",
                now,
                account_id,
            ),
        )
        conn.executemany(
            "insert into simulation_order values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    account_id,
                    order.order_id,
                    order.trade_date.isoformat(),
                    order.ts_code,
                    order.side.value,
                    order.order_price,
                    order.order_quantity,
                    order.filled_quantity,
                    order.avg_fill_price,
                    order.status.value,
                    order.reject_reason,
                )
                for order in orders
            ],
        )
        conn.executemany(
            "insert into simulation_fill values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    account_id,
                    _fill_id(index, fill.trade_date.isoformat(), fill.ts_code, fill.side.value),
                    fill.trade_date.isoformat(),
                    fill.ts_code,
                    fill.side.value,
                    fill.quantity,
                    fill.price,
                    fill.commission,
                    fill.stamp_tax,
                    fill.transfer_fee,
                )
                for index, fill in enumerate(fills, start=1)
            ],
        )
        conn.executemany(
            "insert into simulation_position values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    account_id,
                    trade_date,
                    code,
                    stock_lookup.get(code).name if code in stock_lookup else code,
                    stock_lookup.get(code).market if code in stock_lookup else "--",
                    position.quantity,
                    position.available_quantity,
                    position.cost_price,
                    position.market_price,
                    position.market_value,
                    position.market_value / snapshot.total_asset if snapshot.total_asset > 0 else 0.0,
                    position.unrealized_pnl,
                    position.market_price / position.cost_price - 1 if position.cost_price > 0 else 0.0,
                    position.cost_price * 0.92,
                    position.holding_days + 1,
                )
                for code, position in portfolio.positions.items()
            ],
        )
        conn.execute(
            "insert into simulation_equity_curve values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_id,
                trade_date,
                snapshot.total_asset,
                snapshot.cash,
                snapshot.market_value,
                snapshot.daily_return,
                snapshot.cumulative_return,
                snapshot.drawdown,
                snapshot.max_drawdown,
                snapshot.position_count,
                snapshot.total_weight,
            ),
        )


def _fill_id(index: int, trade_date: str, ts_code: str, side: str) -> str:
    return f"{trade_date}-{index:06d}-{ts_code}-{side}"


def _account_row(row: Any) -> dict[str, Any]:
    return {
        "accountId": row["account_id"],
        "accountName": row["account_name"],
        "mode": row["mode"],
        "strategyName": row["strategy_name"],
        "initialCash": round(row["initial_cash"], 2),
        "totalAsset": round(row["total_asset"], 2),
        "cash": round(row["cash"], 2),
        "marketValue": round(row["market_value"], 2),
        "cumulativeReturn": round(row["cumulative_return"], 6),
        "maxDrawdown": round(row["max_drawdown"], 6),
        "positionCount": row["position_count"],
        "lastTradeDate": row["last_trade_date"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def _position_row(row: Any) -> dict[str, Any]:
    return {
        "tradeDate": row["trade_date"],
        "tsCode": row["ts_code"],
        "name": row["name"],
        "industry": row["industry"],
        "quantity": row["quantity"],
        "availableQuantity": row["available_quantity"],
        "costPrice": round(row["cost_price"], 4),
        "marketPrice": round(row["market_price"], 4),
        "marketValue": round(row["market_value"], 2),
        "weight": round(row["weight"], 6),
        "unrealizedPnl": round(row["unrealized_pnl"], 2),
        "unrealizedPnlPct": round(row["unrealized_pnl_pct"], 6),
        "stopPrice": round(row["stop_price"], 4),
        "holdingDays": row["holding_days"],
    }


def _equity_row(row: Any) -> dict[str, Any]:
    return {
        "tradeDate": row["trade_date"],
        "totalAsset": round(row["total_asset"], 2),
        "cash": round(row["cash"], 2),
        "marketValue": round(row["market_value"], 2),
        "dailyReturn": round(row["daily_return"], 6),
        "cumulativeReturn": round(row["cumulative_return"], 6),
        "drawdown": round(row["drawdown"], 6),
        "maxDrawdown": round(row["max_drawdown"], 6),
        "positionCount": row["position_count"],
        "totalWeight": round(row["total_weight"], 6),
    }


def _order_row(row: Any) -> dict[str, Any]:
    return {
        "orderId": row["order_id"],
        "tradeDate": row["trade_date"],
        "tsCode": row["ts_code"],
        "side": row["side"],
        "orderPrice": round(row["order_price"], 4),
        "orderQuantity": row["order_quantity"],
        "filledQuantity": row["filled_quantity"],
        "avgFillPrice": round(row["avg_fill_price"], 4),
        "status": row["status"],
        "rejectReason": row["reject_reason"],
    }


def _fill_row(row: Any) -> dict[str, Any]:
    return {
        "fillId": row["fill_id"],
        "tradeDate": row["trade_date"],
        "tsCode": row["ts_code"],
        "side": row["side"],
        "quantity": row["quantity"],
        "price": round(row["price"], 4),
        "commission": round(row["commission"], 4),
        "stampTax": round(row["stamp_tax"], 4),
        "transferFee": round(row["transfer_fee"], 4),
        "fee": round(row["commission"] + row["stamp_tax"] + row["transfer_fee"], 4),
    }
