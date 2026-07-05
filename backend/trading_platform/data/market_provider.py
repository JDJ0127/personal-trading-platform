from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Protocol

from trading_platform.data.csv_provider import parse_date
from trading_platform.models import DailyBar, MinuteBar, NewsEvent, RealtimeQuote, StockBasic


class MarketDataError(RuntimeError):
    pass


class AkshareClientProtocol(Protocol):
    def stock_info_a_code_name(self) -> Any:
        ...

    def stock_zh_a_hist(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str) -> Any:
        ...

    def stock_zh_a_hist_min_em(self, symbol: str, start_date: str, end_date: str, period: str, adjust: str) -> Any:
        ...

    def stock_zh_a_spot_em(self) -> Any:
        ...

    def stock_news_em(self, symbol: str) -> Any:
        ...

    def stock_info_global_em(self) -> Any:
        ...


class EfinanceStockProtocol(Protocol):
    def get_quote_history(self, stock_codes: str, beg: str, end: str, klt: int, fqt: int) -> Any:
        ...

    def get_realtime_quotes(self, fs: str | None = None) -> Any:
        ...


@dataclass(frozen=True)
class MarketDataSourceReport:
    source: str
    fallback_used: bool
    rows: int


class CompositeMarketDataProvider:
    """A-share market data provider with AKShare primary source and optional fallbacks."""

    def __init__(
        self,
        akshare_client: AkshareClientProtocol | None = None,
        efinance_stock: EfinanceStockProtocol | None = None,
        mootdx_client: Any | None = None,
    ) -> None:
        self.akshare = akshare_client
        self.efinance = efinance_stock
        self.mootdx = mootdx_client
        self.last_report: MarketDataSourceReport | None = None

    def load_stock_basic(self, as_of: date) -> list[StockBasic]:
        ak = self._akshare()
        rows = _records(ak.stock_info_a_code_name())
        stocks = [
            StockBasic(
                ts_code=_to_ts_code(row.get("code") or row.get("代码") or row.get("symbol") or ""),
                symbol=str(row.get("code") or row.get("代码") or row.get("symbol") or ""),
                name=str(row.get("name") or row.get("名称") or ""),
                exchange=_exchange_from_code(str(row.get("code") or row.get("代码") or "")),
                market="主板/创业板/科创板",
                list_date=as_of,
                status="L",
            )
            for row in rows
            if row.get("code") or row.get("代码") or row.get("symbol")
        ]
        self.last_report = MarketDataSourceReport("AKShare", False, len(stocks))
        return stocks

    def load_daily_bars(
        self,
        start: date,
        end: date,
        codes: Iterable[str],
        adjust: str = "qfq",
        continue_on_error: bool = False,
    ) -> list[DailyBar]:
        bars: list[DailyBar] = []
        fallback_used = False
        for code in codes:
            try:
                bars.extend(self._load_daily_bars_akshare(start, end, code, adjust))
            except Exception:
                try:
                    bars.extend(self._load_daily_bars_efinance(start, end, code, adjust))
                    fallback_used = True
                except Exception:
                    if continue_on_error:
                        continue
                    raise
        self.last_report = MarketDataSourceReport("AKShare+efinance" if fallback_used else "AKShare", fallback_used, len(bars))
        return bars

    def load_minute_bars(
        self,
        start: date,
        end: date,
        codes: Iterable[str],
        interval: str = "1",
        adjust: str = "",
        continue_on_error: bool = False,
    ) -> list[MinuteBar]:
        bars: list[MinuteBar] = []
        for code in codes:
            try:
                rows = _records(
                    self._akshare().stock_zh_a_hist_min_em(
                        symbol=_symbol(code),
                        start_date=f"{start.isoformat()} 09:30:00",
                        end_date=f"{end.isoformat()} 15:00:00",
                        period=interval,
                        adjust=adjust,
                    )
                )
            except Exception:
                if continue_on_error:
                    continue
                raise
            for row in rows:
                bar = _minute_bar_from_row(row, code, interval, adjust, "AKShare")
                if bar and start <= bar.trade_time.date() <= end:
                    bars.append(bar)
        self.last_report = MarketDataSourceReport("AKShare", False, len(bars))
        return bars

    def load_realtime_quotes(self, codes: Iterable[str] | None = None) -> list[RealtimeQuote]:
        requested = {_normalize_code(code) for code in codes or []}
        errors: list[Exception] = []
        for source_name, loader in (("mootdx", self._load_realtime_quotes_mootdx), ("AKShare", self._load_realtime_quotes_akshare), ("efinance", self._load_realtime_quotes_efinance)):
            try:
                quotes = loader(requested)
                self.last_report = MarketDataSourceReport(source_name, source_name != "mootdx", len(quotes))
                return quotes
            except Exception as exc:
                errors.append(exc)
        raise MarketDataError(f"Realtime quote query failed: {errors[-1] if errors else 'unknown error'}")

    def load_news_events(self, code: str | None = None, limit: int = 50) -> list[NewsEvent]:
        ak = self._akshare()
        if code:
            rows = _records(ak.stock_news_em(symbol=_symbol(code)))
        else:
            rows = _records(ak.stock_info_global_em())
        events = [_news_event_from_row(row) for row in rows[:limit]]
        self.last_report = MarketDataSourceReport("AKShare", False, len(events))
        return [event for event in events if event]

    def _load_daily_bars_akshare(self, start: date, end: date, code: str, adjust: str) -> list[DailyBar]:
        rows = _records(
            self._akshare().stock_zh_a_hist(
                symbol=_symbol(code),
                period="daily",
                start_date=_compact_date(start),
                end_date=_compact_date(end),
                adjust=adjust,
            )
        )
        return [
            bar
            for row in rows
            if (bar := _daily_bar_from_row(row, code))
            if start <= bar.trade_date <= end
        ]

    def _load_daily_bars_efinance(self, start: date, end: date, code: str, adjust: str) -> list[DailyBar]:
        ef = self._efinance()
        rows = _records(
            ef.get_quote_history(
                stock_codes=_symbol(code),
                beg=_compact_date(start),
                end=_compact_date(end),
                klt=101,
                fqt=_efinance_adjust_flag(adjust),
            )
        )
        return [
            bar
            for row in rows
            if (bar := _daily_bar_from_row(row, code))
            if start <= bar.trade_date <= end
        ]

    def _load_realtime_quotes_mootdx(self, requested: set[str]) -> list[RealtimeQuote]:
        client = self.mootdx or _import_mootdx_client()
        codes = list(requested) if requested else None
        rows = _records(client.quotes(codes) if codes else client.quotes())
        return _filter_quotes([quote for row in rows if (quote := _quote_from_row(row, "mootdx"))], requested)

    def _load_realtime_quotes_akshare(self, requested: set[str]) -> list[RealtimeQuote]:
        rows = _records(self._akshare().stock_zh_a_spot_em())
        return _filter_quotes([quote for row in rows if (quote := _quote_from_row(row, "AKShare"))], requested)

    def _load_realtime_quotes_efinance(self, requested: set[str]) -> list[RealtimeQuote]:
        rows = _records(self._efinance().get_realtime_quotes())
        return _filter_quotes([quote for row in rows if (quote := _quote_from_row(row, "efinance"))], requested)

    def _akshare(self) -> AkshareClientProtocol:
        if self.akshare is None:
            self.akshare = _import_akshare()
        return self.akshare

    def _efinance(self) -> EfinanceStockProtocol:
        if self.efinance is None:
            self.efinance = _import_efinance_stock()
        return self.efinance


def _daily_bar_from_row(row: dict[str, Any], code: str) -> DailyBar | None:
    trade_date_value = _get(row, "日期", "date", "trade_date")
    close = _float(_get(row, "收盘", "close", "最新价"))
    open_price = _float(_get(row, "开盘", "open", "今开"))
    if not trade_date_value or close is None or open_price is None:
        return None
    return DailyBar(
        trade_date=parse_date(str(trade_date_value)),
        ts_code=_to_ts_code(code),
        open=open_price,
        high=_float(_get(row, "最高", "high")) or open_price,
        low=_float(_get(row, "最低", "low")) or open_price,
        close=close,
        pre_close=_previous_close(row, close),
        volume=_float(_get(row, "成交量", "volume", "vol")) or 0.0,
        amount=_float(_get(row, "成交额", "amount")) or 0.0,
        pct_chg=_float(_get(row, "涨跌幅", "pct_chg", "涨跌幅%")) or 0.0,
        adj_factor=1.0,
    )


def _minute_bar_from_row(row: dict[str, Any], code: str, interval: str, adjust: str, source: str) -> MinuteBar | None:
    trade_time = _parse_datetime(_get(row, "时间", "日期", "day", "datetime"))
    close = _float(_get(row, "收盘", "close"))
    open_price = _float(_get(row, "开盘", "open"))
    if trade_time is None or close is None or open_price is None:
        return None
    return MinuteBar(
        trade_time=trade_time,
        ts_code=_to_ts_code(code),
        interval=interval,
        open=open_price,
        high=_float(_get(row, "最高", "high")) or open_price,
        low=_float(_get(row, "最低", "low")) or open_price,
        close=close,
        volume=_float(_get(row, "成交量", "volume")) or 0.0,
        amount=_float(_get(row, "成交额", "amount")) or 0.0,
        adjust=adjust,
        source=source,
    )


def _quote_from_row(row: dict[str, Any], source: str) -> RealtimeQuote | None:
    code = _get(row, "代码", "code", "symbol")
    price = _float(_get(row, "最新价", "price", "now", "现价"))
    if not code or price is None:
        return None
    return RealtimeQuote(
        quote_time=datetime.now(),
        ts_code=_to_ts_code(str(code)),
        name=str(_get(row, "名称", "name") or ""),
        price=price,
        open=_float(_get(row, "今开", "open")) or 0.0,
        high=_float(_get(row, "最高", "high")) or 0.0,
        low=_float(_get(row, "最低", "low")) or 0.0,
        pre_close=_float(_get(row, "昨收", "pre_close", "preclose")) or 0.0,
        volume=_float(_get(row, "成交量", "volume", "vol")) or 0.0,
        amount=_float(_get(row, "成交额", "amount")) or 0.0,
        pct_chg=_float(_get(row, "涨跌幅", "pct_chg")) or 0.0,
        source=source,
    )


def _news_event_from_row(row: dict[str, Any]) -> NewsEvent | None:
    title = str(_get(row, "标题", "title", "新闻标题") or "")
    if not title:
        return None
    return NewsEvent(
        event_time=_parse_datetime(_get(row, "发布时间", "时间", "date", "datetime")) or datetime.now(),
        source=str(_get(row, "文章来源", "媒体", "source") or "AKShare"),
        title=title,
        url=str(_get(row, "新闻链接", "链接", "url") or ""),
        content=str(_get(row, "新闻内容", "content") or ""),
    )


def _records(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if hasattr(data, "to_dict"):
        return list(data.to_dict("records"))
    if isinstance(data, dict):
        return [data]
    return [dict(row) for row in data]


def _get(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _previous_close(row: dict[str, Any], close: float) -> float:
    pre_close = _float(_get(row, "昨收", "pre_close", "preclose"))
    pct_chg = _float(_get(row, "涨跌幅", "pct_chg"))
    if pre_close is not None:
        return pre_close
    if pct_chg is not None and pct_chg != -100:
        return close / (1 + pct_chg / 100)
    return close


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time())
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d %H:%M:%S", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return datetime.combine(parse_date(text[:10]), time())
    except Exception:
        return None


def _filter_quotes(quotes: list[RealtimeQuote], requested: set[str]) -> list[RealtimeQuote]:
    if not requested:
        return quotes
    return [quote for quote in quotes if _normalize_code(quote.ts_code) in requested]


def _to_ts_code(code: str) -> str:
    normalized = _normalize_code(code)
    if normalized.endswith(".SH") or normalized.endswith(".SZ") or normalized.endswith(".BJ"):
        return normalized
    exchange = _exchange_from_code(normalized)
    return f"{normalized}.{exchange}" if exchange else normalized


def _normalize_code(code: str) -> str:
    code = code.strip()
    if "." in code:
        number, exchange = code.split(".", 1)
        return f"{number}.{exchange.upper()}"
    if code.startswith(("sh", "sz", "bj")):
        exchange = code[:2].upper()
        suffix = {"SH": "SH", "SZ": "SZ", "BJ": "BJ"}[exchange]
        return f"{code[2:]}.{suffix}"
    return code


def _symbol(code: str) -> str:
    normalized = _normalize_code(code)
    return normalized.split(".", 1)[0]


def _exchange_from_code(code: str) -> str:
    normalized = _normalize_code(code)
    if normalized.endswith(".SH") or normalized.startswith(("5", "6", "9")):
        return "SH"
    if normalized.endswith(".SZ") or normalized.startswith(("0", "2", "3")):
        return "SZ"
    if normalized.endswith(".BJ") or normalized.startswith(("4", "8")):
        return "BJ"
    return ""


def _compact_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _efinance_adjust_flag(adjust: str) -> int:
    return {"": 0, "qfq": 1, "hfq": 2}.get(adjust, 1)


def _import_akshare() -> AkshareClientProtocol:
    try:
        import akshare as ak
    except ImportError as exc:
        raise MarketDataError("AKShare is required. Install optional dependency: pip install akshare") from exc
    return ak


def _import_efinance_stock() -> EfinanceStockProtocol:
    try:
        from efinance import stock
    except ImportError as exc:
        raise MarketDataError("efinance fallback is required. Install optional dependency: pip install efinance") from exc
    return stock


def _import_mootdx_client() -> Any:
    try:
        from mootdx.quotes import Quotes
    except ImportError as exc:
        raise MarketDataError("mootdx realtime source is required. Install optional dependency: pip install mootdx") from exc
    return Quotes.factory(market="std")
