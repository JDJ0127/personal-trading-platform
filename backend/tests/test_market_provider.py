from __future__ import annotations

from datetime import date
from unittest import TestCase

from trading_platform.data.market_provider import CompositeMarketDataProvider


class FakeAkshare:
    def stock_info_a_code_name(self):
        return [{"code": "600030", "name": "中信证券"}]

    def stock_zh_a_hist(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str):
        self.hist_args = (symbol, period, start_date, end_date, adjust)
        return [
            {
                "日期": "2026-07-03",
                "开盘": 20.0,
                "最高": 20.8,
                "最低": 19.9,
                "收盘": 20.5,
                "成交量": 120000,
                "成交额": 246000000,
                "涨跌幅": 1.49,
            }
        ]

    def stock_zh_a_hist_min_em(self, symbol: str, start_date: str, end_date: str, period: str, adjust: str):
        self.minute_args = (symbol, start_date, end_date, period, adjust)
        return [
            {
                "时间": "2026-07-03 09:31:00",
                "开盘": 20.0,
                "最高": 20.1,
                "最低": 20.0,
                "收盘": 20.1,
                "成交量": 1000,
                "成交额": 2010000,
            }
        ]

    def stock_zh_a_spot_em(self):
        return [
            {
                "代码": "600030",
                "名称": "中信证券",
                "最新价": 20.5,
                "今开": 20.0,
                "最高": 20.8,
                "最低": 19.9,
                "昨收": 20.2,
                "成交量": 120000,
                "成交额": 246000000,
                "涨跌幅": 1.49,
            }
        ]

    def stock_news_em(self, symbol: str):
        return [{"发布时间": "2026-07-03 10:00:00", "文章来源": "财经快讯", "标题": "券商板块活跃", "新闻链接": "https://example.test/news"}]

    def stock_info_global_em(self):
        return [{"发布时间": "2026-07-03 09:00:00", "文章来源": "财经快讯", "标题": "宏观政策保持稳定"}]


class FailingAkshare(FakeAkshare):
    def stock_zh_a_hist(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str):
        raise RuntimeError("akshare temporary failure")


class FakeEfinanceStock:
    def get_quote_history(self, stock_codes: str, beg: str, end: str, klt: int, fqt: int):
        self.history_args = (stock_codes, beg, end, klt, fqt)
        return [
            {
                "日期": "2026-07-03",
                "开盘": 20.0,
                "最高": 20.6,
                "最低": 19.8,
                "收盘": 20.3,
                "成交量": 110000,
                "成交额": 223300000,
                "涨跌幅": 0.5,
            }
        ]

    def get_realtime_quotes(self, fs: str | None = None):
        return [{"代码": "600030", "名称": "中信证券", "最新价": 20.3}]


class FakeMootdxClient:
    def quotes(self, codes=None):
        self.codes = codes
        return [{"code": "600030", "name": "中信证券", "price": 20.6, "open": 20.0, "high": 20.8, "low": 19.9, "pre_close": 20.2}]


class MarketProviderTest(TestCase):
    def test_load_daily_bars_uses_akshare_qfq(self) -> None:
        akshare = FakeAkshare()
        provider = CompositeMarketDataProvider(akshare_client=akshare)

        bars = provider.load_daily_bars(date(2026, 7, 3), date(2026, 7, 3), ["600030.SH"], adjust="qfq")

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].trade_date, date(2026, 7, 3))
        self.assertEqual(bars[0].ts_code, "600030.SH")
        self.assertEqual(bars[0].close, 20.5)
        self.assertEqual(akshare.hist_args, ("600030", "daily", "20260703", "20260703", "qfq"))

    def test_load_daily_bars_filters_rows_outside_requested_date_range(self) -> None:
        class LooseDateAkshare(FakeAkshare):
            def stock_zh_a_hist(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str):
                return [
                    {
                        "日期": "2026-07-02",
                        "开盘": 20.0,
                        "最高": 20.8,
                        "最低": 19.9,
                        "收盘": 20.5,
                    }
                ]

        provider = CompositeMarketDataProvider(akshare_client=LooseDateAkshare())

        bars = provider.load_daily_bars(date(2026, 7, 3), date(2026, 7, 3), ["600030.SH"])

        self.assertEqual(bars, [])

    def test_load_daily_bars_falls_back_to_efinance(self) -> None:
        efinance = FakeEfinanceStock()
        provider = CompositeMarketDataProvider(akshare_client=FailingAkshare(), efinance_stock=efinance)

        bars = provider.load_daily_bars(date(2026, 7, 3), date(2026, 7, 3), ["600030.SH"], adjust="hfq")

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].close, 20.3)
        self.assertTrue(provider.last_report.fallback_used)
        self.assertEqual(efinance.history_args, ("600030", "20260703", "20260703", 101, 2))

    def test_load_minute_bars(self) -> None:
        akshare = FakeAkshare()
        provider = CompositeMarketDataProvider(akshare_client=akshare)

        bars = provider.load_minute_bars(date(2026, 7, 3), date(2026, 7, 3), ["600030.SH"], interval="1")

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].trade_time.date(), date(2026, 7, 3))
        self.assertEqual(bars[0].interval, "1")
        self.assertEqual(akshare.minute_args[0], "600030")

    def test_realtime_quotes_prefers_mootdx(self) -> None:
        mootdx = FakeMootdxClient()
        provider = CompositeMarketDataProvider(akshare_client=FakeAkshare(), mootdx_client=mootdx)

        quotes = provider.load_realtime_quotes(["600030.SH"])

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].source, "mootdx")
        self.assertEqual(mootdx.codes, ["600030.SH"])

    def test_load_news_events(self) -> None:
        provider = CompositeMarketDataProvider(akshare_client=FakeAkshare())

        events = provider.load_news_events(code="600030.SH")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "券商板块活跃")
