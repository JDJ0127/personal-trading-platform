from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from trading_platform.models import DailyBar, LimitPrice, StockBasic, Suspension, TradeCalendar


def parse_date(value: str) -> date:
    value = value.strip()
    if "-" in value:
        return date.fromisoformat(value)
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))


def _optional_date(value: str) -> date | None:
    return parse_date(value) if value.strip() else None


class CsvDataProvider:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)

    def load_stock_basic(self) -> list[StockBasic]:
        path = self.data_dir / "stock_basic.csv"
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as file:
            return [
                StockBasic(
                    ts_code=row["ts_code"],
                    symbol=row["symbol"],
                    name=row["name"],
                    exchange=row["exchange"],
                    market=row["market"],
                    list_date=parse_date(row["list_date"]),
                    delist_date=_optional_date(row.get("delist_date", "")),
                    is_hs=row.get("is_hs", ""),
                    status=row.get("status", "L"),
                )
                for row in csv.DictReader(file)
            ]

    def load_daily_bars(self) -> list[DailyBar]:
        path = self.data_dir / "daily_bar.csv"
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as file:
            return [
                DailyBar(
                    trade_date=parse_date(row["trade_date"]),
                    ts_code=row["ts_code"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    pre_close=float(row["pre_close"]),
                    volume=float(row["volume"]),
                    amount=float(row["amount"]),
                    pct_chg=float(row.get("pct_chg", 0) or 0),
                    adj_factor=float(row.get("adj_factor", 1) or 1),
                )
                for row in csv.DictReader(file)
            ]

    def load_limit_prices(self) -> list[LimitPrice]:
        path = self.data_dir / "limit_price.csv"
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as file:
            return [
                LimitPrice(
                    trade_date=parse_date(row["trade_date"]),
                    ts_code=row["ts_code"],
                    up_limit=float(row["up_limit"]),
                    down_limit=float(row["down_limit"]),
                    limit_type=row.get("limit_type", "normal"),
                )
                for row in csv.DictReader(file)
            ]

    def load_suspensions(self) -> list[Suspension]:
        path = self.data_dir / "suspension.csv"
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as file:
            return [
                Suspension(
                    trade_date=parse_date(row["trade_date"]),
                    ts_code=row["ts_code"],
                    suspend_type=row["suspend_type"],
                    reason=row.get("reason", ""),
                )
                for row in csv.DictReader(file)
            ]

    def load_trade_calendar(self) -> list[TradeCalendar]:
        path = self.data_dir / "trade_calendar.csv"
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as file:
            return [
                TradeCalendar(
                    cal_date=parse_date(row["cal_date"]),
                    exchange=row.get("exchange", "SSE"),
                    is_open=row["is_open"] in {"1", "true", "True"},
                    pretrade_date=_optional_date(row.get("pretrade_date", "")),
                )
                for row in csv.DictReader(file)
            ]
