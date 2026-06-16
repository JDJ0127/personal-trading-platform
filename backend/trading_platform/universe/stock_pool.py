from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import DailyBar, StockBasic, StockPoolEntry


@dataclass(frozen=True)
class StockPoolConfig:
    min_listed_days: int = 60
    min_avg_amount: float = 100_000_000
    lookback_days: int = 20
    min_history_days: int = 3


DEFAULT_STOCK_POOL_CONFIG = StockPoolConfig()


def build_stock_pool(
    stock_basic: list[StockBasic],
    bars: list[DailyBar],
    suspended: set[tuple[date, str]],
    down_limits: dict[tuple[date, str], float],
    trade_date: date,
    config: StockPoolConfig = DEFAULT_STOCK_POOL_CONFIG,
) -> list[StockPoolEntry]:
    bars_by_code: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in sorted(bars, key=lambda item: item.trade_date):
        if bar.trade_date <= trade_date:
            bars_by_code[bar.ts_code].append(bar)

    entries: list[StockPoolEntry] = []
    for stock in stock_basic:
        history = bars_by_code.get(stock.ts_code, [])
        latest = history[-1] if history and history[-1].trade_date == trade_date else None
        lookback = history[-config.lookback_days :]
        listed_days = (trade_date - stock.list_date).days
        reasons: list[str] = []

        if stock.status != "L":
            reasons.append("非上市状态")
        if "ST" in stock.name.upper() or "退" in stock.name:
            reasons.append("ST或退市风险")
        if listed_days < config.min_listed_days:
            reasons.append("上市不足60天")
        if (trade_date, stock.ts_code) in suspended:
            reasons.append("当日停牌")
        if not latest:
            reasons.append("当日无行情")
        if len(lookback) < config.min_history_days:
            reasons.append("历史行情不足")

        avg_amount = _average([bar.amount for bar in lookback])
        if avg_amount is not None and avg_amount < config.min_avg_amount:
            reasons.append("流动性不足")
        if avg_amount is None:
            reasons.append("缺少成交额")

        down_limit = down_limits.get((trade_date, stock.ts_code))
        if latest and down_limit is not None and latest.close <= down_limit:
            reasons.append("当日跌停")

        entries.append(
            StockPoolEntry(
                trade_date=trade_date,
                ts_code=stock.ts_code,
                name=stock.name,
                industry=stock.market or stock.exchange or "--",
                is_pass=not reasons,
                filter_reasons=tuple(reasons),
                listed_days=max(0, listed_days),
                close=latest.close if latest else None,
                amount=latest.amount if latest else None,
                avg_amount=avg_amount,
            )
        )

    return entries


def build_stock_pool_from_store(
    store: SQLiteStore,
    trade_date: date | None = None,
    config: StockPoolConfig = DEFAULT_STOCK_POOL_CONFIG,
) -> list[StockPoolEntry]:
    store.initialize()
    bars = store.load_daily_bars()
    target_date = trade_date or _latest_trade_date(bars)
    if not target_date:
        return []
    down_limits = {
        key: value.down_limit
        for key, value in store.load_limit_prices().items()
    }
    return build_stock_pool(
        stock_basic=store.load_stock_basic(),
        bars=bars,
        suspended=store.load_suspensions(),
        down_limits=down_limits,
        trade_date=target_date,
        config=config,
    )


def build_stock_pool_report(entries: list[StockPoolEntry]) -> dict[str, Any]:
    trade_date = entries[0].trade_date.isoformat() if entries else "--"
    reason_counts = Counter(reason for entry in entries for reason in entry.filter_reasons)
    passed = [entry for entry in entries if entry.is_pass]
    blocked = [entry for entry in entries if not entry.is_pass]

    return {
        "schemaVersion": 1,
        "tradeDate": trade_date,
        "summary": {
            "total": len(entries),
            "passed": len(passed),
            "blocked": len(blocked),
            "passRate": round(len(passed) / len(entries), 6) if entries else 0,
        },
        "filters": [
            {"reason": reason, "count": count}
            for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "stocks": [
            {
                "tsCode": entry.ts_code,
                "name": entry.name,
                "industry": entry.industry,
                "isPass": entry.is_pass,
                "filterReasons": list(entry.filter_reasons),
                "listedDays": entry.listed_days,
                "close": entry.close,
                "amount": entry.amount,
                "avgAmount": entry.avg_amount,
            }
            for entry in entries
        ],
    }


def write_stock_pool_report(entries: list[StockPoolEntry], output: str | Path) -> dict[str, Any]:
    report = build_stock_pool_report(entries)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _latest_trade_date(bars: list[DailyBar]) -> date | None:
    if not bars:
        return None
    return max(bar.trade_date for bar in bars)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
