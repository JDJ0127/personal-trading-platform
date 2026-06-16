from unittest import TestCase
from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path

from trading_platform.cli.main import _incremental_start, _resolve_baostock_sync_dates, _select_codes
from trading_platform.data.sqlite_store import SQLiteStore
from trading_platform.models import DailyBar


class CliUniverseTest(TestCase):
    def test_limit_codes_keeps_prefix(self) -> None:
        self.assertEqual(_select_codes(["600030.SH", "300308.SZ", "000001.SZ"], 0, 2), ["600030.SH", "300308.SZ"])

    def test_select_codes_applies_offset(self) -> None:
        self.assertEqual(_select_codes(["600030.SH", "300308.SZ", "000001.SZ"], 1, 1), ["300308.SZ"])

    def test_limit_codes_rejects_non_positive_limit(self) -> None:
        with self.assertRaises(SystemExit):
            _select_codes(["600030.SH"], 0, 0)

    def test_incremental_start_uses_day_after_latest_bar(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "sync.sqlite")
            store.initialize()
            store.upsert_daily_bars([DailyBar(date(2026, 6, 3), "600030.SH", 20, 21, 19, 20, 19, 100, 1000)])

            self.assertEqual(_incremental_start(store, date(2026, 6, 1), date(2026, 6, 8)), date(2026, 6, 4))

    def test_resolve_baostock_dates_can_infer_incremental_start(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SQLiteStore(Path(tmpdir) / "sync.sqlite")
            store.initialize()
            store.upsert_daily_bars([DailyBar(date(2026, 6, 3), "600030.SH", 20, 21, 19, 20, 19, 100, 1000)])

            start, end = _resolve_baostock_sync_dates(store, None, date(2026, 6, 8), True)

            self.assertEqual(start, date(2026, 6, 4))
            self.assertEqual(end, date(2026, 6, 8))
