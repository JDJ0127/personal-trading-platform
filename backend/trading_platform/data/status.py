from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.data.validation import validate_daily_bars


DISPLAY_NAMES = {
    "stock_basic": "股票基础信息",
    "trade_calendar": "交易日历",
    "daily_bar": "日线行情",
    "limit_price": "涨跌停价格",
    "suspension": "停复牌",
    "stock_pool": "股票池",
    "factor_value": "因子值",
    "signal": "策略信号",
}

RAW_TABLES = {"stock_basic", "trade_calendar", "daily_bar", "limit_price", "suspension"}
DERIVED_TABLES = {"stock_pool", "factor_value", "signal"}


def build_data_status_report(store: SQLiteStore, source_name: str = "Tushare") -> dict[str, Any]:
    table_rows = store.table_status()
    daily_bars = store.load_daily_bars()
    daily_issues = validate_daily_bars(daily_bars)
    tables = [_table_status_to_task(row, source_name) for row in table_rows]
    latest_trade_date = _latest_for(table_rows, "daily_bar")
    latest_calendar_date = _latest_for(table_rows, "trade_calendar")
    coverage = _build_coverage(store, daily_bars)

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "database": str(store.db_path),
        "summary": {
            "latestTradeDate": latest_trade_date or "--",
            "latestCalendarDate": latest_calendar_date or "--",
            "tableCount": len(tables),
            "totalRecords": sum(int(row["recordCount"]) for row in table_rows),
            "qualityIssueCount": len(daily_issues),
            "stockCount": coverage["stockCount"],
            "barStockCount": coverage["barStockCount"],
            "barTradeDayCount": coverage["barTradeDayCount"],
            "expectedBarCount": coverage["expectedBarCount"],
            "actualBarCount": coverage["actualBarCount"],
            "missingBarCount": coverage["missingBarCount"],
            "coverageRate": coverage["coverageRate"],
        },
        "coverage": coverage,
        "tables": tables,
        "qualityIssues": [
            {"table": issue.table, "key": issue.key, "message": issue.message}
            for issue in daily_issues[:50]
        ],
    }


def write_data_status_report(store: SQLiteStore, output: str | Path, source_name: str = "Tushare") -> dict[str, Any]:
    report = build_data_status_report(store, source_name)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _table_status_to_task(row: dict[str, object], source_name: str) -> dict[str, object]:
    table = str(row["table"])
    label = DISPLAY_NAMES.get(table, table)
    source = source_name if table in RAW_TABLES else "本地生成" if table in DERIVED_TABLES else "--"
    record_count = int(row["recordCount"])
    return {
        "table": table,
        "name": label,
        "source": source,
        "status": "正常" if record_count > 0 else "待同步",
        "latestDate": row["latestDate"] or "--",
        "recordCount": record_count,
    }


def _latest_for(rows: list[dict[str, object]], table: str) -> str | None:
    for row in rows:
        if row["table"] == table:
            value = row["latestDate"]
            return str(value) if value else None
    return None


def _build_coverage(store: SQLiteStore, daily_bars: list[Any]) -> dict[str, Any]:
    stock_count = sum(1 for stock in store.load_stock_basic() if stock.status == "L")
    if not daily_bars:
        return {
            "startDate": "--",
            "endDate": "--",
            "stockCount": stock_count,
            "barStockCount": 0,
            "calendarTradeDayCount": 0,
            "barTradeDayCount": 0,
            "expectedBarCount": 0,
            "actualBarCount": 0,
            "missingBarCount": 0,
            "coverageRate": 0.0,
            "missingByDate": [],
            "missingByStock": [],
        }

    start_date = min(bar.trade_date for bar in daily_bars)
    end_date = max(bar.trade_date for bar in daily_bars)
    bar_codes = sorted({bar.ts_code for bar in daily_bars})
    bar_dates = sorted({bar.trade_date for bar in daily_bars})
    calendar_dates = _open_calendar_dates(store, start_date, end_date)
    expected_dates = calendar_dates or bar_dates
    observed: dict[date, set[str]] = defaultdict(set)
    for bar in daily_bars:
        if start_date <= bar.trade_date <= end_date:
            observed[bar.trade_date].add(bar.ts_code)

    expected_bar_count = len(expected_dates) * len(bar_codes)
    actual_bar_count = sum(len(observed[trade_date]) for trade_date in expected_dates)
    missing_by_date = []
    missing_by_stock: Counter[str] = Counter()
    for trade_date in expected_dates:
        missing_codes = sorted(set(bar_codes) - observed.get(trade_date, set()))
        if not missing_codes:
            continue
        missing_by_date.append(
            {
                "tradeDate": trade_date.isoformat(),
                "missingCount": len(missing_codes),
                "missingCodes": missing_codes[:10],
            }
        )
        missing_by_stock.update(missing_codes)

    missing_bar_count = expected_bar_count - actual_bar_count
    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "stockCount": stock_count,
        "barStockCount": len(bar_codes),
        "calendarTradeDayCount": len(calendar_dates),
        "barTradeDayCount": len(bar_dates),
        "expectedBarCount": expected_bar_count,
        "actualBarCount": actual_bar_count,
        "missingBarCount": missing_bar_count,
        "coverageRate": round(actual_bar_count / expected_bar_count, 6) if expected_bar_count else 0.0,
        "missingByDate": missing_by_date[:20],
        "missingByStock": [
            {"tsCode": ts_code, "missingCount": count}
            for ts_code, count in missing_by_stock.most_common(20)
        ],
    }


def _open_calendar_dates(store: SQLiteStore, start_date: date, end_date: date) -> list[date]:
    with store.connect() as conn:
        rows = conn.execute(
            """
            select distinct cal_date from trade_calendar
            where is_open = 1 and cal_date between ? and ?
            order by cal_date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return [date.fromisoformat(row["cal_date"]) for row in rows]
