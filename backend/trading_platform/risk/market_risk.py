from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import DailyBar


def build_market_risk_report(store: SQLiteStore, trade_date: date | None = None) -> dict[str, Any]:
    bars = store.load_daily_bars(end=trade_date) if trade_date else store.load_daily_bars()
    if not bars:
        return _empty_report(trade_date)

    target_date = trade_date or max(bar.trade_date for bar in bars)
    latest_bars = [bar for bar in bars if bar.trade_date == target_date]
    if not latest_bars:
        return _empty_report(target_date)
    history_by_code: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in sorted(bars, key=lambda item: item.trade_date):
        if bar.trade_date <= target_date:
            history_by_code[bar.ts_code].append(bar)

    up_count = sum(1 for bar in latest_bars if bar.close >= bar.pre_close)
    down_count = len(latest_bars) - up_count
    breadth = up_count / len(latest_bars) if latest_bars else 0
    trend_pass_count = 0
    new_high_count = 0
    new_low_count = 0
    checks: list[dict[str, Any]] = []

    for ts_code, history in history_by_code.items():
        if len(history) < 3 or history[-1].trade_date != target_date:
            continue
        latest = history[-1]
        ma3 = sum(bar.close for bar in history[-3:]) / 3
        if latest.close > ma3:
            trend_pass_count += 1
        recent_closes = [bar.close for bar in history[-5:]]
        if latest.close >= max(recent_closes):
            new_high_count += 1
        if latest.close <= min(recent_closes):
            new_low_count += 1

    tradable_count = len(latest_bars)
    trend_ratio = trend_pass_count / tradable_count if tradable_count else 0
    conditions = [
        ("上涨股票占比 > 55%", breadth > 0.55),
        ("站上短期均线股票占比 > 50%", trend_ratio > 0.50),
        ("短期新高数量 > 新低数量", new_high_count > new_low_count),
        ("跌多涨少风险未触发", down_count <= up_count),
        ("可用行情数量 > 0", tradable_count > 0),
    ]
    score = sum(1 for _label, passed in conditions if passed)
    max_weight = _market_max_weight(score)
    risk_state = _risk_state(score, max_weight)

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tradeDate": target_date.isoformat(),
        "market": {
            "score": score,
            "state": _market_state(score),
            "maxWeight": max_weight,
            "breadthUpPct": round(breadth * 100, 2),
            "upCount": up_count,
            "downCount": down_count,
            "newHighCount": new_high_count,
            "newLowCount": new_low_count,
            "trendPassPct": round(trend_ratio * 100, 2),
            "checks": [{"name": label, "passed": passed} for label, passed in conditions],
        },
        "risk": risk_state,
    }


def write_market_risk_report(store: SQLiteStore, output: str | Path, trade_date: date | None = None) -> dict[str, Any]:
    report = build_market_risk_report(store, trade_date)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _market_state(score: int) -> str:
    if score >= 5:
        return "强势"
    if score == 4:
        return "偏强"
    if score == 3:
        return "震荡偏强"
    if score == 2:
        return "震荡偏弱"
    return "弱势"


def _market_max_weight(score: int) -> float:
    if score >= 5:
        return 0.90
    if score == 4:
        return 0.80
    if score == 3:
        return 0.60
    if score == 2:
        return 0.40
    return 0.20


def _risk_state(score: int, allowed_weight: float) -> dict[str, Any]:
    if score <= 1:
        state = "PauseBuy"
        actions = ["暂停新增买入", "只允许处理卖出信号", "等待市场评分恢复"]
    elif score == 2:
        state = "Defensive"
        actions = ["降低目标仓位", "控制单日新增数量", "优先低波动标的"]
    elif score == 3:
        state = "Caution"
        actions = ["每日最多新增 1 只", "保持行业暴露分散", "跟踪跌破均线风险"]
    else:
        state = "Normal"
        actions = ["允许按策略信号执行", "保持组合上限约束", "继续监控数据质量"]
    return {
        "state": state,
        "allowedPositionWeight": allowed_weight,
        "maxDrawdownLimit": 0.15,
        "currentDrawdown": 0.0,
        "actions": actions,
    }


def _empty_report(trade_date: date | None = None) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tradeDate": trade_date.isoformat() if trade_date else "--",
        "market": {
            "score": 0,
            "state": "无数据",
            "maxWeight": 0,
            "breadthUpPct": 0,
            "upCount": 0,
            "downCount": 0,
            "newHighCount": 0,
            "newLowCount": 0,
            "trendPassPct": 0,
            "checks": [],
        },
        "risk": {"state": "Stop", "allowedPositionWeight": 0, "maxDrawdownLimit": 0.15, "currentDrawdown": 0, "actions": ["等待数据同步"]},
    }
