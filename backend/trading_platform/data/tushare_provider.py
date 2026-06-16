from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from trading_platform.data.csv_provider import parse_date
from trading_platform.models import DailyBar, LimitPrice, StockBasic, Suspension, TradeCalendar

TUSHARE_PRO_URL = "https://api.tushare.pro"


class TushareError(RuntimeError):
    pass


Transport = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class TushareClient:
    token: str
    endpoint: str = TUSHARE_PRO_URL
    timeout: float = 30.0
    transport: Transport | None = None

    def query(self, api_name: str, params: dict[str, Any] | None = None, fields: list[str] | None = None) -> list[dict[str, Any]]:
        payload = {
            "api_name": api_name,
            "token": self.token,
            "params": params or {},
            "fields": ",".join(fields or []),
        }
        response = self.transport(payload) if self.transport else self._post(payload)
        code = response.get("code")
        if code != 0:
            raise TushareError(f"Tushare {api_name} failed: {response.get('msg', 'unknown error')}")

        data = response.get("data") or {}
        response_fields = data.get("fields") or []
        items = data.get("items") or []
        return [dict(zip(response_fields, item)) for item in items]

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise TushareError(f"Tushare network request failed: {exc}") from exc


class TushareDataProvider:
    def __init__(self, client: TushareClient) -> None:
        self.client = client

    def load_stock_basic(self) -> list[StockBasic]:
        rows = self.client.query(
            "stock_basic",
            params={"list_status": "L"},
            fields=["ts_code", "symbol", "name", "area", "industry", "market", "exchange", "list_date", "delist_date", "is_hs"],
        )
        return [
            StockBasic(
                ts_code=row["ts_code"],
                symbol=row["symbol"],
                name=row["name"],
                exchange=row.get("exchange") or "",
                market=row.get("market") or "",
                list_date=parse_date(row["list_date"]),
                delist_date=_optional_date(row.get("delist_date")),
                is_hs=row.get("is_hs") or "",
                status="L",
            )
            for row in rows
        ]

    def load_daily_bars(self, start: date, end: date, ts_code: str | None = None) -> list[DailyBar]:
        params = {"start_date": _tushare_date(start), "end_date": _tushare_date(end)}
        if ts_code:
            params["ts_code"] = ts_code

        daily_rows = self.client.query(
            "daily",
            params=params,
            fields=["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "pct_chg", "vol", "amount"],
        )
        adj_factors = self._load_adj_factors(start, end, ts_code)
        return [
            DailyBar(
                trade_date=parse_date(row["trade_date"]),
                ts_code=row["ts_code"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                pre_close=float(row["pre_close"]),
                volume=float(row.get("vol") or 0),
                amount=float(row.get("amount") or 0),
                pct_chg=float(row.get("pct_chg") or 0),
                adj_factor=adj_factors.get((row["trade_date"], row["ts_code"]), 1.0),
            )
            for row in daily_rows
        ]

    def load_trade_calendar(self, start: date, end: date, exchange: str = "SSE") -> list[TradeCalendar]:
        rows = self.client.query(
            "trade_cal",
            params={"exchange": exchange, "start_date": _tushare_date(start), "end_date": _tushare_date(end)},
            fields=["exchange", "cal_date", "is_open", "pretrade_date"],
        )
        return [
            TradeCalendar(
                cal_date=parse_date(row["cal_date"]),
                exchange=row.get("exchange") or exchange,
                is_open=str(row.get("is_open")) == "1",
                pretrade_date=_optional_date(row.get("pretrade_date")),
            )
            for row in rows
        ]

    def load_limit_prices(self, start: date, end: date, ts_code: str | None = None) -> list[LimitPrice]:
        params = {"start_date": _tushare_date(start), "end_date": _tushare_date(end)}
        if ts_code:
            params["ts_code"] = ts_code

        rows = self.client.query(
            "stk_limit",
            params=params,
            fields=["trade_date", "ts_code", "up_limit", "down_limit"],
        )
        return [
            LimitPrice(
                trade_date=parse_date(row["trade_date"]),
                ts_code=row["ts_code"],
                up_limit=float(row["up_limit"]),
                down_limit=float(row["down_limit"]),
                limit_type="tushare",
            )
            for row in rows
        ]

    def load_suspensions(self, start: date, end: date, ts_code: str | None = None) -> list[Suspension]:
        params = {"suspend_date": "", "start_date": _tushare_date(start), "end_date": _tushare_date(end)}
        if ts_code:
            params["ts_code"] = ts_code

        rows = self.client.query(
            "suspend_d",
            params=params,
            fields=["ts_code", "suspend_date", "suspend_reason", "reason_type"],
        )
        return [
            Suspension(
                trade_date=parse_date(row["suspend_date"]),
                ts_code=row["ts_code"],
                suspend_type="suspend",
                reason=row.get("suspend_reason") or row.get("reason_type") or "",
            )
            for row in rows
            if row.get("suspend_date")
        ]

    def _load_adj_factors(self, start: date, end: date, ts_code: str | None = None) -> dict[tuple[str, str], float]:
        params = {"start_date": _tushare_date(start), "end_date": _tushare_date(end)}
        if ts_code:
            params["ts_code"] = ts_code

        rows = self.client.query(
            "adj_factor",
            params=params,
            fields=["ts_code", "trade_date", "adj_factor"],
        )
        return {
            (row["trade_date"], row["ts_code"]): float(row["adj_factor"])
            for row in rows
            if row.get("trade_date") and row.get("ts_code") and row.get("adj_factor") is not None
        }


def _tushare_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _optional_date(value: str | None) -> date | None:
    return parse_date(value) if value else None
