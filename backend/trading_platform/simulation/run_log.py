from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_platform.data.sqlite_store import SQLiteStore


def start_pipeline_run(
    store: SQLiteStore,
    workflow: str,
    source: str,
    account_id: str | None,
    trade_date: date | None,
) -> str:
    store.initialize()
    run_id = uuid4().hex
    now = datetime.now().isoformat(timespec="seconds")
    with store.connect() as conn:
        conn.execute(
            """
            insert into pipeline_run
              (run_id, workflow, source, account_id, trade_date, status, started_at)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, workflow, source, account_id, trade_date.isoformat() if trade_date else None, "running", now),
        )
    return run_id


def finish_pipeline_run(
    store: SQLiteStore,
    run_id: str,
    status: str,
    metrics: dict[str, int] | None = None,
    error_message: str = "",
) -> dict[str, Any]:
    store.initialize()
    now = datetime.now()
    metrics = metrics or {}
    with store.connect() as conn:
        started = conn.execute("select started_at from pipeline_run where run_id = ?", (run_id,)).fetchone()
        duration_ms = None
        if started:
            started_at = datetime.fromisoformat(started["started_at"])
            duration_ms = int((now - started_at).total_seconds() * 1000)
        conn.execute(
            """
            update pipeline_run
            set status = ?, finished_at = ?, duration_ms = ?,
                stock_count = ?, signal_count = ?, planned_order_count = ?, blocked_order_count = ?,
                order_count = ?, fill_count = ?, error_message = ?
            where run_id = ?
            """,
            (
                status,
                now.isoformat(timespec="seconds"),
                duration_ms,
                metrics.get("stockCount", 0),
                metrics.get("signalCount", 0),
                metrics.get("plannedOrderCount", 0),
                metrics.get("blockedOrderCount", 0),
                metrics.get("orderCount", 0),
                metrics.get("fillCount", 0),
                error_message[:1000],
                run_id,
            ),
        )
    return build_run_log_report(store)


def collect_paper_metrics(store: SQLiteStore, account_id: str, trade_date: date) -> dict[str, int]:
    store.initialize()
    date_text = trade_date.isoformat()
    with store.connect() as conn:
        stock_count = conn.execute("select count(*) as count from stock_pool where trade_date = ?", (date_text,)).fetchone()["count"]
        signal_count = conn.execute("select count(*) as count from signal where signal_date = ?", (date_text,)).fetchone()["count"]
        order_count = conn.execute(
            "select count(*) as count from simulation_order where account_id = ? and trade_date = ?",
            (account_id, date_text),
        ).fetchone()["count"]
        fill_count = conn.execute(
            "select count(*) as count from simulation_fill where account_id = ? and trade_date = ?",
            (account_id, date_text),
        ).fetchone()["count"]
    return {
        "stockCount": stock_count,
        "signalCount": signal_count,
        "orderCount": order_count,
        "fillCount": fill_count,
    }


def build_run_log_report(store: SQLiteStore, limit: int = 30) -> dict[str, Any]:
    store.initialize()
    with store.connect() as conn:
        rows = conn.execute(
            """
            select * from pipeline_run
            order by started_at desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    success_count = sum(1 for row in rows if row["status"] == "success")
    failed_count = sum(1 for row in rows if row["status"] == "failed")
    running_count = sum(1 for row in rows if row["status"] == "running")
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "runCount": len(rows),
            "successCount": success_count,
            "failedCount": failed_count,
            "runningCount": running_count,
            "latestStatus": rows[0]["status"] if rows else "--",
            "latestTradeDate": rows[0]["trade_date"] if rows else "--",
        },
        "runs": [_row_to_dict(row) for row in rows],
    }


def write_run_log_report(store: SQLiteStore, output: str | Path, limit: int = 30) -> dict[str, Any]:
    report = build_run_log_report(store, limit)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "runId": row["run_id"],
        "workflow": row["workflow"],
        "source": row["source"],
        "accountId": row["account_id"],
        "tradeDate": row["trade_date"],
        "status": row["status"],
        "startedAt": row["started_at"],
        "finishedAt": row["finished_at"],
        "durationMs": row["duration_ms"],
        "stockCount": row["stock_count"],
        "signalCount": row["signal_count"],
        "plannedOrderCount": row["planned_order_count"],
        "blockedOrderCount": row["blocked_order_count"],
        "orderCount": row["order_count"],
        "fillCount": row["fill_count"],
        "errorMessage": row["error_message"],
    }
