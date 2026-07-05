from datetime import date, datetime
from tempfile import TemporaryDirectory
from unittest import TestCase

from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import MinuteBar, RealtimeQuote


class MarketStoreTest(TestCase):
    def test_store_minute_bars_and_realtime_quotes(self) -> None:
        with TemporaryDirectory() as tmp:
            store = SQLiteStore(f"{tmp}/market.sqlite")
            store.initialize()

            minute_count = store.upsert_minute_bars(
                [
                    MinuteBar(
                        trade_time=datetime(2026, 7, 3, 9, 31),
                        ts_code="600030.SH",
                        interval="1",
                        open=20.0,
                        high=20.1,
                        low=20.0,
                        close=20.1,
                        volume=1000,
                        amount=2010000,
                        adjust="qfq",
                        source="AKShare",
                    )
                ]
            )
            quote_count = store.upsert_realtime_quotes(
                [
                    RealtimeQuote(
                        quote_time=datetime(2026, 7, 3, 10, 0),
                        ts_code="600030.SH",
                        name="中信证券",
                        price=20.5,
                        open=20.0,
                        high=20.8,
                        low=19.9,
                        pre_close=20.2,
                        volume=120000,
                        amount=246000000,
                        pct_chg=1.49,
                        source="mootdx",
                    )
                ]
            )

            self.assertEqual(minute_count, 1)
            self.assertEqual(quote_count, 1)
            self.assertEqual(store.load_minute_bars(date(2026, 7, 3), date(2026, 7, 3))[0].close, 20.1)
            self.assertEqual(store.load_realtime_quotes()[0].price, 20.5)
