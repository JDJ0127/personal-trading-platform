from datetime import date
from unittest import TestCase

from trading_platform.data.baostock_provider import BaoStockDataProvider, _to_baostock_code, _to_ts_code


class FakeBaoStockResult:
    def __init__(self, fields: list[str], rows: list[list[str]]) -> None:
        self.error_code = "0"
        self.error_msg = ""
        self.fields = fields
        self.rows = rows
        self.index = -1

    def next(self) -> bool:
        self.index += 1
        return self.index < len(self.rows)

    def get_row_data(self) -> list[str]:
        return self.rows[self.index]


class FakeBaoStockClient:
    def query_all_stock(self, day: str) -> FakeBaoStockResult:
        self.day = day
        return FakeBaoStockResult(["code", "tradeStatus", "code_name"], [["sh.600030", "1", "中信证券"]])

    def query_stock_basic(self, code: str = "", code_name: str = "") -> FakeBaoStockResult:
        return FakeBaoStockResult(
            ["code", "code_name", "ipoDate", "outDate", "type", "status"],
            [["sh.600030", "中信证券", "2003-01-06", "", "1", "1"], ["sh.000001", "上证指数", "1990-12-19", "", "2", "1"]],
        )

    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "2",
    ) -> FakeBaoStockResult:
        self.history_args = (code, fields, start_date, end_date, frequency, adjustflag)
        return FakeBaoStockResult(
            fields.split(","),
            [["2026-06-01", "sh.600030", "20.0", "20.5", "19.8", "20.2", "19.9", "5000", "101000", "1.51"]],
        )

    def query_trade_dates(self, start_date: str, end_date: str) -> FakeBaoStockResult:
        return FakeBaoStockResult(
            ["calendar_date", "is_trading_day"],
            [["2026-06-01", "1"], ["2026-06-02", "0"], ["2026-06-03", "1"]],
        )


class FailingHistoryClient(FakeBaoStockClient):
    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "2",
    ) -> FakeBaoStockResult:
        if code == "sh.600031":
            raise RuntimeError("network timeout")
        return super().query_history_k_data_plus(code, fields, start_date, end_date, frequency, adjustflag)


class BaoStockProviderTest(TestCase):
    def test_code_conversion_accepts_baostock_and_ts_code_formats(self) -> None:
        self.assertEqual(_to_ts_code("sh.600030"), "600030.SH")
        self.assertEqual(_to_ts_code("600030.SH"), "600030.SH")
        self.assertEqual(_to_baostock_code("600030.SH"), "sh.600030")
        self.assertEqual(_to_baostock_code("sh.600030"), "sh.600030")

    def test_load_stock_basic_filters_by_all_stock_result(self) -> None:
        provider = BaoStockDataProvider(FakeBaoStockClient())

        stocks = provider.load_stock_basic(date(2026, 6, 1))

        self.assertEqual(len(stocks), 1)
        self.assertEqual(stocks[0].ts_code, "600030.SH")
        self.assertEqual(stocks[0].exchange, "SSE")
        self.assertEqual(stocks[0].status, "L")

    def test_load_daily_bars(self) -> None:
        client = FakeBaoStockClient()
        provider = BaoStockDataProvider(client)

        bars = provider.load_daily_bars(date(2026, 6, 1), date(2026, 6, 1), ["600030.SH"])

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].ts_code, "600030.SH")
        self.assertEqual(bars[0].close, 20.2)
        self.assertEqual(client.history_args[0], "sh.600030")

    def test_load_daily_bars_can_skip_failed_symbols(self) -> None:
        provider = BaoStockDataProvider(FailingHistoryClient())

        bars = provider.load_daily_bars(
            date(2026, 6, 1),
            date(2026, 6, 1),
            ["600030.SH", "600031.SH"],
            retries=1,
            continue_on_error=True,
        )

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].ts_code, "600030.SH")

    def test_load_trade_calendar_sets_previous_open_date(self) -> None:
        provider = BaoStockDataProvider(FakeBaoStockClient())

        calendar = provider.load_trade_calendar(date(2026, 6, 1), date(2026, 6, 3))

        self.assertEqual(len(calendar), 3)
        self.assertIsNone(calendar[0].pretrade_date)
        self.assertEqual(calendar[1].pretrade_date, date(2026, 6, 1))
        self.assertEqual(calendar[2].pretrade_date, date(2026, 6, 1))
