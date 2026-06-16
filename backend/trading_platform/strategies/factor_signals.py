from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from trading_platform.config import DEFAULT_CONFIG, TradingConfig
from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import DailyBar, FactorValue, Signal, SignalType, StockPoolEntry


FACTOR_NAMES = ["trend", "strength", "volume", "risk"]


def generate_factor_values(entries: list[StockPoolEntry], bars: list[DailyBar], trade_date: date) -> list[FactorValue]:
    history_by_code: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in sorted(bars, key=lambda item: item.trade_date):
        if bar.trade_date <= trade_date:
            history_by_code[bar.ts_code].append(bar)

    values: list[FactorValue] = []
    for entry in entries:
        if not entry.is_pass:
            continue
        history = history_by_code.get(entry.ts_code, [])
        if len(history) < 3:
            continue
        close = history[-1].close
        ma3 = _average([bar.close for bar in history[-3:]])
        first_close = history[0].close
        recent_return = close / first_close - 1 if first_close > 0 else 0.0
        amount_ratio = (entry.amount or 0) / entry.avg_amount if entry.avg_amount else 0.0
        volatility = _average([abs(bar.pct_chg) for bar in history[-5:]]) / 100

        factors = {
            "trend": (close / ma3 - 1 if ma3 else 0.0, _clip(50 + (close / ma3 - 1) * 1000 if ma3 else 50)),
            "strength": (recent_return, _clip(50 + recent_return * 500)),
            "volume": (amount_ratio, _clip(50 + (amount_ratio - 1) * 50)),
            "risk": (volatility, _clip(100 - volatility * 800)),
        }
        for name, (factor_value, factor_score) in factors.items():
            values.append(
                FactorValue(
                    trade_date=trade_date,
                    ts_code=entry.ts_code,
                    factor_name=name,
                    factor_value=factor_value,
                    factor_score=factor_score,
                )
            )
    return values


def generate_signals(
    entries: list[StockPoolEntry],
    factors: list[FactorValue],
    signal_date: date,
    trading_config: TradingConfig = DEFAULT_CONFIG,
) -> list[Signal]:
    factor_scores: dict[str, dict[str, float]] = defaultdict(dict)
    for factor in factors:
        factor_scores[factor.ts_code][factor.factor_name] = factor.factor_score

    signals: list[Signal] = []
    for entry in entries:
        if not entry.is_pass:
            continue
        scores = factor_scores.get(entry.ts_code, {})
        if not all(name in scores for name in FACTOR_NAMES):
            continue
        total_score = (
            scores["trend"] * 0.35
            + scores["strength"] * 0.25
            + scores["volume"] * 0.20
            + scores["risk"] * 0.20
        )
        if total_score >= 60:
            signal_type = SignalType.BUY
            target_weight = trading_config.min_position_weight
            reason = "趋势、强弱和量价评分满足买入观察阈值"
        elif total_score >= 50:
            signal_type = SignalType.HOLD
            target_weight = 0.0
            reason = "综合分进入观察区，等待趋势或量价确认"
        else:
            continue
        signals.append(
            Signal(
                signal_date=signal_date,
                trade_date=signal_date,
                ts_code=entry.ts_code,
                signal_type=signal_type,
                score=round(total_score, 4),
                target_weight=target_weight,
                reason=reason,
            )
        )
    return sorted(signals, key=lambda item: item.score, reverse=True)


def generate_factor_signals_from_store(store: SQLiteStore, trade_date: date | None = None) -> tuple[list[FactorValue], list[Signal]]:
    bars = store.load_daily_bars()
    target_date = trade_date or (max((bar.trade_date for bar in bars), default=None))
    if target_date is None:
        return [], []
    entries = store.load_stock_pool(target_date)
    if not entries:
        from trading_platform.universe.stock_pool import build_stock_pool_from_store

        entries = build_stock_pool_from_store(store, target_date)
        store.upsert_stock_pool(entries)
    factors = generate_factor_values(entries, bars, target_date)
    signals = generate_signals(entries, factors, target_date)
    return factors, signals


def build_signal_report(store: SQLiteStore, trade_date: date | None = None) -> dict[str, Any]:
    bars = store.load_daily_bars()
    target_date = trade_date or (max((bar.trade_date for bar in bars), default=None))
    if target_date is None:
        return {"schemaVersion": 1, "tradeDate": "--", "summary": {"signalCount": 0}, "signals": []}
    signals = store.load_signals(target_date)
    factors = store.load_factor_values(target_date)
    pool = {entry.ts_code: entry for entry in store.load_stock_pool(target_date)}
    factor_scores: dict[str, dict[str, float]] = defaultdict(dict)
    for factor in factors:
        factor_scores[factor.ts_code][factor.factor_name] = round(factor.factor_score, 2)

    return {
        "schemaVersion": 1,
        "tradeDate": target_date.isoformat(),
        "summary": {
            "signalCount": len(signals),
            "buyCount": sum(1 for item in signals if item.signal_type == SignalType.BUY),
            "watchCount": sum(1 for item in signals if item.signal_type == SignalType.HOLD),
        },
        "signals": [
            {
                "tsCode": signal.ts_code,
                "name": pool.get(signal.ts_code).name if signal.ts_code in pool else signal.ts_code,
                "industry": pool.get(signal.ts_code).industry if signal.ts_code in pool else "--",
                "signal": "buy" if signal.signal_type == SignalType.BUY else "watch",
                "totalScore": round(signal.score, 2),
                "trendScore": factor_scores.get(signal.ts_code, {}).get("trend", 0),
                "strengthScore": factor_scores.get(signal.ts_code, {}).get("strength", 0),
                "volumeScore": factor_scores.get(signal.ts_code, {}).get("volume", 0),
                "riskScore": factor_scores.get(signal.ts_code, {}).get("risk", 0),
                "targetWeight": signal.target_weight,
                "reason": signal.reason,
            }
            for signal in signals
        ],
    }


def write_signal_report(store: SQLiteStore, output: str | Path, trade_date: date | None = None) -> dict[str, Any]:
    report = build_signal_report(store, trade_date)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _clip(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 4)
