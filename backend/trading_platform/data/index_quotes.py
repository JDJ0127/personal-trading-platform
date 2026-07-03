from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from trading_platform.data.baostock_provider import BaoStockSession
from trading_platform.models import DailyBar


DEFAULT_INDEXES = [
    {"name": "上证", "code": "000001.SH"},
    {"name": "深证", "code": "399001.SZ"},
    {"name": "创业板", "code": "399006.SZ"},
    {"name": "沪深300", "code": "000300.SH"},
]


def build_index_quote_report(bars: list[DailyBar], trade_date: date, source_name: str = "BaoStock") -> dict[str, Any]:
    bars_by_code = {bar.ts_code: bar for bar in bars}
    quotes = []
    for index_meta in DEFAULT_INDEXES:
        bar = bars_by_code.get(index_meta["code"])
        if not bar:
            continue
        change = bar.close - bar.pre_close
        change_pct = (change / bar.pre_close * 100) if bar.pre_close else bar.pct_chg
        quotes.append(
            {
                "name": index_meta["name"],
                "code": index_meta["code"],
                "value": round(bar.close, 4),
                "change": round(change, 4),
                "changePct": round(change_pct, 4),
                "updatedAt": trade_date.isoformat(),
                "trend": "up" if change > 0 else "down" if change < 0 else "flat",
            }
        )
    return {
        "schemaVersion": 1,
        "source": source_name,
        "tradeDate": trade_date.isoformat(),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "quotes": quotes,
    }


def write_baostock_index_quote_report(
    trade_date: date,
    output: str | Path,
    timeout: float = 20.0,
    retries: int = 1,
) -> dict[str, Any]:
    codes = [item["code"] for item in DEFAULT_INDEXES]
    with BaoStockSession(timeout=timeout) as provider:
        bars = provider.load_daily_bars(
            trade_date,
            trade_date,
            codes,
            adjustflag="3",
            retries=retries,
            continue_on_error=True,
        )
    report = build_index_quote_report(bars, trade_date)
    if len(report["quotes"]) != len(codes):
        found = {quote["code"] for quote in report["quotes"]}
        missing = [code for code in codes if code not in found]
        report["missingCodes"] = missing
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
