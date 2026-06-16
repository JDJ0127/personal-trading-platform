from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def build_strategy_comparison(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    baseline_summary = baseline["summary"]
    optimized_summary = optimized["summary"]
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "baselineStrategy": baseline["strategy"],
        "optimizedStrategy": optimized["strategy"],
        "period": optimized["period"],
        "metrics": [
            _metric("累计收益", baseline_summary["cumulativeReturn"], optimized_summary["cumulativeReturn"], higher_is_better=True),
            _metric("最大回撤", baseline_summary["maxDrawdown"], optimized_summary["maxDrawdown"], higher_is_better=False),
            _metric("交易胜率", baseline_summary["winRate"], optimized_summary["winRate"], higher_is_better=True),
            _metric("月度胜率", baseline_summary["monthlyWinRate"], optimized_summary["monthlyWinRate"], higher_is_better=True),
            _metric("成交次数", baseline_summary["fillCount"], optimized_summary["fillCount"], higher_is_better=False),
            _metric("连续亏损月份", baseline_summary["maxConsecutiveLosingMonths"], optimized_summary["maxConsecutiveLosingMonths"], higher_is_better=False),
        ],
        "verdict": _verdict(baseline_summary, optimized_summary),
    }


def write_strategy_comparison(baseline_path: str | Path, optimized_path: str | Path, output: str | Path) -> dict[str, Any]:
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    optimized = json.loads(Path(optimized_path).read_text(encoding="utf-8"))
    report = build_strategy_comparison(baseline, optimized)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _metric(label: str, baseline: float, optimized: float, higher_is_better: bool) -> dict[str, Any]:
    delta = optimized - baseline
    improved = delta > 0 if higher_is_better else delta < 0
    return {
        "label": label,
        "baseline": round(baseline, 6),
        "optimized": round(optimized, 6),
        "delta": round(delta, 6),
        "improved": improved,
    }


def _verdict(baseline: dict[str, Any], optimized: dict[str, Any]) -> str:
    if optimized["cumulativeReturn"] <= baseline["cumulativeReturn"]:
        return "收益未改善"
    if optimized["maxDrawdown"] > baseline["maxDrawdown"]:
        return "收益改善但回撤变大"
    if optimized["monthlyWinRate"] < 0.5:
        return "收益改善但月度稳定性不足"
    return "优化有效，进入更大样本验证"
