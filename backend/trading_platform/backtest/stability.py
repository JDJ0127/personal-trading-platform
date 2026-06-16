from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_platform.models import BacktestResult, PortfolioSnapshot


def build_stability_report(result: BacktestResult) -> dict[str, Any]:
    monthly_groups = _group_snapshots(result.snapshots, "%Y-%m")
    yearly_groups = _group_snapshots(result.snapshots, "%Y")
    monthly_returns = _period_rows(monthly_groups)
    yearly_returns = _period_rows(yearly_groups)
    month_values = [row["return"] for row in monthly_returns]
    winning_months = sum(1 for value in month_values if value > 0)
    losing_months = sum(1 for value in month_values if value < 0)

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "strategy": result.strategy_name,
        "period": {
            "start": result.snapshots[0].trade_date.isoformat() if result.snapshots else "--",
            "end": result.snapshots[-1].trade_date.isoformat() if result.snapshots else "--",
            "tradingDays": len(result.snapshots),
        },
        "summary": {
            "cumulativeReturn": round(result.cumulative_return, 6),
            "maxDrawdown": round(result.max_drawdown, 6),
            "winRate": round(result.win_rate, 6),
            "orderCount": result.order_count,
            "fillCount": result.fill_count,
            "winningMonthCount": winning_months,
            "losingMonthCount": losing_months,
            "monthlyWinRate": round(winning_months / len(month_values), 6) if month_values else 0,
            "bestMonthReturn": round(max(month_values), 6) if month_values else 0,
            "worstMonthReturn": round(min(month_values), 6) if month_values else 0,
            "maxConsecutiveLosingMonths": _max_consecutive_losses(month_values),
        },
        "yearlyReturns": yearly_returns,
        "monthlyReturns": monthly_returns,
        "checks": _build_checks(result, month_values),
    }


def write_stability_report(result: BacktestResult, output: str | Path) -> dict[str, Any]:
    report = build_stability_report(result)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _group_snapshots(snapshots: list[PortfolioSnapshot], pattern: str) -> dict[str, list[PortfolioSnapshot]]:
    groups: dict[str, list[PortfolioSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        groups[snapshot.trade_date.strftime(pattern)].append(snapshot)
    return groups


def _period_rows(groups: dict[str, list[PortfolioSnapshot]]) -> list[dict[str, Any]]:
    rows = []
    previous_end_asset: float | None = None
    for period, snapshots in sorted(groups.items()):
        start_asset = previous_end_asset if previous_end_asset is not None else snapshots[0].total_asset
        rows.append(_period_row(period, snapshots, start_asset))
        previous_end_asset = snapshots[-1].total_asset
    return rows


def _period_row(period: str, snapshots: list[PortfolioSnapshot], start_asset: float) -> dict[str, Any]:
    end_asset = snapshots[-1].total_asset
    period_return = end_asset / start_asset - 1 if start_asset > 0 else 0
    max_drawdown = max(snapshot.drawdown for snapshot in snapshots)
    return {
        "period": period,
        "startAsset": round(start_asset, 2),
        "endAsset": round(end_asset, 2),
        "return": round(period_return, 6),
        "maxDrawdown": round(max_drawdown, 6),
        "tradingDays": len(snapshots),
    }


def _max_consecutive_losses(values: list[float]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _build_checks(result: BacktestResult, monthly_returns: list[float]) -> list[dict[str, Any]]:
    monthly_win_rate = sum(1 for value in monthly_returns if value > 0) / len(monthly_returns) if monthly_returns else 0
    checks = [
        ("累计收益为正", result.cumulative_return > 0),
        ("最大回撤低于 15%", result.max_drawdown <= 0.15),
        ("成交次数不少于 10 次", result.fill_count >= 10),
        ("月度胜率不低于 50%", monthly_win_rate >= 0.5),
        ("连续亏损月份不超过 3 个月", _max_consecutive_losses(monthly_returns) <= 3),
    ]
    return [{"name": name, "passed": passed} for name, passed in checks]
