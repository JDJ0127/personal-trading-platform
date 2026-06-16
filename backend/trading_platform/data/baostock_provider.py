from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
import signal
import socket
from typing import Any, Protocol

from trading_platform.data.csv_provider import parse_date
from trading_platform.models import DailyBar, LimitPrice, StockBasic, Suspension, TradeCalendar


class BaoStockError(RuntimeError):
    pass


class BaoStockClientProtocol(Protocol):
    def login(self) -> Any:
        ...

    def logout(self) -> Any:
        ...

    def query_all_stock(self, day: str) -> Any:
        ...

    def query_stock_basic(self, code: str = "", code_name: str = "") -> Any:
        ...

    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "2",
    ) -> Any:
        ...

    def query_trade_dates(self, start_date: str, end_date: str) -> Any:
        ...


@dataclass
class BaoStockSession:
    client: BaoStockClientProtocol | None = None
    timeout: float = 20.0
    _previous_timeout: float | None = None

    def __enter__(self) -> "BaoStockDataProvider":
        self._previous_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(self.timeout)
        client = self.client or _import_baostock()
        login_result = client.login()
        if getattr(login_result, "error_code", "0") != "0":
            raise BaoStockError(f"BaoStock login failed: {getattr(login_result, 'error_msg', 'unknown error')}")
        self.client = client
        return BaoStockDataProvider(client, timeout=self.timeout)

    def __exit__(self, *_exc: object) -> None:
        if self.client:
            self.client.logout()
        socket.setdefaulttimeout(self._previous_timeout)


class BaoStockDataProvider:
    def __init__(self, client: BaoStockClientProtocol, timeout: float = 20.0) -> None:
        self.client = client
        self.timeout = timeout

    def load_stock_basic(self, as_of: date, codes: Iterable[str] | None = None) -> list[StockBasic]:
        if codes:
            rows = []
            for code in codes:
                rows.extend(_result_rows(self.client.query_stock_basic(code=_to_baostock_code(code))))
            return _stock_basic_from_rows(rows)

        listed_codes = {
            _to_ts_code(row["code"])
            for row in _result_rows(self.client.query_all_stock(day=as_of.isoformat()))
            if row.get("code")
        }
        return [
            stock
            for stock in _stock_basic_from_rows(_result_rows(self.client.query_stock_basic()))
            if not listed_codes or stock.ts_code in listed_codes
        ]

    def load_all_stock_codes(self, as_of: date) -> list[str]:
        return [
            _to_ts_code(row["code"])
            for row in _result_rows(self.client.query_all_stock(day=as_of.isoformat()))
            if row.get("code")
        ]

    def load_daily_bars(
        self,
        start: date,
        end: date,
        codes: Iterable[str],
        adjustflag: str = "2",
        retries: int = 1,
        continue_on_error: bool = False,
    ) -> list[DailyBar]:
        fields = "date,code,open,high,low,close,preclose,volume,amount,pctChg"
        bars: list[DailyBar] = []
        for code in codes:
            try:
                rows = self._history_rows_with_retry(code, fields, start, end, adjustflag, retries)
            except Exception:
                if continue_on_error:
                    continue
                raise
            for row in rows:
                bar = _daily_bar_from_row(row)
                if bar:
                    bars.append(bar)
        return bars

    def _history_rows_with_retry(
        self,
        code: str,
        fields: str,
        start: date,
        end: date,
        adjustflag: str,
        retries: int,
    ) -> list[dict[str, str]]:
        attempts = max(1, retries + 1)
        last_error: Exception | None = None
        for _attempt in range(attempts):
            try:
                with _query_deadline(self.timeout, code):
                    rs = self.client.query_history_k_data_plus(
                        _to_baostock_code(code),
                        fields,
                        start_date=start.isoformat(),
                        end_date=end.isoformat(),
                        frequency="d",
                        adjustflag=adjustflag,
                    )
                return _result_rows(rs)
            except Exception as exc:
                last_error = exc
        raise BaoStockError(f"BaoStock history query failed for {code}: {last_error}") from last_error

    def load_trade_calendar(self, start: date, end: date, exchange: str = "SSE") -> list[TradeCalendar]:
        rows = _result_rows(self.client.query_trade_dates(start_date=start.isoformat(), end_date=end.isoformat()))
        previous_open_date: date | None = None
        calendar = []
        for row in rows:
            cal_date = parse_date(row["calendar_date"])
            is_open = row.get("is_trading_day") == "1"
            calendar.append(TradeCalendar(cal_date=cal_date, exchange=exchange, is_open=is_open, pretrade_date=previous_open_date))
            if is_open:
                previous_open_date = cal_date
        return calendar

    def load_limit_prices(self, _start: date, _end: date, _codes: Iterable[str]) -> list[LimitPrice]:
        return []

    def load_suspensions(self, _start: date, _end: date, _codes: Iterable[str]) -> list[Suspension]:
        return []


def _daily_bar_from_row(row: dict[str, str]) -> DailyBar | None:
    if not row.get("open") or not row.get("close"):
        return None
    return DailyBar(
        trade_date=parse_date(row["date"]),
        ts_code=_to_ts_code(row["code"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        pre_close=float(row.get("preclose") or 0),
        volume=float(row.get("volume") or 0),
        amount=float(row.get("amount") or 0),
        pct_chg=float(row.get("pctChg") or 0),
        adj_factor=1.0,
    )


@contextmanager
def _query_deadline(timeout: float, code: str):
    if timeout <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return
    def _raise_timeout(_signum: int, _frame: object) -> None:
        raise TimeoutError(f"BaoStock history query timed out for {code} after {timeout:.1f}s")

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])
        signal.signal(signal.SIGALRM, previous_handler)


def _stock_basic_from_rows(rows: list[dict[str, str]]) -> list[StockBasic]:
    result = []
    for row in rows:
        ts_code = _to_ts_code(row["code"])
        result.append(
            StockBasic(
                ts_code=ts_code,
                symbol=ts_code.split(".")[0],
                name=row.get("code_name", ""),
                exchange=_exchange_from_baostock_code(row["code"]),
                market=_market_from_type(row.get("type", "")),
                list_date=parse_date(row["ipoDate"]),
                delist_date=_optional_date(row.get("outDate", "")),
                is_hs="",
                status="L" if row.get("status", "1") == "1" else "D",
            )
        )
    return result


def _result_rows(result: Any) -> list[dict[str, str]]:
    if getattr(result, "error_code", "0") != "0":
        raise BaoStockError(getattr(result, "error_msg", "BaoStock query failed"))

    fields = list(getattr(result, "fields", []))
    rows = []
    while result.next():
        values = result.get_row_data()
        rows.append(dict(zip(fields, values)))
    return rows


def _import_baostock() -> BaoStockClientProtocol:
    try:
        import baostock as bs
    except ImportError as exc:
        raise BaoStockError("BaoStock is not installed. Run: pip install baostock") from exc
    return bs


def _to_ts_code(code: str) -> str:
    normalized = code.strip()
    if "." in normalized:
        first, second = normalized.split(".", 1)
        if first.lower() in {"sh", "sz"}:
            return f"{second.upper()}.{first.upper()}"
        return f"{first.upper()}.{second.upper()}"
    return normalized.upper()


def _to_baostock_code(code: str) -> str:
    normalized = code.strip()
    if "." in normalized:
        first, second = normalized.split(".", 1)
        if first.lower() in {"sh", "sz"}:
            return f"{first.lower()}.{second.lower()}"
        return f"{second.lower()}.{first.lower()}"
    return normalized.lower()


def _exchange_from_baostock_code(code: str) -> str:
    return "SSE" if code.startswith("sh.") else "SZSE"


def _market_from_type(value: str) -> str:
    return {"1": "股票", "2": "指数", "3": "其他"}.get(value, value or "股票")


def _optional_date(value: str | None) -> date | None:
    return parse_date(value) if value else None
